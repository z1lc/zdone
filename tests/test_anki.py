import re

import pytest

from app.card_generation.anki import generate_full_apkg, TEST_FILENAME
from app.card_generation.readwise import get_highlight_model
from app.card_generation.spotify import get_track_model, get_artist_model
from app.card_generation.untappd import get_beer_model
from app.card_generation.util import AnkiCard
from app.card_generation.videos import get_video_person_model, get_video_model
from app.card_generation.people_getter import _get_person_model
from utils import TEST_USER


def test_models_reasonable():
    models_and_names = [
        (get_track_model(TEST_USER), "spotify_track"),
        (get_artist_model(TEST_USER), "spotify_artist"),
        (get_video_model(TEST_USER), "video"),
        (get_video_person_model(TEST_USER), "video_person"),
        (get_highlight_model(TEST_USER), "readwise_highlight_cloze"),
        (_get_person_model(TEST_USER), "person"),
        (get_beer_model(TEST_USER), "beer"),
    ]

    for model, name in models_and_names:
        # the number of templates in the model should match the number of AnkiCard enums defined for the same directory
        assert len(model.templates) == len([e for e in AnkiCard if e.directory == name])

        # the first field should match the id field name specified in the AnkiCard enums for the same directory
        assert all([e.id_field_name == model.fields[0]["name"] for e in AnkiCard if e.directory == name])

        for template in model.templates:
            question = template["qfmt"]
            answer = template["afmt"]

            assert ">" or "Extra" in template["name"]

            # if we're dealing with an 'extra' type of template, we may not have a question at all.
            if question:
                # ensure we're using the shared AnkiLibrary for image resizing, text recoloring...
                assert "_AnkiLibrary.js" in question

                # ensure there's either an rsAnswer or rsAnswerMulti css class applied OR we're using a Cloze note type
                assert "rsAnswer" or "{{cloze:" in answer
                # ensure all cards have logging on their back
                # TODO remove if statement once person cards have proper ID
                if name != "person":
                    assert f"https://www.zdone.co/api/{TEST_USER.api_key}/log/" in answer

                # ensure there's a textPart followed by an imagePart
                assert re.search(
                    r"<div id=\"textPart\"[\s\S]*?</div>[\s\S]*?<div id=\"imagePart\"[\s\S]*?</div>", question
                ), question
                assert re.search(
                    r"<div id=\"textPart\"[\s\S]*?</div>[\s\S]*?<div id=\"imagePart\"[\s\S]*?</div>", answer
                ), answer


@pytest.mark.skip(reason="integration")
def test_generate_full_apkg():
    generate_full_apkg(TEST_USER, TEST_FILENAME)
