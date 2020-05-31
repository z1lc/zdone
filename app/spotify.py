import datetime
import json
import random
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from random import randrange
from typing import Optional, List, Tuple

import pytz
import requests
import spotipy
from dateutil import parser
from flask import redirect
from spotipy import oauth2
from sqlalchemy.exc import IntegrityError

from app import kv, redis_client, db
from app.models import ManagedSpotifyArtist, SpotifyArtist, SpotifyTrack, SpotifyPlay, User, TopTrack, SpotifyAlbum
from app.util import today_datetime, today, JsonDict

# Scopes that are currently requested for public users -- only request things that are necessary
MIN_SCOPES: str = 'user-read-playback-state ' \
                  'user-modify-playback-state ' \
                  'user-read-currently-playing ' \
                  'user-library-read ' \
                  'user-top-read ' \
                  'user-follow-read '

# Scopes that are requested for 'internal' users -- request generously to ease testing
ALL_SCOPES: str = 'user-read-playback-state ' \
                  'user-modify-playback-state ' \
                  'user-read-currently-playing ' \
                  'user-library-read ' \
                  'user-top-read ' \
                  'user-read-playback-position ' \
                  'user-read-recently-played ' \
                  'user-follow-read ' \
                  'user-follow-modify ' \
                  'playlist-read-collaborative ' \
                  'playlist-modify-public ' \
                  'playlist-read-private ' \
                  'playlist-modify-private'
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
        results.extend(saved['artists']['items'])
        last_artist_id = saved['artists']['cursors']['after']
        if not last_artist_id:
            break
    do_add_artists(user, [artist['uri'] for artist in results], True)


def update_last_fm_scrobble_counts(user: User):
    if user.last_fm_username is None:
        return
    if user.last_fm_last_refresh_time is None or \
            pytz.timezone('US/Pacific').localize(user.last_fm_last_refresh_time) < (
            today_datetime() - timedelta(days=7)):
        done = False
        page = 1
        name_to_plays = {}
        while not done:
            top_artists_batch = json.loads(requests.get(
                f"https://ws.audioscrobbler.com/2.0/?method=user.gettopartists&user={user.last_fm_username}"
                f"&api_key={kv.get('LAST_FM_API_KEY')}&format=json&limit=1000&page={str(page)}").text)
            page += 1
            done = page >= int(top_artists_batch['topartists']['@attr']['totalPages'])
            for artist in top_artists_batch['topartists']['artist']:
                name_to_plays[artist['name'].lower()] = artist['playcount']
        for managed_spotify_artist, spotify_artist in db.session.query(ManagedSpotifyArtist, SpotifyArtist) \
                .join(ManagedSpotifyArtist) \
                .filter_by(user_id=user.id) \
                .all():
            managed_spotify_artist.last_fm_scrobbles = name_to_plays.get(spotify_artist.name.lower(), None)
        user.last_fm_last_refresh_time = today_datetime()
        db.session.commit()


def save_token_info(token_info, user: User):
    user.spotify_token_json = json.dumps(token_info)
    db.session.commit()


def get_cached_token_info(sp_oauth, user: User) -> Optional[JsonDict]:
    maybe_token_info = user.spotify_token_json
    if maybe_token_info:
        token_info = json.loads(maybe_token_info)
        if sp_oauth.is_token_expired(token_info):
            token_info = sp_oauth.refresh_access_token(token_info['refresh_token'])
            save_token_info(token_info, user)
        return token_info
    return None


def add_or_get_album(sp, spotify_album_uri: str):
    album = SpotifyAlbum.query.filter_by(uri=spotify_album_uri).one_or_none()
    if not album:
        sp_album = sp.album(spotify_album_uri)
        album = SpotifyAlbum(
            uri=spotify_album_uri,
            name=sp_album['name'],
            spotify_artist_uri=sp_album['artists'][0]['uri'],
            album_type=sp_album['album_type'],
            released_at=parser.parse(sp_album['release_date']).date(),
            spotify_image_url=sp_album['images'][0]['url'] if sp_album['images'] else None
        )
        db.session.add(album)
        db.session.commit()
    return album


def populate_null(user: User) -> None:
    top_played_tracks_sql = f"""select distinct spotify_album_uri
from spotify_tracks
where spotify_album_uri not in (select uri from spotify_albums)"""
    unpopulated = [a[0] for a in list(db.engine.execute(top_played_tracks_sql))]
    sp = get_spotify("", user)

    batchsize = 20
    for i in range(0, len(unpopulated), batchsize):
        batch = unpopulated[i:i + batchsize]
        albums = sp.albums(batch)
        for j, item in enumerate(batch):
            sp_album = albums['albums'][j]
            add_or_get_artist(sp, sp_album['artists'][0]['uri'])
            album = SpotifyAlbum(
                uri=item,
                name=sp_album['name'],
                spotify_artist_uri=sp_album['artists'][0]['uri'],
                album_type=sp_album['album_type'],
                released_at=parser.parse(sp_album['release_date']).date(),
                spotify_image_url=sp_album['images'][0]['url'] if sp_album['images'] else None
            )
            db.session.add(album)
        print(f"Wrote 20 more artists. Total this run is {round(i / len(unpopulated) * 1000) / 10}%, "
              f"{i} / {len(unpopulated)}")
        db.session.commit()


def add_or_get_artist(sp, spotify_artist_uri: str):
    artist = SpotifyArtist.query.filter_by(uri=spotify_artist_uri).one_or_none()
    if not artist:
        sp_artist = sp.artist(spotify_artist_uri)
        artist = SpotifyArtist(
            uri=spotify_artist_uri,
            name=sp_artist['name'],
            spotify_image_url=sp_artist['images'][0]['url'] if sp_artist['images'] else None
        )
        db.session.add(artist)
        db.session.commit()
    return artist


def maybe_get_spotify_authorize_url(full_url: str, user: User) -> Optional[str]:
    sp_oauth = oauth2.SpotifyOAuth(
        scope=ALL_SCOPES if user.id <= 8 else MIN_SCOPES,
        client_id="03f34cada5cc46a5929be06ff7532321",
        client_secret=kv.get('SPOTIFY_CLIENT_SECRET'),
        redirect_uri="https://www.zdone.co/spotify/auth" if "zdone" in full_url else "http://127.0.0.1:5000/spotify/auth",
        cache_path=".cache-" + user.username)

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
        scope=ALL_SCOPES if user.id <= 8 else MIN_SCOPES,
        client_id="03f34cada5cc46a5929be06ff7532321",
        client_secret=kv.get('SPOTIFY_CLIENT_SECRET'),
        redirect_uri="https://www.zdone.co/spotify/auth" if "zdone" in full_url else "http://127.0.0.1:5000/spotify/auth",
        cache_path=".cache-" + user.username)

    token_info = get_cached_token_info(sp_oauth, user)

    if not token_info:
        return sp_oauth.get_authorize_url()
    else:
        sp = spotipy.Spotify(auth=token_info['access_token'])
        return sp


def bulk_add_tracks(sp, track_uris: List[str]) -> None:
    not_added_tracks = set(track_uris) - set([track.uri for track in SpotifyTrack.query.all()])
    for track_uri in not_added_tracks:
        add_or_get_track(sp, track_uri)


def add_or_get_track(sp, track_uri: str) -> SpotifyTrack:
    track = SpotifyTrack.query.filter_by(uri=track_uri).one_or_none()
    if not track:
        sp_track = sp.track(track_uri)
        spotify_artist = add_or_get_artist(sp, sp_track['artists'][0]['uri'])
        spotify_album = add_or_get_album(sp, sp_track['album']['uri'])
        track = SpotifyTrack(uri=track_uri,
                             name=sp_track['name'],
                             spotify_artist_uri=spotify_artist.uri,
                             spotify_album_uri=spotify_album.uri,
                             duration_milliseconds=sp_track['duration_ms'])
        db.session.add(track)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()  # uh oh, let's roll back this session

            # potentially another thread added the track between this thread's read & write. try reading it here again
            track = SpotifyTrack.query.filter_by(uri=track_uri).one()
    return track


def do_add_artists(user: User, artist_uris: List[str], remove_not_included: bool = False) -> None:
    sp = get_spotify("", user)
    existing_managed_artist_uris = [msa.spotify_artist_uri for msa in
                                    ManagedSpotifyArtist.query.filter_by(user_id=user.id).all()]
    # if we pass true get_followed_managed_spotify_artists_for_user, we cause infinite loop:
    # do_add_artists -> get_followed_managed_spotify_artists_for_user -> follow_unfollow_artists -> do_add_artists
    currently_unfollowed_managed_artist_uris = [msa.spotify_artist_uri for msa in
                                                get_followed_managed_spotify_artists_for_user(user, False)]

    to_add = set(artist_uris).difference(set(existing_managed_artist_uris))
    for artist_uri in to_add:
        spotify_artist = add_or_get_artist(sp, artist_uri)
        managed_artist = ManagedSpotifyArtist(user_id=user.id,
                                              spotify_artist_uri=spotify_artist.uri,
                                              date_added=today())
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
        redis_client.set(f"last_spotify_track-{user.username}", track_uri.encode(), ex=10)
        return redirect(sp)
    track = add_or_get_track(sp, track_uri)
    maybe_redis_last_play_key = f"last_play-{user.username}-{track_uri}"
    if offset is None:
        start = randrange(RANDOM_RANGE_MS, track.duration_milliseconds - RANDOM_RANGE_MS)
        last_random_play = redis_client.get(maybe_redis_last_play_key)
        if last_random_play and track.duration_milliseconds > RANDOM_RANGE_MS * 3:  # avoid infinite loop
            # try to pick a different spot in the song from the last random selection
            while start - RANDOM_RANGE_MS < int(last_random_play.decode()) < start + RANDOM_RANGE_MS:
                start = randrange(RANDOM_RANGE_MS, track.duration_milliseconds - RANDOM_RANGE_MS)

        redis_client.set(maybe_redis_last_play_key, start, ex=60)
    else:
        start = offset
    sp.start_playback(uris=[track_uri], position_ms=start)
    spotify_play = SpotifyPlay(user_id=user.id,
                               spotify_track_uri=track.uri,
                               created_at=today_datetime())
    db.session.add(spotify_play)
    db.session.commit()
    return ""


def get_liked_page(sp, offset: int) -> List[JsonDict]:
    tries = 0
    while tries < 10:
        tries += 1
        try:
            return sp.current_user_saved_tracks(limit=50, offset=offset)['items']
        except Exception as e:
            continue
    print('returned nothing')
    return []


def get_top_tracks(sp, artist: SpotifyArtist, allow_refresh: bool = False) -> Tuple[List[TopTrack], List[TopTrack]]:
    should_refresh = allow_refresh and (artist.last_top_tracks_refresh is None or
                                        artist.last_top_tracks_refresh < (datetime.datetime.now() - timedelta(days=7)))
    if should_refresh:
        dropped = TopTrack.query.filter_by(artist_uri=artist.uri).delete()
        top_tracks = sp.artist_top_tracks(artist_id=artist.uri)['tracks']
        to_return = []
        for ordinal, top_track in enumerate(top_tracks, 1):
            track = add_or_get_track(sp, top_track['uri'])
            top_track_db = TopTrack(track_uri=track.uri,
                                    artist_uri=artist.uri,
                                    ordinal=ordinal,
                                    api_response=json.dumps(top_track))
            db.session.add(top_track_db)
            to_return.append(top_track_db)
        artist.last_top_tracks_refresh = datetime.datetime.now()
        db.session.commit()
        return dropped, to_return
    else:
        return [], TopTrack.query.filter_by(artist_uri=artist.uri).all()


def get_followed_managed_spotify_artists_for_user(user: User, should_update: bool) -> List[ManagedSpotifyArtist]:
    if should_update:
        follow_unfollow_artists(user)
    return ManagedSpotifyArtist.query.filter_by(user_id=user.id, following='true').all()


def get_tracks(user: User) -> List[JsonDict]:
    print(f"get tracks {today_datetime()}")
    sp = get_spotify("zdone", user)
    if isinstance(sp, str):
        return []
    dedup_map = {}
    my_managed_artists = get_followed_managed_spotify_artists_for_user(user, True)
    managed_arists_uris = set([artist.spotify_artist_uri for artist in my_managed_artists])

    # get liked tracks with artists that are in ARTISTS
    liked_tracks = list()
    print(f"getting liked {today_datetime()}")

    pages = sp.current_user_saved_tracks(limit=1)['total'] // 50 + 1
    offsets = [x * 50 for x in range(0, pages)]
    with ThreadPoolExecutor() as executor:
        for saved in executor.map(get_liked_page, [sp] * pages, offsets):
            liked_tracks.extend(saved)

    for item in liked_tracks:
        track = item['track']
        artists = [artist['uri'] for artist in track['artists']]
        for artist in artists:
            if artist in managed_arists_uris:
                dedup_map[track['uri']] = track

    print(f"getting top 3 tracks per artist {today_datetime()}")
    # get top 3 tracks for each artist in ARTISTS
    for artist in my_managed_artists:
        top_tracks = TopTrack.query.filter_by(artist_uri=artist.spotify_artist_uri).all()
        if not top_tracks:
            _, top_tracks = get_top_tracks(sp, SpotifyArtist.query.filter_by(uri=artist.spotify_artist_uri).one())
        for top_track in top_tracks[:artist.num_top_tracks]:
            dedup_map[top_track.track_uri] = json.loads(top_track.api_response)

    output = dedup_map.values()

    print(f"[skipped] ensuring all tracks are in db {today_datetime()}")
    bulk_add_tracks(sp, [track['uri'] for track in output])
    print(f"before output {today_datetime()}")
    return list(output)


def get_anki_csv(user: User) -> str:
    tracks = get_tracks(user)
    return "".join([create_csv_line(track) for track in tracks])


def create_csv_line(track) -> str:
    csv_line = "\""
    csv_line += track['uri'] + "\",\""
    csv_line += track['name'].replace('"', '\'') + "\",\""
    inner_artists = []
    for inner_artist in track['artists']:
        inner_artists.append(inner_artist['name'])
    csv_line += ", ".join(inner_artists).replace('"', '\'') + "\",\""
    csv_line += track['album']['name'].replace('"', '\'') + "\",\""
    csv_line += "<img src='" + track['album']['images'][0]['url'] + "'>\"\n"
    return csv_line


def get_top_liked() -> JsonDict:
    sp = get_spotify("", User.query.filter_by(username="rsanek").one())
    results = sp.current_user_saved_tracks(limit=50)
    artists = []
    tracks = []
    for item in results['items']:
        track = item['track']
        artists.append(track['artists'][0]['name'])
        tracks.append(track)

    selected_track = random.choice(tracks)
    sp.start_playback(uris=[selected_track['uri']], position_ms=20000)
    correct_artist = selected_track['artists'][0]['name']

    final_artists = [correct_artist]
    while len(final_artists) < 8:
        maybe_artist = random.choice(artists)
        if maybe_artist not in final_artists:
            final_artists.append(maybe_artist)

    random.shuffle(final_artists)
    return {
        "artists": final_artists,
        "correct_artist": correct_artist
    }


def get_random_song_family() -> JsonDict:
    user_ids = [1, 4, 5]
    user_id = random.choice(user_ids)
    managed_artist = random.choice(ManagedSpotifyArtist.query.filter_by(following='true', user_id=user_id).all())
    artist = SpotifyArtist.query.filter_by(uri=managed_artist.spotify_artist_uri).one()
    song = random.choice(SpotifyTrack.query.filter_by(spotify_artist_uri=managed_artist.spotify_artist_uri).all())
    sp = get_spotify("", User.query.filter_by(username="vsanek").one())
    sp.start_playback(uris=[song.uri], position_ms=20000)
    correct_artist = artist.name

    random_artists_all_users = [pair[1].name for pair in
                                db.session.query(ManagedSpotifyArtist, SpotifyArtist)
                                    .join(ManagedSpotifyArtist)
                                    .filter(ManagedSpotifyArtist.user_id.in_(user_ids))  # type: ignore
                                    .all()]

    final_artists = [correct_artist]
    while len(final_artists) < 8:
        maybe_artist = random.choice(random_artists_all_users)
        if maybe_artist not in final_artists:
            final_artists.append(maybe_artist)

    random.shuffle(final_artists)
    return {
        "artists": [correct_artist],
        "correct_artist": correct_artist
    }


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


# TODO: create Spotify playlist(s) for songs from managed artists you haven't yet listened to (as a way to promote
#  knowing an artist's full catalogue)
def get_artists_images() -> str:
    sp = get_spotify("", User.query.filter_by(username="rsanek").one())
    to_ret = ""
    for artist_uri in db.engine.execute("""select uri
from spotify_artists
where uri in (select spotify_artist_uri from managed_spotify_artists where user_id in (1, 2, 3, 4, 5, 6))
and not ((good_image and spotify_image_url is not null) or image_override_name is not null)"""):
        artist = sp.artist(artist_uri[0])
        src = artist['images'][0]['url'] if artist['images'] else ''
        name = artist['name']
        to_ret += f"{name}<br><img src='{src}'><br>"
    return to_ret
