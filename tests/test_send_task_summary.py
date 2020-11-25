import pytest

from app.models.base import User
from app.scheduled.send_task_summary import send_email


@pytest.mark.skip(reason="integration")
def test_send_email():
    send_email(User.query.filter_by(username="rsanek").one())
