import pytest

from app.card_generation.spotify import clean_album_name, clean_track_name
from app.models.base import User
from app.spotify import update_spotify_anki_playlist


@pytest.mark.skip(reason="integration")
def test_send_and_log_notification_integration():
    update_spotify_anki_playlist(User.query.filter_by(username="rsanek").one())


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
        "Sucker For Pain (with Wiz Khalifa, Imagine Dragons, Logic & Ty Dolla $ign feat. X Ambassadors)"
    )

    assert "No Place" == clean_track_name("No Place - Will Clarke Remix")
    assert "Don't" == clean_track_name("Don't - Don Diablo Remix")
    assert "I Don’t Even Know You Anymore" == clean_track_name(
        "I Don’t Even Know You Anymore (feat. Bazzi & Lil Wayne)"
    )

    assert "I Walk the Line" == clean_track_name("I Walk the Line - Stereo Version")
    assert "Ring Of Fire" == clean_track_name("Ring Of Fire - 1988 Version")

    assert "ringtone" == clean_track_name("ringtone (Remix) [feat. Charli XCX, Rico Nasty, Kero Kero Bonito]")
    assert "Mrs. Robinson" == clean_track_name('Mrs. Robinson - From "The Graduate" Soundtrack')
    assert "Only The Young" == clean_track_name("Only The Young - Featured in Miss Americana")
    assert "La vie en rose" == clean_track_name("La vie en rose - Single Version")
    assert "Dream A Little Dream Of Me" == clean_track_name("Dream A Little Dream Of Me - With Introduction")
    assert "Life Is Good" == clean_track_name("Life Is Good - Remix")
    assert "Dear Boy" == clean_track_name("Dear Boy - Avicii By Avicii")
    assert "Into the Unknown" == clean_track_name("Into the Unknown - Panic! At The Disco Version")
    assert "Diving with Whales" == clean_track_name("Diving with Whales - Daniel Portman Radio Mix")
    assert "Antidote" == clean_track_name("Antidote - Extended")
    assert "Satisfaction" == clean_track_name("Satisfaction (Isak Original Extended) - Benny Benassi Presents The Biz")

    assert "Much Better Off" == clean_track_name("Much Better Off - Album Version / Stereo")
    assert "Baby, Baby Don't Cry" == clean_track_name("Baby, Baby Don't Cry - Stereo")
    assert "On My Own" == clean_track_name("On My Own - 2019 remaster")
    assert "No Woman, No Cry" == clean_track_name("No Woman, No Cry - Live At The Lyceum, London/1975")

    assert "Epiphany" == clean_track_name("Epiphany - Edit")
    assert "Folsom Prison Blues" == clean_track_name(
        "Folsom Prison Blues - Live at Folsom State Prison, Folsom, CA - January 1968"
    )


def test_clean_album_name():
    assert "So" == clean_album_name("So (25th Anniversary Deluxe Edition)")
    assert "÷" == clean_album_name("÷ (Deluxe)")
    assert "The Joshua Tree" == clean_album_name("The Joshua Tree (Super Deluxe)")
    assert "Can't Buy the Mood" == clean_album_name("Can't Buy the Mood (Deluxe Edition)")
    assert "Rare" == clean_album_name("Rare (Bonus Track Version)")
    assert "Led Zeppelin IV" == clean_album_name("Led Zeppelin IV (Deluxe Edition; Remaster)")
    assert "Ready to Die" == clean_album_name("Ready to Die (The Remaster)")
    assert "1989" == clean_album_name("1989 (Big Machine Radio Release Special)")
    assert "x" == clean_album_name("x (Wembley Edition)")
    assert "Help!" == clean_album_name("Help! (Remastered)")
    assert "Peter Gabriel 1: Car" == clean_album_name("Peter Gabriel 1: Car (Remastered Version)")
    assert "Caution" == clean_album_name("Caution (Radio Edit)")
    assert "A Star Is Born Soundtrack" == clean_album_name("A Star Is Born Soundtrack (Without Dialogue)")
    assert "My Way" == clean_album_name("My Way (Expanded Edition)")
    assert "Led Zeppelin II" == clean_album_name("Led Zeppelin II (1994 Remaster)")
    assert "Led Zeppelin III" == clean_album_name("Led Zeppelin III (Remaster)")
    assert "Pet Sounds" == clean_album_name("Pet Sounds (Original Mono & Stereo Mix Versions)")
    assert "Discovery" == clean_album_name("Discovery (Deluxe / Remastered 2015)")
    assert "I Walk the Line" == clean_album_name("I Walk the Line (Stereo Version)")
    assert "Lady Soul" == clean_album_name("Lady Soul (With Bonus Selections)")
    assert "Hypnotica" == clean_album_name("Hypnotica (Benny Benassi Presents The Biz)")
    assert "For Lack of a Better Name" == clean_album_name("For Lack of a Better Name (The Extended Mixes)")
    assert "Random Album Title" == clean_album_name("Random Album Title (Unmixed Extended Versions)")
