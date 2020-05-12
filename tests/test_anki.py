import uuid

from app.anki import get_track_model, get_artist_model, AnkiCard
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
