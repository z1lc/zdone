from flask_login import UserMixin
from sqlalchemy import func, UniqueConstraint
from werkzeug.security import generate_password_hash, check_password_hash

from . import db
from . import login


# to run a db migration (in regular command line in zdone working directory):
# flask db migrate -m "comment explaining model change"
# flask db upgrade
class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(128), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    maximum_minutes_per_day = db.Column(db.Integer, nullable=False, server_default='120')

    api_key = db.Column(db.String(128), unique=True, nullable=False)

    # https://api.toodledo.com/3/account/authorize.php?response_type=code&client_id=ztasks&state=MY_STATE&scope=basic tasks notes outlines lists share write folders
    # complete auth via Postman (see http://api.toodledo.com/3/account/index.php for full info)
    toodledo_token_json = db.Column(db.String(512))

    habitica_user_id = db.Column(db.String(128))
    habitica_api_token = db.Column(db.String(128))

    dependencies = db.Column(db.Text)
    priorities = db.Column(db.Text)

    trello_api_key = db.Column(db.String(128))
    # https://trello.com/1/authorize?expiration=never&name=zdone&scope=read,write&response_type=token&key=API_KEY
    trello_api_access_token = db.Column(db.String(128))

    spotify_token_json = db.Column(db.String(1024))

    last_fm_username = db.Column(db.String(128), unique=True)
    last_fm_last_refresh_time = db.Column(db.DateTime)

    uses_rsAnki_javascript = db.Column(db.Boolean, server_default='false', nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return '<User {}>'.format(self.username)


class ManagedSpotifyArtist(db.Model):
    __tablename__ = "managed_spotify_artists"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    spotify_artist_uri = db.Column(db.String(128), db.ForeignKey('spotify_artists.uri'), nullable=False)
    date_added = db.Column(db.Date, nullable=False, server_default=func.current_date())
    comment = db.Column(db.String(128))
    num_top_tracks = db.Column(db.Integer, server_default='3')  # TODO: expose to users & allow editing
    following = db.Column(db.Boolean, server_default='true')
    last_fm_scrobbles = db.Column(db.Integer, nullable=True)
    __table_args__ = (UniqueConstraint('user_id', 'spotify_artist_uri', name='_user_id_and_spotify_artist_uri'),)

    def get_bare_uri(self):
        return self.uri.split("spotify:artist:")[1]


class SpotifyArtist(db.Model):
    __tablename__ = "spotify_artists"
    uri = db.Column(db.String(128), primary_key=True)
    name = db.Column(db.String(128), nullable=False)

    def get_bare_uri(self):
        return self.uri.split("spotify:artist:")[1]


class SpotifyTrack(db.Model):
    __tablename__ = "spotify_tracks"
    uri = db.Column(db.String(128), primary_key=True)
    name = db.Column(db.String(1024), nullable=False)
    spotify_artist_uri = db.Column(db.String(128), db.ForeignKey('spotify_artists.uri'), nullable=False)
    duration_milliseconds = db.Column(db.Integer, nullable=False)


class SpotifyPlay(db.Model):
    __tablename__ = "spotify_plays"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    spotify_track_uri = db.Column(db.String(128), db.ForeignKey('spotify_tracks.uri'), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False)


# genanki uses the `guid` column in Anki's `notes` table to deduplicate upon import. While I have updated the GUID to
# be based upon the Spotify track URI, old notes that were imported using the original, CSV-based method have GUIDs that
# will not match these, since Anki seems to assign GUIDs randomly instead of in some deterministic fashion. This table
# captures that mapping for such cards created before genanki days, so that existing users wouldn't have to hard-migrate
# to the new approach (and in the process lose all review history). This table should be read-only, since no cards in
# the future should need this mapping if generated through genanki.
class LegacySpotifyTrackNoteGuidMapping(db.Model):
    __tablename__ = "legacy_spotify_track_note_guid_mappings"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    spotify_track_uri = db.Column(db.String(128), db.ForeignKey('spotify_tracks.uri'), nullable=False)
    anki_guid = db.Column(db.String(10), nullable=False)
    __table_args__ = (
        UniqueConstraint('user_id', 'spotify_track_uri', name='_user_id_and_spotify_track_uri'),
        UniqueConstraint('user_id', 'anki_guid', name='_user_id_and_anki_guid'),
    )


# similarly, so that existing users don't have to migrate to a new note type
class LegacyModelIdMapping(db.Model):
    __tablename__ = "legacy_model_id_mappings"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    anki_spotify_track_model_id = db.Column(db.BigInteger, nullable=False)


class TaskCompletion(db.Model):
    __tablename__ = "task_completions"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    service = db.Column(db.String(128), nullable=False)
    task_id = db.Column(db.String(128), nullable=False)
    subtask_id = db.Column(db.String(128))
    duration_seconds = db.Column(db.Integer)
    at = db.Column(db.DateTime)


@login.user_loader
def load_user(id) -> User:
    return User.query.get(int(id))


class kv(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    k = db.Column(db.Text, unique=True)
    v = db.Column(db.Text)
