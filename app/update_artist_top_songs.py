from typing import List

from sentry_sdk import capture_exception
from spotipy import SpotifyException

from app.models import SpotifyArtist, User
from app.spotify import get_spotify, refresh_top_tracks

MAX_RETRIES_PER_ARTIST = 2

# This code is scheduled to run once daily by the Heroku Scheduler, to avoid having to do this in-request.
if __name__ == '__main__':
    print('Will update the top songs for all artists in table `spotify_artists`.')
    print('Getting artists...')
    artists: List[SpotifyArtist] = SpotifyArtist.query.all()
    print(f'Got {len(artists)} artists.')
    user: User = User.query.filter_by(username="rsanek").one()
    sp = get_spotify("zdone", user)
    print(f'Getting top liked songs as user {user.username}...')

    for i, artist in enumerate(artists):
        try_count = 0
        while try_count < MAX_RETRIES_PER_ARTIST:
            try_count += 1
            try:
                dropped, top_tracks = refresh_top_tracks(sp, artist.uri)
                print(f'[{round(i / len(artists) * 100)}%] '
                      f'Updated mappings for artist {artist.name}, dropping {dropped} & adding {len(top_tracks)}.')
            except SpotifyException as probably_token_expiration:
                print(f'Received Spotify exception {probably_token_expiration}. '
                      f'Will try to refresh access token and try again.')
                sp = get_spotify("zdone", user)
            except Exception as e:
                print(f'Received exception while trying to get top tracks for artist {artist.name}.')
                print('Exception was sent to Sentry.')
                capture_exception(e)

    print('Updated all artists. Exiting...')
