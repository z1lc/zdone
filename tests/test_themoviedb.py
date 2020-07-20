from app.themoviedb import clean_description


def test_clean_description():
    assert "XBCDEFGXBCDEFG" == clean_description("ABCDEFGABCDEFG", "A", "X")
