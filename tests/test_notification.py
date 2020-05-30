import pytest

from app.models import User
from app.notification import send_and_log_notification


@pytest.mark.skip(reason="integration")
def test_send_and_log_notification_integration():
    send_and_log_notification(User.query.filter_by(username='rsanek').one(), 27, log=False)
