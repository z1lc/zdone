from unittest import TestCase

import pytest

from app.models.base import User
from app.scheduled.refresh_data_generate_apkgs_and_upload_to_b2 import refresh_user


class Test(TestCase):
    @pytest.mark.skip(reason="integration")
    def test_refresh_user(self):
        refresh_user(User.query.filter_by(username="demo").one())
