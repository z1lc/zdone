import json
from datetime import datetime

import requests

from app import kv, db
from app.models.hn import HnStory

if __name__ == '__main__':
    current_item = int(kv.get('HN_ITEM_OFFSET'))
    max_item = int(requests.get('https://hacker-news.firebaseio.com/v0/maxitem.json').text)
    while current_item < max_item:
        item = json.loads(requests.get(
            f"https://hacker-news.firebaseio.com/v0/item/{current_item}.json?print=pretty").text)
        if item and item['type'] == "story" and "deleted" not in item:
            db.session.add(HnStory(
                id=item['id'],
                comments=item.get('descendants', 0),
                score=item['score'],
                title=item['title'],
                url=item.get('url', f"https://news.ycombinator.com/item?id={item['id']}"),
                posted_at=datetime.fromtimestamp(item['time']),
            ))
            db.session.commit()
        current_item += 1
        kv.put('HN_ITEM_OFFSET', str(current_item))
