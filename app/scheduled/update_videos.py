from app.models.base import User
from app.themoviedb import get_stuff

if __name__ == '__main__':
    for user in User.query.filter(User.tmdb_session_id.isnot(None)).all():  # type: ignore
        get_stuff(user)
