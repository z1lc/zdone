"""Token storage"""

from json import dumps, loads

from toodledo import TokenStorageFile

from . import kv


class TokenStoragePostgres(TokenStorageFile):
    """Stores the API tokens as a file"""

    def __init__(self, path):
        super().__init__(path)

    def Save(self, token):
        kv.put(self.path, dumps(token))

    def Load(self):
        return loads(kv.get(self.path))
