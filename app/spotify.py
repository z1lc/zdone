import random
from random import randrange

import spotipy
from spotipy import oauth2

from app import kv

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
    for artist in ARTISTS:
        for top_track in sp.artist_top_tracks(artist_id=artist)['tracks'][:NUM_TOP_TRACKS]:
            csv_line = "\""
            csv_line += top_track['uri'] + "\",\""
            csv_line += top_track['name'] + "\",\""
            inner_artists = []
            for inner_artist in top_track['artists']:
                inner_artists.append(inner_artist['name'])
            csv_line += ", ".join(inner_artists) + "\",\""
            csv_line += top_track['album']['name'] + "\",\""
            csv_line += "<img src='" + top_track['album']['images'][0]['url'] + "'>\"\n"

            output.append(csv_line)

    return "".join(set(output))
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
