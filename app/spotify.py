import json
import random
from datetime import timedelta
from random import randrange

import spotipy
from flask import redirect
from spotipy import oauth2

from app import kv, redis_client, db
from app.models import ManagedSpotifyArtist

SCOPES = 'user-read-playback-state user-modify-playback-state user-library-read user-top-read'
NUM_TOP_TRACKS = 3


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


def play_track(full_url, track_uri, user, offset=None):
    sp = get_spotify(full_url, user)
    if isinstance(sp, str):
        redis_client.set("last_spotify_track", track_uri.encode())
        redis_client.expire("last_spotify_track", timedelta(seconds=10))
        return redirect(sp)
    track = sp.track(track_uri)
    start = randrange(10000, track['duration_ms'] - 10000) if offset is None else offset
    sp.start_playback(uris=[track_uri], position_ms=start)
    return ""


def get_top_track_uris(user):
    sp = get_spotify("zdone", user)
    if isinstance(sp, str):
        return None
    output = []
    my_managed_artists = [artist.spotify_artist_uri for artist in
                          ManagedSpotifyArtist.query.filter_by(user_id=user.id).all()]

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
            if artist in my_managed_artists:
                output.append(create_csv_line(track))

    # get top 3 tracks for each artist in ARTISTS
    for artist in my_managed_artists:
        for top_track in sp.artist_top_tracks(artist_id=artist)['tracks'][:NUM_TOP_TRACKS]:
            output.append(create_csv_line(top_track))

    return "".join(set(output))
    # return sp.artist_top_tracks(artist_id=artists[0])


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
