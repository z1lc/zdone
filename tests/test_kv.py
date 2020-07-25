import pytest

from app import kv


@pytest.mark.skip(reason="integration")
def test_get_put():
    kv.put("a", "b")
    assert "b" == kv.get("a")
