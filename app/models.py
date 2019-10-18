from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from . import db
from . import login


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(128), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    maximum_minutes_per_day = db.Column(db.Integer, nullable=False, server_default='120')

    # import uuid ; uuid.uuid4()
    api_key = db.Column(db.String(128), unique=True)

    toodledo_token_json = db.Column(db.String(512))

    habitica_user_id = db.Column(db.String(128))
    habitica_api_token = db.Column(db.String(128))

    dependencies = db.Column(db.Text)
    priorities = db.Column(db.Text)

    trello_api_key = db.Column(db.String(128))
    trello_api_access_token = db.Column(db.String(128))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return '<User {}>'.format(self.username)


@login.user_loader
def load_user(id) -> User:
    return User.query.get(int(id))


class kv(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    k = db.Column(db.Text, unique=True)
    v = db.Column(db.Text)
