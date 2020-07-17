import datetime

from sqlalchemy import func, UniqueConstraint, CheckConstraint

from app import db
from app.models.base import BaseModel


class SpotifyArtist(BaseModel):
    __tablename__ = "spotify_artists"
    uri: str = db.Column(db.String(128), primary_key=True)
    name: str = db.Column(db.Text, nullable=False)
    spotify_image_url: str = db.Column(db.Text)
    good_image: bool = db.Column(db.Boolean, nullable=False, server_default='false')
    image_override_name: str = db.Column(db.String(128), nullable=True)
    last_top_tracks_refresh: datetime.datetime = db.Column(db.DateTime, nullable=True)

    def get_bare_uri(self):
        return self.uri.split("spotify:artist:")[1]


class ManagedSpotifyArtist(BaseModel):
    __tablename__ = "managed_spotify_artists"
    id: int = db.Column(db.Integer, primary_key=True)
    user_id: int = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    spotify_artist_uri: str = db.Column(db.String(128), db.ForeignKey('spotify_artists.uri'), nullable=False)
    date_added: datetime.date = db.Column(db.Date, nullable=False, server_default=func.current_date())
    comment: str = db.Column(db.String(128))
    num_top_tracks: int = db.Column(db.Integer, server_default='3')  # TODO: expose to users & allow editing
    following: bool = db.Column(db.Boolean, server_default='true', nullable=True)
    last_fm_scrobbles: int = db.Column(db.Integer, nullable=True)
    __table_args__ = (UniqueConstraint('user_id', 'spotify_artist_uri', name='_user_id_and_spotify_artist_uri'),)

    def get_bare_uri(self):
        return self.spotify_artist_uri.split("spotify:artist:")[1]


class SpotifyAlbum(BaseModel):
    __tablename__ = "spotify_albums"
    uri: str = db.Column(db.String(128), primary_key=True)
    name: str = db.Column(db.Text, nullable=False)
    spotify_artist_uri: str = db.Column(db.String(128), db.ForeignKey('spotify_artists.uri'), nullable=False)
    album_type: str = db.Column(db.String(128), nullable=False)
    spotify_image_url: str = db.Column(db.Text)
    released_at: datetime.date = db.Column(db.Date, nullable=False)

    def get_bare_uri(self):
        return self.uri.split("spotify:album:")[1]


class SpotifyTrack(BaseModel):
    __tablename__ = "spotify_tracks"
    uri: str = db.Column(db.String(128), primary_key=True)
    name: str = db.Column(db.String(1024), nullable=False)
    spotify_artist_uri: str = db.Column(db.String(128), db.ForeignKey('spotify_artists.uri'), nullable=False)
    spotify_album_uri: str = db.Column(db.String(128), db.ForeignKey('spotify_albums.uri'), nullable=False)
    duration_milliseconds: int = db.Column(db.Integer, nullable=False)


class SpotifyPlay(BaseModel):
    __tablename__ = "spotify_plays"
    id: int = db.Column(db.Integer, primary_key=True)
    user_id: int = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    spotify_track_uri: str = db.Column(db.String(128), db.ForeignKey('spotify_tracks.uri'), nullable=False)
    created_at: datetime.datetime = db.Column(db.DateTime, nullable=False)


class TopTrack(BaseModel):
    __tablename__ = "top_tracks"
    id: int = db.Column(db.Integer, primary_key=True)
    artist_uri: str = db.Column(db.String(128), db.ForeignKey('spotify_artists.uri'), nullable=False)
    track_uri: str = db.Column(db.String(128), db.ForeignKey('spotify_tracks.uri'), nullable=False)
    ordinal: int = db.Column(db.Integer, nullable=False)
    api_response: str = db.Column(db.Text)  # simple dump of the exact json that was returned by the API
    __table_args__ = (
        UniqueConstraint('artist_uri', 'track_uri'),
        UniqueConstraint('artist_uri', 'ordinal'),
        CheckConstraint('ordinal >= 1'),
        CheckConstraint('ordinal <= 10'),
    )


# genanki uses the `guid` column in Anki's `notes` table to deduplicate upon import. While I have updated the GUID to
# be based upon the Spotify track URI, old notes that were imported using the original, CSV-based method have GUIDs that
# will not match these, since Anki seems to assign GUIDs randomly instead of in some deterministic fashion. This table
# captures that mapping for such cards created before genanki days, so that existing users wouldn't have to hard-migrate
# to the new approach (and in the process lose all review history). This table should be read-only, since no cards in
# the future should need this mapping if generated through genanki.
class LegacySpotifyTrackNoteGuidMapping(BaseModel):
    __tablename__ = "legacy_spotify_track_note_guid_mappings"
    id: int = db.Column(db.Integer, primary_key=True)
    user_id: int = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    spotify_track_uri: str = db.Column(db.String(128), db.ForeignKey('spotify_tracks.uri'), nullable=False)
    anki_guid: str = db.Column(db.String(10), nullable=False)
    __table_args__ = (
        UniqueConstraint('user_id', 'spotify_track_uri', name='_user_id_and_spotify_track_uri'),
        UniqueConstraint('user_id', 'anki_guid', name='_user_id_and_anki_guid'),
    )
