import pytest
from genanki import Deck

from app.card_generation.untappd import generate_beer
from app.models.base import User
from card_generation.anki import SPOTIFY_TRACK_DECK_ID


@pytest.mark.skip(reason="integration")
def test_generate_beer():
    generate_beer(User.query.filter_by(username="rsanek").one(), Deck(SPOTIFY_TRACK_DECK_ID, "Spotify Tracks"), [])
