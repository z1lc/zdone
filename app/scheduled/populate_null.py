from app.models.base import User
from app.spotify import populate_null

if __name__ == '__main__':
    populate_null(User.query.filter_by(username="rsanek").one())
