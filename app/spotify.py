import random
from random import randrange

import spotipy
from spotipy import oauth2

from app import kv

SCOPES = 'user-read-playback-state user-modify-playback-state user-library-read user-top-read'

artists = [
    '27gtK7m9vYwCyJ04zz0kIb'
]


def spotify_callback(full_url):
    username = "rsanek"
    sp_oauth = oauth2.SpotifyOAuth(
        scope=SCOPES,
        client_id="03f34cada5cc46a5929be06ff7532321",
        client_secret=kv.get('SPOTIFY_CLIENT_SECRET'),
        redirect_uri="https://www.zdone.co/spotify/auth",
        cache_path=".cache-" + username)

    token_info = sp_oauth.get_cached_token()

    if not token_info:
        if "code" not in full_url:
            return "Go to <a href='" + sp_oauth.get_authorize_url() + "'>" + sp_oauth.get_authorize_url() + "</a>"
        else:
            code = sp_oauth.parse_response_code(full_url)
            token_info = sp_oauth.get_access_token(code)
    return "successfully auth'd"


def get_spotify():
    username = "rsanek"
    sp_oauth = oauth2.SpotifyOAuth(
        scope=SCOPES,
        client_id="03f34cada5cc46a5929be06ff7532321",
        client_secret=kv.get('SPOTIFY_CLIENT_SECRET'),
        redirect_uri="https://www.zdone.co/spotify/auth",
        cache_path=".cache-" + username)

    token_info = sp_oauth.get_cached_token()

    if not token_info:
        auth_url = sp_oauth.get_authorize_url()
        print("Go to: " + auth_url)
    else:
        sp = spotipy.Spotify(auth=token_info['access_token'])
        return sp


def play_track(track_uri, offset=None):
    sp = get_spotify()
    track = sp.track(track_uri)
    start = randrange(10000, track['duration_ms'] - 10000) if offset is None else offset
    sp.start_playback(uris=[track_uri], position_ms=start)
    return ""


def get_top_track_uris():
    sp = get_spotify()
    output = []
    for artist in artists:
        for top_track in sp.artist_top_tracks(artist_id=artist)['tracks']:
            csv_line = "\""
            csv_line += top_track['uri'] + "\",\""
            csv_line += top_track['name'] + "\",\""
            inner_artists = []
            for inner_artist in top_track['artists']:
                inner_artists.append(inner_artist['name'])
            csv_line += ", ".join(inner_artists) + "\",\""
            csv_line += top_track['album']['name'] + "\",\""
            csv_line += "<img src='" + top_track['album']['images'][0]['url'] + "'>\n"

            output.append(csv_line)

    return output
    # return sp.artist_top_tracks(artist_id=artists[0])


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
