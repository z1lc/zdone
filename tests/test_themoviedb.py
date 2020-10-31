import pytest
import tmdbsimple

from app import kv
from app.themoviedb import clean_description, backfill_null, get_or_add_person, get_or_add_youtube_video


def test_clean_description():
    assert "XBCDEFGXBCDEFG" == clean_description("ABCDEFGABCDEFG", "A", "X")
    assert "Cobb, a skilled thief who commits corporate espionage by infiltrating the subconscious of his targets is offered a chance to regain his old life as payment for a task considered to be impossible: \"[film]\", the implantation of another person's idea into a target's subconscious." == clean_description(
        "Cobb, a skilled thief who commits corporate espionage by infiltrating the subconscious of his targets is offered a chance to regain his old life as payment for a task considered to be impossible: \"inception\", the implantation of another person's idea into a target's subconscious.",
        "Inception", "[film]")


@pytest.mark.skip(reason="integration")
def test_backfill_null():
    tmdbsimple.API_KEY = kv.get('TMDB_API_KEY')
    backfill_null()


@pytest.mark.skip(reason="integration")
def test_get_or_add_person():
    tmdbsimple.API_KEY = kv.get('TMDB_API_KEY')
    get_or_add_person('zdone:person:tmdb:121247')


@pytest.mark.skip(reason="integration")
def test_get_or_add_youtube_video():
    tmdbsimple.API_KEY = kv.get('TMDB_API_KEY')
    get_or_add_youtube_video('RTMk-xy2dTY')


@pytest.mark.skip(reason="integration")
def get_imdb_top_250():
    top250IM = list()  # extract with regex on HTML from https://www.imdb.com/chart/top/
    top250TM = list()
    for imdbid in top250IM:
        movie = tmdbsimple.Find(imdbid).info(language="en-US", external_source="imdb_id")['movie_results'][0]
        top250TM.append(movie['id'])
        print(f"Got {movie['original_title']}")

    for tmdbid in top250TM:
        tmdbsimple.Lists(id=123456789, session_id='REPLACE').add_item(media_id=tmdbid)
