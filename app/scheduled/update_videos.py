from app.models.base import User
from app.themoviedb import get_stuff

if __name__ == '__main__':
    get_stuff(User.query.filter_by(username='rsanek').one())