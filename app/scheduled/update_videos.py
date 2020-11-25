from app.models.base import User
from app.themoviedb import refresh_videos

# deprecated -- now captured in refresh_data_generate_apkgs_and_upload_to_b2.py
if __name__ == "__main__":
    for user in User.query.filter(User.tmdb_session_id.isnot(None)).all():  # type: ignore
        refresh_videos(user)
