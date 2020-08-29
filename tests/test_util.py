from app.card_generation.util import _sort_credit


def test__sort_credit():
    assert -9999 == _sort_credit("TV Show (1990 - Present)")
    assert -2002 == _sort_credit("Film (2002)")
    assert -9998 == _sort_credit("Uh-oh, no date!")
    assert -2005 == _sort_credit("1990 1991 2002 1993 1994 2005 1996 1997 2001")
