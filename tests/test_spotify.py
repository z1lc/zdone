import pytest

from app.models.base import User
from app.spotify import update_spotify_anki_playlist


@pytest.mark.skip(reason="integration")
def test_send_and_log_notification_integration():
    update_spotify_anki_playlist(User.query.filter_by(username='rsanek').one())