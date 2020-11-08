import os
import uuid
from datetime import datetime

from sentry_sdk import capture_exception

from app import app, db
from app.card_generation.anki import generate_full_apkg
from app.log import log
from app.models.base import User, ApkgGeneration
from app.util import get_b2_api
from readwise import refresh_highlights_and_books
from themoviedb import refresh_videos

if __name__ == '__main__':
    b2_api = get_b2_api()
    for user in User.query.all():  # type: ignore
        try:
            if user.tmdb_session_id:
                log(f'Beginning refresh of videos from TMDB for user {user.username}...')
                refresh_videos(user)
                log(f'Successfully completed TMDB refresh for user {user.username}.')
            else:
                log(f'Did not find TMDB credentials for user {user.username}')

            if user.readwise_access_token:
                log(f'Beginning export of highlights from Readwise for user {user.username}...')
                refresh_highlights_and_books(user)
                log(f'Successfully completed export of highlights from Readwise for user {user.username}.')
            else:
                log(f'Did not find Readwise credentials for user {user.username}')

            if user.id <= 6:
                log(f'Beginning generation of Anki package file (.apkg) for user {user.username}...')
                filename: str = os.path.join(app.instance_path, f'anki-export-{user.username}.apkg')
                os.makedirs(app.instance_path, exist_ok=True)
                notes = generate_full_apkg(user, filename)
                log(f'Successfully generated apkg with {notes} notes. Beginning upload to B2...')

                at = datetime.utcnow()
                b2_filename = f'{at.strftime("%Y%m%d")}-{user.username}-{uuid.uuid4()}.apkg'
                b2_file = b2_api.get_bucket_by_name('zdone-apkgs').upload_local_file(
                    local_file=filename,
                    file_name=b2_filename,
                    file_infos={
                        'user': user.username,
                        'user_id': str(user.id),
                        'note_count': str(notes),
                    }
                )
                id = b2_file.id_
                size = b2_file.size
                log(f'Successfully uploaded apkg file with name {b2_filename} to B2. Received file id {id}. '
                    f'Will log into apkg_generations table...')
                db.session.add(ApkgGeneration(
                    user_id=user.id,
                    at=at,
                    b2_file_id=id,
                    b2_file_name=b2_filename,
                    file_size=size,
                    notes=notes
                ))
                db.session.commit()

                log(f'Successfully completed apkg generation & upload for user {user.username}.')
        except Exception as e:
            log(f'Received unexpected exception for user {user.username}!')
            capture_exception(e)
