from app.card_generation.readwise import get_highlight_model
from app.card_generation.spotify import get_track_model, get_artist_model
from app.card_generation.util import AnkiCard
from app.card_generation.videos import get_video_person_model, get_video_model
from app.models.base import User

rsanek_user = User(id=1,
                   username="rsanek",
                   email="rsanek@gmail.com",
                   api_key='api-key-rsanek-1234',
                   uses_rsAnki_javascript=True)


def test_models_reasonable():
    models_and_names = [
        (get_track_model(rsanek_user), 'spotify_track'),
        (get_artist_model(rsanek_user), 'spotify_artist'),
        (get_video_model(rsanek_user), 'video'),
        (get_video_person_model(rsanek_user), 'video_person'),
        (get_highlight_model(rsanek_user), 'readwise_highlight_cloze'),
    ]

    for model, name in models_and_names:
        # the number of templates in the model should match the number of AnkiCard enums defined for the same directory
        assert len(model.templates) == len([e for e in AnkiCard if e.directory == name])

        # the first field should match the id field name specified in the AnkiCard enums for the same directory
        assert all([e.id_field_name == model.fields[0]['name'] for e in AnkiCard if e.directory == name])

        for template in model.templates:
            question = template['qfmt']
            answer = template['afmt']

            assert '>' or 'Extra' in template['name']

            # if we're dealing with an 'extra' type of template, we may not have a question at all.
            if question:
                # ensure we're using the shared AnkiLibrary for image resizing, text recoloring...
                assert "_AnkiLibrary.js" in question

                # ensure there's either an rsAnswer or rsAnswerMulti css class applied OR we're using a Cloze note type
                assert "rsAnswer" or "{{cloze:" in answer
                # ensure all cards have logging on their back
                assert "https://www.zdone.co/api/api-key-rsanek-1234/log/" in answer
