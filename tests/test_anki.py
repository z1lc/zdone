import uuid

from app.anki import get_track_model, get_artist_model, AnkiCard, clean_track_name
from app.models import User

rsanek_user = User(id=1,
                   username="rsanek",
                   email="rsanek@gmail.com",
                   api_key=uuid.uuid4(),
                   uses_rsAnki_javascript=True)


def test_track_templates_reasonable(tmpdir):
    track = get_track_model(rsanek_user)
    assert len(track.templates) == len([e for e in AnkiCard if e.directory == 'spotify_track'])
    for template in track.templates:
        name = template['name']
        question = template['qfmt']
        answer = template['afmt']

        assert '>' in name
        assert str(rsanek_user.api_key) in question
        assert "rsAnswer" in answer
        assert "_AnkiLibrary.js" in question

    artist = get_artist_model(rsanek_user)
    assert len(artist.templates) == len([e for e in AnkiCard if e.directory == 'spotify_artist'])
    for template in artist.templates:
        assert '>' or 'Extra' in template['name']


def test_clean_track_name():
    assert "Twist And Shout" == clean_track_name("Twist And Shout - Remastered 2009")
    assert "Juicy" == clean_track_name("Juicy - 2005 Remaster")
    assert "Hey Jude" == clean_track_name("Hey Jude - Remastered 2015")

    assert "Good Vibrations" == clean_track_name("Good Vibrations - Remastered")
    assert "Wouldn't It Be Nice" == clean_track_name("Wouldn't It Be Nice - Stereo Mix")
    assert "Need a Friend" == clean_track_name("Need a Friend - Original Mix")

    assert "That Way" == clean_track_name("That Way - Bonus Track")

    assert "Get Lucky" == clean_track_name("Get Lucky (feat. Pharrell Williams & Nile Rodgers) - Radio Edit")
    assert "Instant Crush" == clean_track_name("Instant Crush (feat. Julian Casablancas)")
    assert "Sucker For Pain" == clean_track_name(
        "Sucker For Pain (with Wiz Khalifa, Imagine Dragons, Logic & Ty Dolla $ign feat. X Ambassadors)")

    assert "No Place" == clean_track_name("No Place - Will Clarke Remix")
    assert "Don't" == clean_track_name("Don't - Don Diablo Remix")
    assert "I Don’t Even Know You Anymore" == clean_track_name(
        "I Don’t Even Know You Anymore (feat. Bazzi & Lil Wayne)")

    assert "I Walk the Line" == clean_track_name("I Walk the Line - Stereo Version")
    assert "Ring Of Fire" == clean_track_name("Ring Of Fire - 1988 Version")

    assert "ringtone" == clean_track_name("ringtone (Remix) [feat. Charli XCX, Rico Nasty, Kero Kero Bonito]")
    assert "Mrs. Robinson" == clean_track_name("Mrs. Robinson - From \"The Graduate\" Soundtrack")
    assert "Only The Young" == clean_track_name("Only The Young - Featured in Miss Americana")
    assert "La vie en rose" == clean_track_name("La vie en rose - Single Version")
    assert "Dream A Little Dream Of Me" == clean_track_name("Dream A Little Dream Of Me - With Introduction")
    assert "Life Is Good" == clean_track_name("Life Is Good - Remix")
    assert "Dear Boy" == clean_track_name("Dear Boy - Avicii By Avicii")
    assert "Into the Unknown" == clean_track_name("Into the Unknown - Panic! At The Disco Version")
    assert "Diving with Whales" == clean_track_name("Diving with Whales - Daniel Portman Radio Mix")
    assert "Antidote" == clean_track_name("Antidote - Extended")
