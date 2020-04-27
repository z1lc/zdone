import uuid

from genanki import Model

from app.anki import get_track_model
from app.models import User

rsanek_user = User(id=1, username="rsanek", email="rsanek@gmail.com", api_key=uuid.uuid4())


def test_track_templates_contain_api_key(tmpdir):
    model: Model = get_track_model(rsanek_user)
    assert len(model.templates) == 2
    for template in model.templates:
        assert str(rsanek_user.api_key) in template['qfmt']
