import pytest
import tmdbsimple

from app import kv
from app.themoviedb import clean_description, backfill_null


def test_clean_description():
    assert "XBCDEFGXBCDEFG" == clean_description("ABCDEFGABCDEFG", "A", "X")


@pytest.mark.skip(reason="integration")
def test_backfill_null():
    tmdbsimple.API_KEY = kv.get('TMDB_API_KEY')
    backfill_null()
