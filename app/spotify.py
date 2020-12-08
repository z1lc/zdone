import collections
import datetime
import json
import random
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from random import randrange
from typing import Optional, List, Tuple, Dict

import pytz
import requests
import spotipy
from dateutil import parser
from flask import redirect
from spotipy import oauth2
from sqlalchemy.exc import IntegrityError

from app import kv, db
from app.log import log
from app.models.base import User, GateDef
from app.models.spotify import (
    ManagedSpotifyArtist,
    SpotifyArtist,
    SpotifyTrack,
    SpotifyPlay,
    TopTrack,
    SpotifyAlbum,
    SpotifyFeature,
)
from app.util import today_datetime, today, JsonDict

# Scopes that are currently requested for public users -- only request things that are necessary
MIN_SCOPES: str = (
    "user-read-playback-state "
    "user-modify-playback-state "
    "user-read-currently-playing "
    "user-library-read "
    "user-top-read "
    "user-follow-read "
)

# Scopes that are requested for 'internal' users -- request generously to ease testing
ALL_SCOPES: str = (
    "user-read-playback-state "
    "user-modify-playback-state "
    "user-read-currently-playing "
    "user-library-read "
    "user-top-read "
    "user-read-playback-position "
    "user-read-recently-played "
    "user-follow-read "
    "user-follow-modify "
    "playlist-read-collaborative "
    "playlist-modify-public "
    "playlist-read-private "
    "playlist-modify-private"
)
NUM_TOP_TRACKS: int = 3
# randomized song playback will avoid starting within RANDOM_RANGE_MS of beginning or end of song.
# If multiple random calls happen in succession, it will also avoid restarting within 2 * RANDOM_RANGE_MS of the most
# recent random playback.
RANDOM_RANGE_MS: int = 10_000


def follow_unfollow_artists(user: User) -> None:
    sp = get_spotify("", user)
    results = list()
    last_artist_id = None
    while True:
        if not last_artist_id:
            saved = sp.current_user_followed_artists(limit=50)
        else:
            saved = sp.current_user_followed_artists(limit=50, after=last_artist_id)
        results.extend(saved["artists"]["items"])
        last_artist_id = saved["artists"]["cursors"]["after"]
        if not last_artist_id:
            break
    do_add_artists(user, [artist["uri"] for artist in results], True)


# via https://stackoverflow.com/a/434328
def chunker(seq, size):
    return (seq[pos : pos + size] for pos in range(0, len(seq), size))


def update_spotify_anki_playlist(user: User):
    if (
        user.spotify_token_json is None
        or user.spotify_token_json == ""
        or not user.is_gated(GateDef.CREATE_ANKI_SPOTIFY_PLAYLIST)
    ):
        log(f"Skipping update for user {user.username} as they are not on the allowlist.")
        return

    sp = get_spotify("zdone", user)
    me = sp.me()

    if user.spotify_playlist_uri is None:
        returned = sp.user_playlist_create(
            me["id"],
            name="Anki Plays",
            public=False,
            description="All the songs that you have played through Spotify + Anki. "
            "Download this playlist to make jumping to random points in Anki faster!",
        )
        user.spotify_playlist_uri = returned["uri"]
        db.session.commit()

    unique_uris = list(set([sp.spotify_track_uri for sp in SpotifyPlay.query.filter_by(user_id=user.id).all()]))

    # as far as I can tell, the API doesn't have an easy way to avoid adding duplicate
    # songs to a playlist, so here we delete all tracks in the playlist before re-adding.
    sp.playlist_replace_items(playlist_id=user.spotify_playlist_uri, items=[])
    for track_uris in chunker(unique_uris, 100):
        sp.playlist_add_items(
            playlist_id=user.spotify_playlist_uri,
            items=track_uris,
        )

    log(f"Updated Spotify playlist for user {user.username}")


def update_last_fm_scrobble_counts(user: User):
    if user.last_fm_username is None:
        log(f"User {user.username} does not have a last.fm username set. Nothing to refresh.")
        return

    last_refresh_time = user.last_fm_last_refresh_time
    week_ago = today_datetime() - timedelta(days=7)
    if last_refresh_time is None or pytz.timezone("US/Pacific").localize(last_refresh_time) < week_ago:
        done = False
        page = 1
        name_to_plays = {}
        while not done:
            top_artists_batch = json.loads(
                requests.get(
                    f"https://ws.audioscrobbler.com/2.0/?method=user.gettopartists&user={user.last_fm_username}"
                    f"&api_key={kv.get('LAST_FM_API_KEY')}&format=json&limit=1000&page={str(page)}"
                ).text
            )
            page += 1
            done = page >= int(top_artists_batch["topartists"]["@attr"]["totalPages"])
            for artist in top_artists_batch["topartists"]["artist"]:
                name_to_plays[artist["name"].lower()] = artist["playcount"]
        for managed_spotify_artist, spotify_artist in (
            db.session.query(ManagedSpotifyArtist, SpotifyArtist)
            .join(ManagedSpotifyArtist)
            .filter_by(user_id=user.id)
            .all()
        ):
            managed_spotify_artist.last_fm_scrobbles = name_to_plays.get(spotify_artist.name.lower(), None)
        user.last_fm_last_refresh_time = today_datetime()
        db.session.commit()
        log(f"Updated scrobble counts for user {user.username}")
    else:
        log(f"Skipping last.fm update for user {user.username} as they have a recent refresh.")


def save_token_info(token_info, user: User):
    user.spotify_token_json = json.dumps(token_info)
    db.session.commit()


def get_cached_token_info(sp_oauth, user: User) -> Optional[JsonDict]:
    maybe_token_info = user.spotify_token_json
    if maybe_token_info:
        token_info = json.loads(maybe_token_info)
        if sp_oauth.is_token_expired(token_info):
            token_info = sp_oauth.refresh_access_token(token_info["refresh_token"])
            save_token_info(token_info, user)
        return token_info
    return None


def add_or_get_album(sp, spotify_album_uri: str):
    album = SpotifyAlbum.query.filter_by(uri=spotify_album_uri).one_or_none()
    if not album:
        sp_album = sp.album(spotify_album_uri)
        album = SpotifyAlbum(
            uri=spotify_album_uri,
            name=sp_album["name"],
            spotify_artist_uri=add_or_get_artist(sp, sp_album["artists"][0]["uri"]).uri,
            album_type=sp_album["album_type"],
            released_at=parser.parse(sp_album["release_date"]).date(),
            spotify_image_url=sp_album["images"][0]["url"] if sp_album["images"] else None,
        )
        db.session.add(album)
        db.session.commit()
    return album


# Unused right now, but nice to keep around if/when I need to do various backfills
def populate_null(user: User) -> None:
    sql = f"""select distinct uri
from spotify_tracks
where uri not in (select spotify_track_uri from spotify_features)"""
    unpopulated = [a[0] for a in list(db.engine.execute(sql))]
    sp = get_spotify("", user)

    batchsize = 20
    for i in range(0, len(unpopulated), batchsize):
        batch = unpopulated[i : i + batchsize]
        if i % 1000 == 0:
            sp = get_spotify("", user)
        tracks = sp.tracks(batch)["tracks"]
        for j, track in enumerate(tracks):
            create_features_from_artists(sp, track)
        log(
            f"Processed 20 more tracks. Total this run is {round(i / len(unpopulated) * 1000) / 10}%, "
            f"{i} / {len(unpopulated)}"
        )


def add_or_get_artist(sp, spotify_artist_uri: str):
    artist = SpotifyArtist.query.filter_by(uri=spotify_artist_uri).one_or_none()
    if not artist:
        sp_artist = sp.artist(spotify_artist_uri)
        artist = SpotifyArtist(
            uri=spotify_artist_uri,
            name=sp_artist["name"],
            spotify_image_url=sp_artist["images"][0]["url"] if sp_artist["images"] else None,
        )
        db.session.add(artist)
        db.session.commit()
    return artist


def maybe_get_spotify_authorize_url(full_url: str, user: User) -> Optional[str]:
    sp_oauth = oauth2.SpotifyOAuth(
        scope=ALL_SCOPES if user.is_gated(GateDef.USE_GENEROUS_SPOTIFY_SCOPES) else MIN_SCOPES,
        client_id="03f34cada5cc46a5929be06ff7532321",
        client_secret=kv.get("SPOTIFY_CLIENT_SECRET"),
        redirect_uri="https://www.zdone.co/spotify/auth"
        if "zdone" in full_url
        else "http://127.0.0.1:5000/spotify/auth",
        cache_path=f".cache-{user.username}",
    )

    token_info = get_cached_token_info(sp_oauth, user)

    if not token_info:
        if "code" not in full_url:
            return sp_oauth.get_authorize_url()
        else:
            code = sp_oauth.parse_response_code(full_url)
            token_info = sp_oauth.get_access_token(code)
            save_token_info(token_info, user)
    return None


def get_spotify(full_url: str, user: User):
    sp_oauth = oauth2.SpotifyOAuth(
        scope=ALL_SCOPES if user.is_gated(GateDef.USE_GENEROUS_SPOTIFY_SCOPES) else MIN_SCOPES,
        client_id="03f34cada5cc46a5929be06ff7532321",
        client_secret=kv.get("SPOTIFY_CLIENT_SECRET"),
        redirect_uri="https://www.zdone.co/spotify/auth"
        if "zdone" in full_url
        else "http://127.0.0.1:5000/spotify/auth",
        cache_path=f".cache-{user.username}",
    )

    if token_info := get_cached_token_info(sp_oauth, user):
        return spotipy.Spotify(auth=token_info["access_token"])
    else:
        return sp_oauth.get_authorize_url()


def bulk_add_tracks(sp, track_uris: List[str]) -> None:
    not_added_tracks = set(track_uris) - set([track.uri for track in SpotifyTrack.query.all()])
    for track_uri in not_added_tracks:
        add_or_get_track(sp, track_uri)


def add_or_get_feature(track_uri: str, artist_uri: str, ordinal: int) -> SpotifyFeature:
    feature = SpotifyFeature.query.filter_by(
        spotify_track_uri=track_uri, spotify_artist_uri=artist_uri, ordinal=ordinal
    ).one_or_none()
    if not feature:
        feature = SpotifyFeature(
            spotify_track_uri=track_uri,
            spotify_artist_uri=artist_uri,
            ordinal=ordinal,
        )
        db.session.add(feature)
        db.session.commit()
    return feature


def create_features_from_artists(sp, sp_track) -> List[SpotifyFeature]:
    to_ret = list()
    for i, artist in enumerate(sp_track["artists"]):
        spotify_artist = add_or_get_artist(sp, artist["uri"])
        to_ret.append(add_or_get_feature(sp_track["uri"], spotify_artist.uri, i))
    return to_ret


def add_or_get_track(sp, track_uri: str) -> SpotifyTrack:
    track = SpotifyTrack.query.filter_by(uri=track_uri).one_or_none()
    if not track:
        sp_track = sp.track(track_uri)
        track = SpotifyTrack(
            uri=track_uri,
            name=sp_track["name"],
            spotify_artist_uri=add_or_get_artist(sp, sp_track["artists"][0]["uri"]).uri,
            spotify_album_uri=add_or_get_album(sp, sp_track["album"]["uri"]).uri,
            duration_milliseconds=sp_track["duration_ms"],
        )
        db.session.add(track)
        create_features_from_artists(sp, sp_track)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()  # uh oh, let's roll back this session

            # potentially another thread added the track between this thread's read & write. try reading it here again
            track = SpotifyTrack.query.filter_by(uri=track_uri).one()
    return track


def do_add_artists(user: User, artist_uris: List[str], remove_not_included: bool = False) -> None:
    sp = get_spotify("", user)
    existing_managed_artist_uris = [
        msa.spotify_artist_uri for msa in ManagedSpotifyArtist.query.filter_by(user_id=user.id).all()
    ]
    # if we pass true get_followed_managed_spotify_artists_for_user, we cause infinite loop:
    # do_add_artists -> get_followed_managed_spotify_artists_for_user -> follow_unfollow_artists -> do_add_artists
    currently_unfollowed_managed_artist_uris = [
        msa.spotify_artist_uri for msa in get_followed_managed_spotify_artists_for_user(user, False)
    ]

    to_add = set(artist_uris).difference(set(existing_managed_artist_uris))
    for artist_uri in to_add:
        spotify_artist = add_or_get_artist(sp, artist_uri)
        managed_artist = ManagedSpotifyArtist(
            user_id=user.id, spotify_artist_uri=spotify_artist.uri, date_added=today()
        )
        db.session.add(managed_artist)

    to_follow = set(artist_uris).intersection(set(currently_unfollowed_managed_artist_uris))
    for artist_uri in to_follow:
        artist = ManagedSpotifyArtist.query.filter_by(user_id=user.id, spotify_artist_uri=artist_uri).one()
        artist.following = True

    if remove_not_included:
        to_remove = set(existing_managed_artist_uris).difference(set(artist_uris))
        for artist_uri in to_remove:
            msa = ManagedSpotifyArtist.query.filter_by(user_id=user.id, spotify_artist_uri=artist_uri).one()
            msa.following = False

    db.session.commit()


def play_track(full_url: str, track_uri: str, user: User, offset: Optional[int] = None):
    sp = get_spotify(full_url, user)
    if isinstance(sp, str):
        user.last_spotify_track = track_uri
        db.session.commit()
        return redirect(sp)
    track = add_or_get_track(sp, track_uri)
    if offset is None:
        start = randrange(RANDOM_RANGE_MS, track.duration_milliseconds - RANDOM_RANGE_MS)
        last_random_play = user.last_random_play_offset
        if last_random_play and track.duration_milliseconds > RANDOM_RANGE_MS * 3:  # avoid infinite loop
            # try to pick a different spot in the song from the last random selection
            while start - RANDOM_RANGE_MS < last_random_play < start + RANDOM_RANGE_MS:
                start = randrange(RANDOM_RANGE_MS, track.duration_milliseconds - RANDOM_RANGE_MS)

        user.last_random_play_offset = start
        db.session.commit()
    else:
        start = offset

    # sometimes, a song that was previously mapped to an ID becomes unplayable. Generally, it would be expensive to
    # detect this ahead of time, and our spotipy library does not thread through the status code (204) that Spotify
    # returns for the start playback call. Here, we try to start playback first anyway (to keep latency as low as
    # possible for the happy path) and then after that call we check, was this song actually playable?
    sp.start_playback(uris=[track_uri], position_ms=start)
    if not sp.tracks([track_uri], market="US")["tracks"][0]["is_playable"]:
        raise ValueError("Track is not playable")
    else:
        spotify_play = SpotifyPlay(user_id=user.id, spotify_track_uri=track.uri, created_at=today_datetime())
        db.session.add(spotify_play)
        db.session.commit()
        return ""


def get_liked_page(sp, offset: int) -> List[JsonDict]:
    tries = 0
    while tries < 10:
        tries += 1
        try:
            return sp.current_user_saved_tracks(limit=50, offset=offset)["items"]
        except Exception as e:
            continue
    log("returned nothing")
    return []


def get_top_tracks(sp, artist: SpotifyArtist, allow_refresh: bool = False) -> Tuple[int, List[TopTrack]]:
    should_refresh = allow_refresh and (
        artist.last_top_tracks_refresh is None
        or artist.last_top_tracks_refresh < (datetime.datetime.utcnow() - timedelta(days=7))
    )
    if should_refresh:
        dropped = TopTrack.query.filter_by(artist_uri=artist.uri).delete()
        top_tracks = sp.artist_top_tracks(artist_id=artist.uri)["tracks"]
        to_return = []
        for ordinal, top_track in enumerate(top_tracks, 1):
            track = add_or_get_track(sp, top_track["uri"])
            top_track_db = TopTrack(
                track_uri=track.uri, artist_uri=artist.uri, ordinal=ordinal, api_response=json.dumps(top_track)
            )
            db.session.add(top_track_db)
            to_return.append(top_track_db)
        artist.last_top_tracks_refresh = datetime.datetime.utcnow()
        db.session.commit()
        return dropped, to_return
    else:
        return 0, TopTrack.query.filter_by(artist_uri=artist.uri).all()


def get_followed_managed_spotify_artists_for_user(user: User, should_update: bool) -> List[ManagedSpotifyArtist]:
    if should_update:
        follow_unfollow_artists(user)
    return ManagedSpotifyArtist.query.filter_by(user_id=user.id, following="true").all()


def get_common_artists(user: User) -> List[SpotifyArtist]:
    artists_with_at_least_three_listens_sql = f"""
select sa.uri
from spotify_plays sp
         join spotify_tracks st on sp.spotify_track_uri = st.uri
         join spotify_features sf on st.uri = sf.spotify_track_uri
         join spotify_artists sa on sf.spotify_artist_uri = sa.uri
where sp.user_id = {user.id}
group by 1
having count(distinct st.uri) >= 3"""
    artists = [row[0] for row in list(db.engine.execute(artists_with_at_least_three_listens_sql))]
    return SpotifyArtist.query.filter(SpotifyArtist.uri.in_(artists)).all()  # type: ignore


def get_all_liked_tracks(sp):
    liked_tracks = list()

    pages = sp.current_user_saved_tracks(limit=1)["total"] // 50 + 1
    offsets = [x * 50 for x in range(0, pages)]
    with ThreadPoolExecutor() as executor:
        for saved in executor.map(get_liked_page, [sp] * pages, offsets):
            liked_tracks.extend(saved)

    return liked_tracks


def get_tracks(user: User) -> List[JsonDict]:
    log(f"get tracks {today_datetime()}")
    sp = get_spotify("zdone", user)
    if isinstance(sp, str):
        return []
    dedup_map = {}
    my_managed_artists = get_followed_managed_spotify_artists_for_user(user, True)
    managed_arists_uris = set([artist.spotify_artist_uri for artist in my_managed_artists])
    not_following_but_liked_tracks: Dict[str, int] = collections.defaultdict(int)

    # get liked tracks, then filter for artists that are in ARTISTS
    log(f"getting liked {today_datetime()}")
    liked_tracks = get_all_liked_tracks(sp)

    for item in liked_tracks:
        track = item["track"]
        artists = [artist["uri"] for artist in track["artists"]]
        if set(artists).intersection(managed_arists_uris):
            dedup_map[track["uri"]] = track
        else:
            for artist in track["artists"]:
                not_following_but_liked_tracks[artist["name"]] = not_following_but_liked_tracks[artist["name"]] + 1

    print(sorted(not_following_but_liked_tracks.items(), key=lambda dict_item: -dict_item[1])[:10])

    log(f"getting top 3 tracks per artist {today_datetime()}")
    # get top 3 tracks for each artist in ARTISTS
    for artist in my_managed_artists:
        top_tracks = TopTrack.query.filter_by(artist_uri=artist.spotify_artist_uri).all()
        if not top_tracks:
            _, top_tracks = get_top_tracks(sp, SpotifyArtist.query.filter_by(uri=artist.spotify_artist_uri).one())
        for top_track in top_tracks[: artist.num_top_tracks]:
            dedup_map[top_track.track_uri] = json.loads(top_track.api_response)

    output = dedup_map.values()

    log(f"[skipped] ensuring all tracks are in db {today_datetime()}")
    # bulk_add_tracks(sp, [track['uri'] for track in output])
    return list(output)


def get_top_liked() -> JsonDict:
    sp = get_spotify("", User.query.filter_by(username="rsanek").one())
    results = sp.current_user_saved_tracks(limit=50)
    artists = []
    tracks = []
    for item in results["items"]:
        track = item["track"]
        artists.append(track["artists"][0]["name"])
        tracks.append(track)

    selected_track = random.choice(tracks)
    sp.start_playback(uris=[selected_track["uri"]], position_ms=20000)
    correct_artist = selected_track["artists"][0]["name"]

    final_artists = [correct_artist]
    while len(final_artists) < 8:
        maybe_artist = random.choice(artists)
        if maybe_artist not in final_artists:
            final_artists.append(maybe_artist)

    random.shuffle(final_artists)
    return {"artists": final_artists, "correct_artist": correct_artist}


def get_random_song_family() -> JsonDict:
    user_ids = [1, 4, 5]
    user_id = random.choice(user_ids)
    managed_artist = random.choice(ManagedSpotifyArtist.query.filter_by(following="true", user_id=user_id).all())
    artist = SpotifyArtist.query.filter_by(uri=managed_artist.spotify_artist_uri).one()
    song = random.choice(SpotifyTrack.query.filter_by(spotify_artist_uri=managed_artist.spotify_artist_uri).all())
    sp = get_spotify("", User.query.filter_by(username="vsanek").one())
    sp.start_playback(uris=[song.uri], position_ms=20000)
    correct_artist = artist.name

    random_artists_all_users = [
        pair[1].name
        for pair in db.session.query(ManagedSpotifyArtist, SpotifyArtist)
        .join(ManagedSpotifyArtist)
        .filter(ManagedSpotifyArtist.user_id.in_(user_ids))  # type: ignore
        .all()
    ]

    final_artists = [correct_artist]
    while len(final_artists) < 8:
        maybe_artist = random.choice(random_artists_all_users)
        if maybe_artist not in final_artists:
            final_artists.append(maybe_artist)

    random.shuffle(final_artists)
    return {"artists": [correct_artist], "correct_artist": correct_artist}


def get_top_recommendations(user: User) -> List[Tuple[str, str]]:
    prepared_sql = f"""with my_artists as (select spotify_artist_uri
from managed_spotify_artists
where user_id = {user.id}),
    grouped as (select name, uri, count(*), sum(last_fm_scrobbles)
                from managed_spotify_artists
                         join spotify_artists sa on managed_spotify_artists.spotify_artist_uri = sa.uri
                where last_fm_scrobbles is not null
                group by 1, 2
                order by 3 desc, 4 desc)
select *
from grouped
where uri not in (select * from my_artists)"""
    return [(row[0], row[1].split("spotify:artist:")[1]) for row in db.engine.execute(prepared_sql)]


def get_artists_images() -> str:
    sp = get_spotify("", User.query.filter_by(username="rsanek").one())
    to_ret = ""
    for artist_uri in db.engine.execute(
        """select uri
            from spotify_artists
            where uri in (select spotify_artist_uri from managed_spotify_artists where user_id in (1, 2, 3, 4, 5, 6))
            and not ((good_image and spotify_image_url is not null) or image_override_name is not null)"""
    ):
        artist = sp.artist(artist_uri[0])
        src = artist["images"][0]["url"] if artist["images"] else ""
        name = artist["name"]
        to_ret += f"{name}<br><img src='{src}'><br>"
    return to_ret


def get_distinct_songs_this_week(user: User) -> int:
    return (
        db.session.query(SpotifyPlay)
        .join(SpotifyTrack)
        .filter(SpotifyPlay.user_id == user.id)
        .filter(SpotifyPlay.created_at >= today() - datetime.timedelta(days=7))
        .distinct(SpotifyTrack.uri)
        .count()
    )


def get_new_this_week(user: User) -> List[str]:
    artists_ordered_by_distinct_days_and_total_listens = f"""
select sa.name, count(distinct date_trunc('day', sp.created_at)), count(sp.id)
from spotify_artists sa
         join spotify_tracks st on sa.uri = st.spotify_artist_uri
         join spotify_plays sp on st.uri = sp.spotify_track_uri
where user_id = {user.id} and sp.created_at >= current_date - interval '7 days'
group by 1
order by 2 desc, 3 desc"""
    return [row[0] for row in list(db.engine.execute(artists_ordered_by_distinct_days_and_total_listens))]


def get_new_songs_this_week(user: User) -> int:
    sql = f"""
with mins as (select spotify_track_uri, min(created_at) as min_created
              from spotify_plays
              where user_id = {user.id}
              group by 1)
select *
from mins
where min_created >= current_date - interval '7 days'"""
    return len(list(db.engine.execute(sql)))
