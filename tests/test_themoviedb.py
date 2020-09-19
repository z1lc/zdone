import pytest
import tmdbsimple

from app import kv
from app.themoviedb import clean_description, backfill_null


def test_clean_description():
    assert "XBCDEFGXBCDEFG" == clean_description("ABCDEFGABCDEFG", "A", "X")
    assert "Cobb, a skilled thief who commits corporate espionage by infiltrating the subconscious of his targets is offered a chance to regain his old life as payment for a task considered to be impossible: \"[film]\", the implantation of another person's idea into a target's subconscious." == clean_description(
        "Cobb, a skilled thief who commits corporate espionage by infiltrating the subconscious of his targets is offered a chance to regain his old life as payment for a task considered to be impossible: \"inception\", the implantation of another person's idea into a target's subconscious.",
        "Inception", "[film]")


@pytest.mark.skip(reason="integration")
def test_backfill_null():
    tmdbsimple.API_KEY = kv.get('TMDB_API_KEY')
    backfill_null()
