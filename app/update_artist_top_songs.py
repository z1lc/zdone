from app import db
from app.models import SpotifyArtist, User, TopTrack
from app.spotify import get_spotify, add_or_get_track

if __name__ == '__main__':
    print('Will update the top songs for all artists in table `spotify_artists`.')
    print('Getting artists...')
    artists = SpotifyArtist.query.all()
    print(f'Got {len(artists)} artists.')
    user = User.query.filter_by(username="rsanek").one()
    sp = get_spotify("zdone", user)
    print(f'Getting top liked songs as user {user.username}...')

    for artist in artists:
        dropped = TopTrack.query.filter_by(artist_uri=artist.uri).delete()
        top_tracks = sp.artist_top_tracks(artist_id=artist.uri)['tracks']
        for ordinal, top_track in enumerate(top_tracks, 1):
            track = add_or_get_track(sp, top_track['uri'])
            db.session.add(TopTrack(track_uri=track.uri,
                                    artist_uri=track.spotify_artist_uri,
                                    ordinal=ordinal))
        db.session.commit()
        print(f'Updated mappings for artist {artist.name}, dropping {dropped} & adding {len(top_tracks)}.')

    print('Updated all artists. Exiting...')
