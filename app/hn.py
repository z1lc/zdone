from datetime import datetime
from typing import List

import humanize

from app import db
from app.models.base import User
from app.models.hn import HnStory, HnReadLog


def get_unread_stories(user: User) -> List[HnStory]:
    read_logs = db.session.query(HnReadLog).filter_by(user_id=user.id).subquery()
    stories = [s for s in db.session.query(HnStory)
        .outerjoin(read_logs)
        .filter(read_logs.c.id == None)
        .filter(HnStory.score >= 100)
        .order_by(HnStory.score.desc())  # type: ignore
        .all()]
    for story in stories:
        story.posted_at = humanize.naturaltime(datetime.now() - story.posted_at)
    return stories
