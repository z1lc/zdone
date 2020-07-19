import time
from typing import List, Tuple

from sentry_sdk import capture_exception

from app import db
from app.log import log
from app.models.base import User
from app.models.spotify import SpotifyArtist, ManagedSpotifyArtist
from app.spotify import get_spotify, get_top_tracks, update_last_fm_scrobble_counts, update_spotify_anki_playlist

MAX_RETRIES_PER_ARTIST = 2

# This code is scheduled to run once daily by the Heroku Scheduler. This helps avoid work that would previously be done
# on apkg download within the request, which was very slow.
if __name__ == '__main__':
    refresh_start_time = time.time()
    all_users = User.query.all()
    log('Will update last.fm scrobble counts for all users.')
    for registered_user in all_users:
        update_last_fm_scrobble_counts(registered_user)

    log('Will update downloadable playlist for all users.')
    for registered_user in all_users:
        update_spotify_anki_playlist(registered_user)

    log('Will update the top songs for all followed artists in table `managed_spotify_artists`.')
    log('Getting artists...')
    managed_artists: List[Tuple[ManagedSpotifyArtist, SpotifyArtist]] = \
        db.session.query(ManagedSpotifyArtist, SpotifyArtist) \
            .join(ManagedSpotifyArtist) \
            .filter_by(following=True) \
            .all()
    artists: List[SpotifyArtist] = list(set([artist for _, artist in managed_artists]))
    log(f'Got {len(artists)} distinct artists.')
    user: User = User.query.filter_by(username="rsanek").one()
    sp = get_spotify("zdone", user)
    log(f'Getting top liked songs as user {user.username}...')

    for i, artist in enumerate(artists):
        try_count = 0
        while try_count < MAX_RETRIES_PER_ARTIST:
            try_count += 1
            try:
                dropped, top_tracks = get_top_tracks(sp, artist, allow_refresh=True)
                log(f'[{round(i / len(artists) * 100)}%] '
                    f'Updated mappings for artist {artist.name}, dropping {dropped} & adding {len(top_tracks)}.')
                break
            except Exception as e:
                log(f'Received exception {e}. Will try to refresh access token and try again.')
                sp = get_spotify("zdone", user)
                if try_count == MAX_RETRIES_PER_ARTIST:
                    # looks like we weren't able to resolve this with just a token refresh.
                    # publish this to Sentry so we know what's going on.
                    capture_exception(e)

    log('Finished updating all followed artists.')
    log(f'Full refresh completed in {round(time.time() - refresh_start_time)} seconds.')
