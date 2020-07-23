import datetime
import pickle
from typing import List, Tuple

import pytz
from flask import Response
from flask_login import current_user
# watch out, this dependency is actually py-trello
from trello import TrelloClient, trellolist

from app import redis_client, db
from app.models.base import User
from app.models.tasks import TaskLog, Task
from app.util import failure, success


def do_update_task(update: str,
                   service: str,
                   task_id: str,
                   user: User = current_user) -> Tuple[Response, int]:
    if task_id is None:
        return failure(f"must pass a valid task_id")
    if service == "zdone":
        task = Task.query.filter_by(id=int(task_id)).one()
        log = TaskLog(
            task_id=task.id,
            at=datetime.datetime.utcnow(),
            at_time_zone=user.current_time_zone,
            action=update
        )
        db.session.add(log)
        if update == "complete":
            task.last_completion = datetime.datetime.now(pytz.timezone(user.current_time_zone))
        elif update == "defer":
            task.defer_until = datetime.datetime.now(pytz.timezone(user.current_time_zone)).date() \
                               + datetime.timedelta(days=3)
        db.session.commit()
        return success()
    elif service == "trello":
        client = TrelloClient(
            api_key=current_user.trello_api_key,
            api_secret=current_user.trello_api_access_token
        )
        client.get_card(task_id).change_list('5efeb6fae7aab58783af4a83')  # completed list
        return success()
    else:
        return failure(f"unexpected service type '{service}'")


def get_open_trello_lists(user: User) -> List[trellolist.List]:
    if user.trello_api_key and user.trello_api_access_token:
        client = TrelloClient(
            api_key=user.trello_api_key,
            api_secret=user.trello_api_access_token
        )
        backlog_board = [board for board in client.list_boards() if board.name == 'Backlogs'][0]

        return backlog_board.list_lists('open')
    return []


def get_updated_trello_cards(user: User, force_refresh: bool = False):
    redis_key = f"trello-{user.username}"
    if force_refresh or redis_client.get(redis_key) is None:
        items = []
        for tlist in get_open_trello_lists(user):
            for tcard in tlist.list_cards():
                item = {
                    "id": tcard.id,
                    "service": "trello",
                    "name": f"<a href='{tcard.url}'>{tlist.name}</a>: {tcard.name}",
                    "note": tcard.description.replace('\n', '<br>'),
                    "list_name": tlist.name,
                    "subtask_id": None,
                    "length_minutes": None,
                }
                items.append(item)

        redis_client.set(redis_key, pickle.dumps(items))

    return pickle.loads(redis_client.get(redis_key))
