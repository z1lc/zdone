from typing import List

from sentry_sdk import capture_exception

from app.models import SpotifyArtist, User
from app.spotify import get_spotify, refresh_top_tracks, update_last_fm_scrobble_counts

MAX_RETRIES_PER_ARTIST = 2

# This code is scheduled to run once daily by the Heroku Scheduler, to avoid having to do this in-request.
if __name__ == '__main__':
    print('Will update last.fm scrobble counts for all users.')
    for user in User.query.all():
        update_last_fm_scrobble_counts(user)
        print(f'Updated scrobble counts for user {user.username}')

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
                break
            except Exception as e:
                print(f'Received exception {e}. Will try to refresh access token and try again.')
                sp = get_spotify("zdone", user)
                if try_count == MAX_RETRIES_PER_ARTIST:
                    # looks like we weren't able to resolve this with just a token refresh.
                    # publish this to Sentry so we know what's going on.
                    capture_exception(e)

    print('Updated all artists. Exiting...')
