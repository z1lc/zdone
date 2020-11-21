import pytest

from app.card_generation.readwise import _get_person_notes_from_highlight
from app.models.base import User
from app.readwise import refresh_highlights_and_books, get_paginated
from utils import TEST_USER, get_test_highlight


@pytest.mark.skip(reason="integration")
def test_refresh_highlights_and_books():
    refresh_highlights_and_books(User.query.filter_by(username='rsanek').one())


@pytest.mark.skip(reason="integration")
def test_get_paginated():
    highlights = get_paginated(User.query.filter_by(username='rsanek').one(), "highlights")
    print(highlights)


def test_get_person_notes_from_highlight():
    fake_highlights = [
        get_test_highlight(text="Abraham Lincoln was an American president in the 19th century"),
        get_test_highlight(text="As a president, Lincoln was an interesting person"),
    ]
    assert (len(_get_person_notes_from_highlight(fake_highlights, [], TEST_USER)) == 1)
