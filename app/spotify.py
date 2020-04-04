import json
import random
from datetime import timedelta
from random import randrange

import spotipy
from flask import redirect
from sentry_sdk import capture_exception
from spotipy import oauth2

from app import kv, redis_client, db
from app.models import ManagedSpotifyArtist, SpotifyArtist, SpotifyTrack, SpotifyPlay
from app.util import today_datetime, today

SCOPES = 'user-read-playback-state ' \
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
NUM_TOP_TRACKS = 3


def migrate_legacy_artists(user):
    legacy_artists = ManagedSpotifyArtist.query.filter_by(
        legacy='true',
        user_id=user.id
    ).all()
    if legacy_artists:
        sp = get_spotify("", user)
        for artist in legacy_artists:
            sp.user_follow_artists(ids=[artist.spotify_artist_uri.split("spotify:artist:")[1]])
            artist.legacy = False
        db.session.commit()


def follow_unfollow_artists(user):
    legacy_artists = ManagedSpotifyArtist.query.filter_by(
        legacy='true',
        user_id=user.id
    ).all()
    # just in case, don't do follow/unfollow in case the person has legacy artists
    if legacy_artists:
        return
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
    do_add_artist(user, [artist['uri'] for artist in results], True)
    return


def save_token_info(token_info, user):
    user.spotify_token_json = json.dumps(token_info)
    db.session.commit()


def get_cached_token_info(sp_oauth, user):
    maybe_token_info = user.spotify_token_json
    if maybe_token_info:
        token_info = json.loads(maybe_token_info)
        if sp_oauth.is_token_expired(token_info):
            token_info = sp_oauth.refresh_access_token(token_info['refresh_token'])
            save_token_info(token_info, user)
        return token_info
    return None


def add_or_get_artist(sp, spotify_artist_uri):
    artist = SpotifyArtist.query.filter_by(uri=spotify_artist_uri).one_or_none()
    if not artist:
        artist_name = sp.artist(spotify_artist_uri)['name']
        artist = SpotifyArtist(uri=spotify_artist_uri, name=artist_name)
        db.session.add(artist)
        db.session.commit()
    return artist


def populate_null_artists(user):
    try:
        unpopulated_artists = SpotifyArtist.query.filter_by(name='').all()
        sp = get_spotify("", user)
        for artist in unpopulated_artists:
            artist.name = sp.artist(artist.uri)['name']
        db.session.commit()
    except Exception as e:
        capture_exception(e)
    return


def maybe_get_spotify_authorize_url(full_url, user):
    sp_oauth = oauth2.SpotifyOAuth(
        scope=SCOPES,
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
    return ""


def get_spotify(full_url, user):
    sp_oauth = oauth2.SpotifyOAuth(
        scope=SCOPES,
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


def add_or_get_track(sp, track_uri):
    track = SpotifyTrack.query.filter_by(uri=track_uri).one_or_none()
    if not track:
        sp_track = sp.track(track_uri)
        spotify_artist = add_or_get_artist(sp, sp_track['artists'][0]['uri'])
        track = SpotifyTrack(uri=track_uri,
                             name=sp_track['name'],
                             spotify_artist_uri=spotify_artist.uri,
                             duration_milliseconds=sp_track['duration_ms'])
        db.session.add(track)
        db.session.commit()
    return track


def do_add_artist(user, artist_uris, remove_not_included=False):
    sp = get_spotify("", user)
    existing_managed_artists = [msa.spotify_artist_uri for msa in ManagedSpotifyArtist.query.filter_by(user_id=user.id).all()]
    to_add = set(artist_uris).difference(set(existing_managed_artists))
    for artist_uri in to_add:
        spotify_artist = add_or_get_artist(sp, artist_uri)
        managed_artist = ManagedSpotifyArtist(user_id=user.id,
                                              spotify_artist_uri=spotify_artist.uri,
                                              legacy=False,
                                              date_added=today())
        db.session.add(managed_artist)

    if remove_not_included:
        to_remove = set(existing_managed_artists).difference(set(artist_uris))
        for artist_uri in to_remove:
            msa = ManagedSpotifyArtist.query.filter_by(user_id=user.id, spotify_artist_uri=artist_uri).one()
            msa.following = False

    db.session.commit()


def play_track(full_url, track_uri, user, offset=None):
    sp = get_spotify(full_url, user)
    if isinstance(sp, str):
        redis_client.set("last_spotify_track", track_uri.encode())
        redis_client.expire("last_spotify_track", timedelta(seconds=10))
        return redirect(sp)
    track = add_or_get_track(sp, track_uri)
    start = randrange(10000, track.duration_milliseconds - 10000) if offset is None else offset
    sp.start_playback(uris=[track_uri], position_ms=start)
    spotify_play = SpotifyPlay(user_id=user.id,
                               spotify_track_uri=track.uri,
                               created_at=today_datetime())
    db.session.add(spotify_play)
    db.session.commit()
    return ""


def get_tracks(user):
    sp = get_spotify("zdone", user)
    if isinstance(sp, str):
        return None
    output = []
    my_managed_artists = ManagedSpotifyArtist.query.filter_by(user_id=user.id).all()

    # get liked tracks with artists that are in ARTISTS
    results = list()
    offset = 0
    while True:
        saved = sp.current_user_saved_tracks(limit=50, offset=offset)
        results.extend(saved['items'])
        offset += 50
        if len(saved['items']) < 50:
            break
    for item in results:
        track = item['track']
        artists = [artist['uri'] for artist in track['artists']]
        for artist in artists:
            if artist in [artist.spotify_artist_uri for artist in my_managed_artists]:
                output.append(track)

    # get top 3 tracks for each artist in ARTISTS
    for artist in my_managed_artists:
        for top_track in sp.artist_top_tracks(artist_id=artist.spotify_artist_uri)['tracks'][:artist.num_top_tracks]:
            output.append(top_track)

    return output


def get_anki_csv(user):
    tracks = get_tracks(user)
    return "".join(set([create_csv_line(track) for track in tracks]))


def create_csv_line(track):
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


def get_artists():
    username = "rsanek"
    sp_oauth = oauth2.SpotifyOAuth(
        scope=SCOPES,
        client_id="03f34cada5cc46a5929be06ff7532321",
        client_secret=kv.get('SPOTIFY_CLIENT_SECRET'),
        redirect_uri="https://www.zdone.co",
        cache_path=".cache-" + username)

    token_info = sp_oauth.get_cached_token()
    # code = sp_oauth.parse_response_code("[url]")
    # token_info = sp_oauth.get_access_token(code)

    if not token_info:
        auth_url = sp_oauth.get_authorize_url()
        return "Go to: " + auth_url
    else:
        sp = spotipy.Spotify(auth=token_info['access_token'])
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
