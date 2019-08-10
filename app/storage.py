"""Token storage"""

from json import dumps, loads

from toodledo import TokenStorageFile

from app.models import User
from . import db


class TokenStoragePostgres(TokenStorageFile):
    """Stores the API tokens in the user db"""

    def __init__(self, path):
        super().__init__(path)

    def Save(self, token):
        User.query.get(int(self.path)).toodledo_token_json = dumps(token)
        db.session.commit()

    def Load(self):
        return loads(User.query.get(int(self.path)).toodledo_token_json)
