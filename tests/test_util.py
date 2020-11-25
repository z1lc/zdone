from app.card_generation.util import (
    _sort_credit,
    AnkiCard,
    get_minified_js_for_review_log,
    get_minified_js_for_song_jump,
    get_minified_js_for_youtube_video,
)


def test__sort_credit():
    assert -9999 == _sort_credit("TV Show (1990 - Present)")
    assert -2002 == _sort_credit("Film (2002)")
    assert -9998 == _sort_credit("Uh-oh, no date!")
    assert -2005 == _sort_credit("1990 1991 2002 1993 1994 2005 1996 1997 2001")


def test_get_minified_js_for_review_log():
    generated_js = get_minified_js_for_review_log("api-key-123", AnkiCard.CREDITS_TO_NAME)
    assert "https://www.zdone.co/api/api-key-123/log/{{zdone Person ID}}/CREDITS_TO_NAME" in generated_js


def test_get_minified_js_for_song_jump():
    generated_js = get_minified_js_for_song_jump("api-key-123")
    assert "https://www.zdone.co/api/api-key-123/play/{{Track URI}}/" in generated_js


def test_get_minified_js_for_youtube_video():
    assert "{{YouTube Trailer Duration}}" in get_minified_js_for_youtube_video()
