import json
import random
from datetime import timedelta
from random import randrange

import spotipy
from flask import redirect
from spotipy import oauth2

from app import kv, redis_client

SCOPES = 'user-read-playback-state user-modify-playback-state user-library-read user-top-read'

ARTISTS = [
    'spotify:artist:27gtK7m9vYwCyJ04zz0kIb',  # lane 8
    'spotify:artist:3TVXtAsR1Inumwj472S9r4',  # drake
    'spotify:artist:24DO0PijjITGIEWsO8XaPs',  # nora en pure
    'spotify:artist:7GMot9WvBYqhhJz92vhBp6',  # EDX
    'spotify:artist:5INjqkS1o8h1imAzPqGZBb',  # Tame Impala
    'spotify:artist:5nki7yRhxgM509M5ADlN1p',  # Oliver Heldens
    'spotify:artist:41X1TR6hrK8Q2ZCpp2EqCz',  # bbno$
    'spotify:artist:4Zdbr0JJj9SXMDJfus1mNs',  # Ali Bakgor
    'spotify:artist:356FCJoyYWyzONni54Dgrv',  # Jerry Folk
    'spotify:artist:75cW8FFekyCjj0mfZM1Gfb',  # Flamingosis
    'spotify:artist:57dN52uHvrHOxijzpIgu3E',  # Ratatat
    'spotify:artist:5TgQ66WuWkoQ2xYxaSTnVP',  # Netsky
    'spotify:artist:1TtJ8j22Roc24e2Jx3OcU4',  # Purity Ring
    'spotify:artist:6DPYiyq5kWVQS4RGwxzPC7',  # Dr. Dre
    'spotify:artist:1RCoE2Dq19lePKhPzt9vM5',  # The Hush Sound
    'spotify:artist:6TQj5BFPooTa08A7pk8AQ1',  # Kaskade
    'spotify:artist:3q7HBObVc0L8jNeTe5Gofh',  # 50 Cent
    'spotify:artist:7CajNmpbOovFoOoasH2HaY',  # Calvin Harris
    'spotify:artist:2CIMQHirSU0MQqyYHq0eOx',  # deadmau5
    'spotify:artist:2o5jDhtHVPhrJdv3cEQ99Z',  # Tiësto
    'spotify:artist:2YOYua8FpudSEiB9s88IgQ',  # Yung Gravy
    'spotify:artist:4tZwfgrHOc3mvqYlEYSvVi',  # Daft Punk
    'spotify:artist:378dH6EszOLFShpRzAQkVM',  # Lindsey Stirling
    'spotify:artist:137W8MRPWKqSmrBGDBFSop',  # Wiz Khalifa
    'spotify:artist:1h6Cn3P4NGzXbaXidqURXs',  # Swedish House Mafia
    'spotify:artist:5K4W6rqBFWDnAN6FQUkS6x',  # Kanye West
    'spotify:artist:06HL4z0CvFAxyc27GXpf02',  # Taylor Swift
    'spotify:artist:3gi5McAv9c0qTjJ5jSmbL0',  # A.L.I.S.O.N
    'spotify:artist:3ifxHfYz2pqHku0bwx8H5J',  # Amtrac
    'spotify:artist:2tEyBfwGBfQgLXeAJW0MgC',  # Baltra
    'spotify:artist:7DuTB6wdzqFJGFLSH17k8e',  # Bhad Bhabie
    'spotify:artist:5Nngx6kSXmrSiL248sEwmT',  # Calippo
    'spotify:artist:4kYSro6naA4h99UJvo89HB',  # Cardi B
    'spotify:artist:5wwnitxvqbrtiGk3QW3BuN',  # COMPUTER DATA
    'spotify:artist:6eUKZXaKkcviH0Ku9w2n3V',  # Ed Sheeran
    'spotify:artist:7HkdQ0gt53LP4zmHsL0nap',  # Ella Mai
    'spotify:artist:1wzBqAvtFexgKHjt7i3ena',  # Fred V & Grafix
    'spotify:artist:2exebQUDoIoT0dXA8BcN1P',  # Home
    'spotify:artist:0nUF7iT0e6D5xEl743Jfu3',  # Icarus
    'spotify:artist:1gPhS1zisyXr5dHTYZyiMe',  # Kevin Gates
    'spotify:artist:3wyVrVrFCkukjdVIdirGVY',  # Lil Pump
    'spotify:artist:4IDMgbEiCgt9G7PRN62mrV',  # Memorex Memories
    'spotify:artist:1Ma3pJzPIrAyYPNRkp3SUF',  # Ross from Friends
    'spotify:artist:5Pb27ujIyYb33zBqVysBkj',  # RUFUS DU SOL
    'spotify:artist:6AUl0ykLLpvTktob97x9hO',  # Tee Grizzley

    ## Coachella 2020
    'spotify:artist:4r63FhuTkUYltbVAg5TQnk',  # DaBaby
    'spotify:artist:2RqrWplViWHSGLzlhmDcbt',  # Yaeji
    'spotify:artist:1KpCi9BOfviCVhmpI4G2sY',  # Tchami
    'spotify:artist:6PfSUFtkMVoDkx4MQkzOi3',  # 100 gecs
    'spotify:artist:4O15NlyKLIASxsJ0PrXPfz',  # Lil Uzi Vert
    'spotify:artist:61lyPtntblHJvA7FMMhi7E',  # Duke Dumont
    # 'spotify:artist:205i7E8fNVfojowcQSfK9m',  # Dom Dolla
    # 'spotify:artist:6nxWCVXbOlEVRexSbLsTer',  # Flume
    'spotify:artist:37hAfseJWi0G3Scife12Il',  # City Girls
    'spotify:artist:1URnnhqYAYcrqrcwql10ft',  # 21 Savage
]
NUM_TOP_TRACKS = 3


def save_token_info(token_info):
    kv.put('spotify_token_info', json.dumps(token_info))


def get_cached_token_info(sp_oauth):
    maybe_token_info = kv.get('spotify_token_info')
    if maybe_token_info:
        token_info = json.loads(maybe_token_info)
        if sp_oauth.is_token_expired(token_info):
            token_info = sp_oauth.refresh_access_token(token_info['refresh_token'])
            save_token_info(token_info)
        return token_info
    return None


def maybe_get_spotify_authorize_url(full_url):
    username = "rsanek"
    sp_oauth = oauth2.SpotifyOAuth(
        scope=SCOPES,
        client_id="03f34cada5cc46a5929be06ff7532321",
        client_secret=kv.get('SPOTIFY_CLIENT_SECRET'),
        redirect_uri="https://www.zdone.co/spotify/auth" if "zdone" in full_url else "http://127.0.0.1:5000/spotify/auth",
        cache_path=".cache-" + username)

    token_info = get_cached_token_info(sp_oauth)

    if not token_info:
        if "code" not in full_url:
            return sp_oauth.get_authorize_url()
        else:
            code = sp_oauth.parse_response_code(full_url)
            token_info = sp_oauth.get_access_token(code)
            save_token_info(token_info)
    return ""


def get_spotify(full_url):
    username = "rsanek"
    sp_oauth = oauth2.SpotifyOAuth(
        scope=SCOPES,
        client_id="03f34cada5cc46a5929be06ff7532321",
        client_secret=kv.get('SPOTIFY_CLIENT_SECRET'),
        redirect_uri="https://www.zdone.co/spotify/auth" if "zdone" in full_url else "http://127.0.0.1:5000/spotify/auth",
        cache_path=".cache-" + username)

    token_info = get_cached_token_info(sp_oauth)

    if not token_info:
        return sp_oauth.get_authorize_url()
    else:
        sp = spotipy.Spotify(auth=token_info['access_token'])
        return sp


def play_track(full_url, track_uri, offset=None):
    sp = get_spotify(full_url)
    if isinstance(sp, str):
        redis_client.set("last_spotify_track", track_uri.encode())
        redis_client.expire("last_spotify_track", timedelta(seconds=10))
        return redirect(sp)
    track = sp.track(track_uri)
    start = randrange(10000, track['duration_ms'] - 10000) if offset is None else offset
    sp.start_playback(uris=[track_uri], position_ms=start)
    return ""


def get_top_track_uris():
    sp = get_spotify("zdone")
    output = []

    # get liked tracks with artists that are in ARTISTS
    while True:
        results = list()
        offset = 0
        while True:
            saved = sp.current_user_saved_tracks(limit=50, offset=offset)
            results.extend(saved['items'])
            offset += 50
            if len(saved) < 50:
                break
        for item in results:
            track = item['track']
            artists = [artist['uri'] for artist in track['artists']]
            for artist in artists:
                if artist in ARTISTS:
                    output.append(create_csv_line(track))
                    break
        if len(results) < 50:
            break

    # get top 3 tracks for each artist in ARTISTS
    for artist in ARTISTS:
        for top_track in sp.artist_top_tracks(artist_id=artist)['tracks'][:NUM_TOP_TRACKS]:
            output.append(create_csv_line(top_track))

    return "".join(set(output))
    # return sp.artist_top_tracks(artist_id=artists[0])


def create_csv_line(track):
    csv_line = "\""
    csv_line += track['uri'] + "\",\""
    csv_line += track['name'] + "\",\""
    inner_artists = []
    for inner_artist in track['artists']:
        inner_artists.append(inner_artist['name'])
    csv_line += ", ".join(inner_artists) + "\",\""
    csv_line += track['album']['name'] + "\",\""
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
