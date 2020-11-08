import pytest

from app.models.base import User
from app.readwise import refresh_highlights_and_books


@pytest.mark.skip(reason="integration")
def test_refresh_highlights_and_books():
    refresh_highlights_and_books(User.query.filter_by(username='rsanek').one())
