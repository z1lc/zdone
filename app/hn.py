import datetime
from typing import List, Tuple

import humanize

from app import db
from app.models.base import User
from app.models.hn import HnStory, HnReadLog
from app.util import today


def get_unread_stories(user: User) -> List[HnStory]:
    read_logs = db.session.query(HnReadLog).filter_by(user_id=user.id).subquery()
    stories = [s for s in db.session.query(HnStory)
        .outerjoin(read_logs)
        .filter(read_logs.c.id == None)
        .filter(HnStory.score >= 100)
        .order_by(HnStory.score.desc())  # type: ignore
        .limit(100)
        .all()]
    for story in stories:
        story.posted_at = humanize.naturaltime(datetime.datetime.now() - story.posted_at)
    return stories


def get_total_and_average_reads_per_week(user: User) -> Tuple[float, float]:
    sql = f"""

select count(*), count(*) / extract(days from (current_date - min(at))) * 7
from hn_read_logs
where user_id = {user.id}"""
    results = list(db.engine.execute(sql))
    return (round(results[0][0], 1), round(results[0][1], 1)) if results else (0, 0)


def get_hn_articles_from_this_week(user: User) -> List[HnStory]:
    return db.session.query(HnStory) \
        .join(HnReadLog) \
        .filter(HnReadLog.user_id == user.id) \
        .filter(HnReadLog.at >= today() - datetime.timedelta(days=7)) \
        .order_by(HnReadLog.at.desc()).all()  # type: ignore
