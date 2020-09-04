import json
from datetime import datetime, timedelta

import requests
from sqlalchemy import or_, and_

from app import kv, db
from app.log import log
from app.models.hn import HnStory

MAX_ITEM_RETRIES = 3


def get_item(item_id):
    try_count = 0
    while try_count < MAX_ITEM_RETRIES:
        try_count += 1
        try:
            response = json.loads(requests.get(
                f"https://hacker-news.firebaseio.com/v0/item/{item_id}.json?print=pretty").text)
            if response and response['type'] == "story" and "deleted" not in response:
                return response
            else:
                break
        except Exception as e:
            log(f'Received exception {e}. Will re-try item {item_id} {MAX_ITEM_RETRIES - try_count} more times.')
    return None


if __name__ == '__main__':
    # refresh stories every day until they are archived by HN, which is 2 weeks after they are posted
    log("Beginning story refresh...")
    now = datetime.utcnow()
    # avoid ever refreshing more than hourly (but use 30 minutes here just to be safe in case we have a long run)
    stories = HnStory.query.filter(HnStory.last_refreshed_at < now - timedelta(minutes=30)).filter(or_(
        # hourly within first 12 hours
        HnStory.posted_at >= now - timedelta(hours=12),
        # daily within first week
        and_(HnStory.posted_at >= (now - timedelta(days=7)), HnStory.last_refreshed_at <= (now - timedelta(days=1))),
        # then, one final time before getting archived
        and_(HnStory.posted_at < (now - timedelta(days=14)),
             HnStory.last_refreshed_at < (HnStory.posted_at + timedelta(days=14))),
    )).all()
    log(f"Will refresh {len(stories)} stories.")
    for i, story in enumerate(stories):
        if i % 10 == 0:
            log(f"On item #{i}; {round(i * 100 / len(stories))}% done.")
        item = get_item(story.id)
        if item:
            story.comments = item.get('descendants', 0)
            story.score = item['score']
            story.title = item['title']
            story.url = item.get('url', f"https://news.ycombinator.com/item?id={item['id']}")
            story.last_refreshed_at = datetime.utcnow()
        else:
            # item was probably deleted, because of spam or whatever
            db.session.delete(story)
        db.session.commit()
    log("Completed story refresh.")

    log("Beginning new story update...")
    current_item = int(kv.get('HN_ITEM_OFFSET'))
    max_item = int(requests.get('https://hacker-news.firebaseio.com/v0/maxitem.json').text)
    total_to_do = max_item - current_item
    log(f"Current max is #{max_item}, which is {total_to_do} ahead of current item #{current_item}.")
    while current_item < max_item:
        if current_item % 10 == 0:
            log(f"On item #{current_item}; {-round((((max_item - current_item) / total_to_do) - 1) * 100)}% done.")
        item = get_item(current_item)
        if item:
            db.session.add(HnStory(
                id=item['id'],
                comments=item.get('descendants', 0),
                score=item['score'],
                title=item['title'],
                url=item.get('url', f"https://news.ycombinator.com/item?id={item['id']}"),
                posted_at=datetime.fromtimestamp(item['time']),
                last_refreshed_at=datetime.utcnow(),
            ))
            db.session.commit()
        current_item += 1
        kv.put('HN_ITEM_OFFSET', str(current_item))
    log("Completed new story update.")
