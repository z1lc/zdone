from app import db
from app.models.base import kv


def get(key: str) -> str:
    maybe_kv = kv.query.filter_by(k=key).one_or_none()
    return maybe_kv.v if maybe_kv else None


def put(key: str, value: str) -> None:
    maybe_kv = kv.query.filter_by(k=key).one_or_none()
    if maybe_kv:
        maybe_kv.v = value
    else:
        db.session.add(kv(k=key, v=value))
    db.session.commit()
