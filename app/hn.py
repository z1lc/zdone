from typing import List

from app import db
from app.models.base import User
from app.models.hn import HnStory, HnReadLog


def get_unread_stories(user: User) -> List[HnStory]:
    return [story for story, log in db.session.query(HnStory, HnReadLog)
        .outerjoin(HnReadLog)
        .filter(HnStory.score >= 100)
        .order_by(HnStory.score.desc())
        .all() if log is None]
