import os
import uuid
from datetime import datetime

from sentry_sdk import capture_exception
from spotipy import SpotifyException

from app import app, db
from app.card_generation.anki import generate_full_apkg
from app.log import log
from app.models.anki import ApkgGeneration
from app.models.base import User, GateDef
from app.readwise import refresh_highlights_and_books
from app.spotify import follow_unfollow_artists
from app.themoviedb import refresh_videos
from app.util import get_b2_api, get_pushover_client


def refresh_user(user: User):
    if user.spotify_token_json:
        log(f"Beginning refresh of followed Spotify artists for user {user.username}...")
        try:
            follow_unfollow_artists(user)
            log(f"Successfully completed Spotify artist refresh for user {user.username}.")
        except SpotifyException as e:
            log(f"Received SpotifyException during artist refresh for user {user.username}!")
            log("This may mean they need to re-authorize.")
            log(repr(e))
            if user.is_gated(GateDef.INTERNAL_USER):
                capture_exception(e)
    else:
        log(f"Did not find Spotify credentials for user {user.username}")

    if user.tmdb_session_id:
        log(f"Beginning refresh of videos from TMDB for user {user.username}...")
        refresh_videos(user)
        log(f"Successfully completed TMDB refresh for user {user.username}.")
    else:
        log(f"Did not find TMDB credentials for user {user.username}")

    if user.readwise_access_token:
        log(f"Beginning export of books & highlights from Readwise for user {user.username}...")
        refresh_highlights_and_books(user)
        log(f"Successfully completed export of books & highlights from Readwise for user {user.username}.")
    else:
        log(f"Did not find Readwise credentials for user {user.username}")

    if user.is_gated(GateDef.INTERNAL_USER):
        log(f"Beginning generation of Anki package file (.apkg) for user {user.username}...")
        filename: str = os.path.join(app.instance_path, f"anki-export-{user.username}.apkg")
        os.makedirs(app.instance_path, exist_ok=True)
        notes = generate_full_apkg(user, filename)
        if notes == 0:
            log(f"0 notes were generated for user {user.username}. Will not upload to B2.")
        else:
            log(f"Successfully generated apkg with {notes} notes. Beginning upload to B2...")
            b2_api = get_b2_api()

            at = datetime.utcnow()
            b2_filename = f'{at.strftime("%Y%m%d")}-{user.username}-{uuid.uuid4()}.apkg'
            b2_file = b2_api.get_bucket_by_name("zdone-apkgs").upload_local_file(
                local_file=filename,
                file_name=b2_filename,
                file_infos={
                    "user": user.username,
                    "user_id": str(user.id),
                    "note_count": str(notes),
                },
            )
            id = b2_file.id_
            size = b2_file.size
            log(
                f"Successfully uploaded apkg file with name {b2_filename} to B2. Received file id {id}. "
                f"Will log into apkg_generations table..."
            )
            db.session.add(
                ApkgGeneration(
                    user_id=user.id, at=at, b2_file_id=id, b2_file_name=b2_filename, file_size=size, notes=notes
                )
            )
            db.session.commit()

            log(f"Successfully completed apkg generation & upload for user {user.username}.")

            if user.is_gated(GateDef.SEND_PUSHOVER_NOTIFICATION_AFTER_APKG_GENERATION):
                log(f"Will send Pushover reminder to {user.username}.")
                args = {
                    "title": "Download new zdone apkg",
                    "message": f"There are a total of <b>{notes}</b> available.",
                    "priority": -1,
                    "html": 1,
                    "url_title": "Download now!",
                    "url": "https://www.zdone.co/spotify/download_apkg",
                }
                get_pushover_client(user).send_message(**args)


if __name__ == "__main__":
    for user in db.session.query(User).order_by(User.id.asc()).all():  # type: ignore
        try:
            refresh_user(user)
        except Exception as e:
            log(f"Received unexpected exception for user {user.username}:")
            log(repr(e))
            capture_exception(e)
