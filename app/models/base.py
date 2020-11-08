import datetime
from typing import Optional

from flask_login import UserMixin
# see https://github.com/dropbox/sqlalchemy-stubs/issues/76#issuecomment-595839159
from flask_sqlalchemy.model import DefaultMeta
from werkzeug.security import generate_password_hash, check_password_hash

from app import db
from app import login

BaseModel: DefaultMeta = db.Model


# to run a db migration (in regular command line in zdone working directory):
# flask db migrate -m "comment explaining model change"
# flask db upgrade
class User(UserMixin, BaseModel):
    __tablename__ = "users"
    id: int = db.Column(db.Integer, primary_key=True)
    username: str = db.Column(db.String(64), index=True, unique=True)
    email: str = db.Column(db.String(128), index=True, unique=True)
    password_hash: str = db.Column(db.String(128))
    # one of https://en.wikipedia.org/wiki/List_of_tz_database_time_zones
    current_time_zone: Optional[str] = db.Column(db.String(128), nullable=True)

    maximum_minutes_per_day: int = db.Column(db.Integer, nullable=False, server_default='120')

    api_key: str = db.Column(db.String(128), unique=True, nullable=False)

    trello_api_key: str = db.Column(db.String(128))
    # User needs to visit URL and send back access token:
    # https://trello.com/1/authorize?expiration=never&name=zdone&scope=read,write&response_type=token&key=API_KEY
    trello_api_access_token: str = db.Column(db.String(128))
    # needed for figuring out who a webhook belongs to
    trello_member_id: str = db.Column(db.Text, unique=True)
    cached_trello_data: Optional[str] = db.Column(db.Text, nullable=True)

    spotify_token_json: str = db.Column(db.String(1024))
    spotify_playlist_uri: Optional[str] = db.Column(db.String(128), unique=True, nullable=True)
    last_spotify_track: Optional[str] = db.Column(db.String(128), db.ForeignKey('spotify_tracks.uri'), nullable=True)
    last_random_play_offset: Optional[int] = db.Column(db.Integer, nullable=True)

    last_fm_username: str = db.Column(db.String(128), unique=True)
    last_fm_last_refresh_time = db.Column(db.DateTime)

    uses_rsAnki_javascript: bool = db.Column(db.Boolean, server_default='false', nullable=False)
    # default tag applied to cards on export
    default_spotify_anki_tag: str = db.Column(db.Text)

    pushover_user_key: str = db.Column(db.String(128), unique=True)

    tmdb_session_id: str = db.Column(db.Text, unique=True)

    readwise_access_token: str = db.Column(db.Text, unique=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return '<User {}>'.format(self.username)


@login.user_loader
def load_user(id) -> User:
    return User.query.get(int(id))


class kv(BaseModel):
    __tablename__ = "kv"
    id: int = db.Column(db.Integer, primary_key=True)
    k: str = db.Column(db.Text, unique=True)
    v: str = db.Column(db.Text)


class ApkgGeneration(BaseModel):
    __tablename__ = "apkg_generations"
    id: int = db.Column(db.Integer, primary_key=True)
    user_id: int = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    # always UTC
    at: datetime.datetime = db.Column(db.DateTime, nullable=False)
    b2_file_id: str = db.Column(db.Text, nullable=False)
    b2_file_name: str = db.Column(db.Text, nullable=False)
    # in bytes
    file_size: int = db.Column(db.BigInteger, nullable=False)
    # the number of notes in this package, used to notify users when their newly generated deck has new notes
    notes: int = db.Column(db.Integer, nullable=False)
