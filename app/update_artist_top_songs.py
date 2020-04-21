from app.models import SpotifyArtist, User
from app.spotify import get_spotify, refresh_top_tracks

if __name__ == '__main__':
    print('Will update the top songs for all artists in table `spotify_artists`.')
    print('Getting artists...')
    artists = SpotifyArtist.query.all()
    print(f'Got {len(artists)} artists.')
    user = User.query.filter_by(username="rsanek").one()
    sp = get_spotify("zdone", user)
    print(f'Getting top liked songs as user {user.username}...')

    for i, artist in enumerate(artists):
        dropped, top_tracks = refresh_top_tracks(sp, artist.uri)
        print(f'[{round(i / len(artists) * 100)}%] '
              f'Updated mappings for artist {artist.name}, dropping {dropped} & adding {len(top_tracks)}.')

    print('Updated all artists. Exiting...')
