import datetime
import json
import re
from typing import List, Tuple, Optional

import pytz
from flask import Response
from flask_login import current_user
from tld import get_fld
# watch out, this dependency is actually py-trello
from trello import TrelloClient, trellolist

from app import db
from app.models.base import User
from app.models.tasks import TaskLog, Task
from app.util import failure, success


def do_update_task(update: str,
                   service: str,
                   task_id: str,
                   days: Optional[int],
                   task_raw_name: Optional[str],
                   to_list_id: Optional[str],
                   user: User = current_user) -> Tuple[Response, int]:
    if task_id is None:
        return failure(f"Must pass a valid task_id.")
    if service not in ["trello", "zdone"]:
        return failure(f"Must pass a valid service.")
    if update not in ["complete", "defer", "move"]:
        return failure(f"Must pass a valid update type.")
    if user.current_time_zone is None:
        return failure(f"User {user.username} does not have a time zone setting.")

    log = TaskLog(
        user_id=user.id,
        at=datetime.datetime.utcnow(),
        at_time_zone=user.current_time_zone,
        action=update
    )
    if service == "zdone":
        task = Task.query.filter_by(id=int(task_id)).one()
        log.task_id = task.id
        db.session.add(log)
        if update == "complete":
            task.last_completion = datetime.datetime.now(pytz.timezone(user.current_time_zone))
        elif update == "defer":
            if days is None:
                return failure(f"Need to pass number of days to defer by.")
            else:
                task.defer_until = datetime.datetime.now(pytz.timezone(user.current_time_zone)).date() \
                                   + datetime.timedelta(days=days)
        else:
            failure(f"Update type {update} not supported for zdone.")
        db.session.commit()
        return success()
    elif service == "trello":
        # clear out cache so we force a refresh in case we don't receive the webhook from Trello
        user.cached_trello_data = None
        db.session.commit()
        client = get_trello_client(user)
        if not client:
            return failure(f"Failed to get Trello client for user {user.username}.")

        if update == "complete":
            completed_list_id = \
                [l for l in [board for board in client.list_boards() if board.name == 'Backlogs'][0].list_lists() if
                 l.name == "Completed via zdone"][0].id
            client.get_card(task_id).change_list(completed_list_id)
            log.task_name = task_raw_name
            db.session.add(log)
            db.session.commit()
        elif update == "move":
            if not to_list_id:
                return failure(f"Need to pass what list to move task to.")
            client.get_card(task_id).change_list(to_list_id)
        else:
            return failure(f"Update type '{update}' not supported for Trello.")
        return success()
    else:
        return failure(f"unexpected service type '{service}'")


def get_trello_client(user: User) -> Optional[TrelloClient]:
    if user.trello_api_key and user.trello_api_access_token:
        client = TrelloClient(
            api_key=user.trello_api_key,
            api_secret=user.trello_api_access_token
        )
        return client

    return None


def ensure_trello_setup_idempotent(user: User) -> str:
    to_return = ""
    client = get_trello_client(user)
    if not client:
        return "API key and/or access token not set.<br>"
    else:
        to_return += "API key & access token correctly set.<br>"
        maybe_backlogs_board = [board for board in client.list_boards() if board.name == 'Backlogs']
        if not maybe_backlogs_board:
            return "Did not find a board called 'Backlogs'.<br>"
        else:
            backlogs_board = maybe_backlogs_board[0]
            to_return += f"Board with name 'Backlogs' found with id {backlogs_board.id}<br>"

            if not user.trello_member_id:
                to_return += f"Trello member ID not set. Setting to {backlogs_board.owner_members()[0].id}...<br>"
                user.trello_member_id = backlogs_board.owner_members()[0].id
                db.session.commit()
                to_return += f"Trello member ID successfully set to {backlogs_board.owner_members()[0].id}.<br>"
            else:
                to_return += f"Trello member ID is set to {backlogs_board.owner_members()[0].id}.<br>"

            has_zdone_hook = False
            for hook in client.list_hooks(token=user.trello_api_access_token):
                if hook.callback_url == "https://www.zdone.co/trello_webhook" and hook.id_model == backlogs_board.id:
                    has_zdone_hook = True
                    to_return += f"Found zdone webook with id {hook.id}.<br>"

            if not has_zdone_hook:
                to_return += "Creating zdone webhook...<br>"
                try:
                    hook = client.create_hook(
                        callback_url="https://www.zdone.co/trello_webhook",
                        id_model=backlogs_board.id,
                    )
                except Exception as e:
                    to_return += f"Received exception while adding webhook: {e}<br>"
                    to_return += f"Did not succeed in creating webhook!" \
                                 f" It is likely the Trello library is still broken." \
                                 f" You'll probably just have to do this by hand in Postman."
                else:
                    to_return += f"Successfully created zdone webhook with id {hook.id}.<br>"

    return to_return


def get_open_trello_lists(user: User) -> List[trellolist.List]:
    client = get_trello_client(user)
    if client:
        backlog_board = [board for board in client.list_boards() if board.name == 'Backlogs'][0]
        return backlog_board.list_lists('open')
    return []


def get_updated_trello_cards(user: User, force_refresh: bool = False):
    if force_refresh or user.cached_trello_data is None:
        items = []
        for tlist in get_open_trello_lists(user):
            for tcard in tlist.list_cards():
                pretty_name = tcard.name
                urls = re.findall(r'(https?://[^\s]+)', pretty_name)
                for url in urls:
                    pretty_name = pretty_name.replace(url, f'<a href="{url}">{get_fld(url)} 🔗</a>')
                item = {
                    "id": tcard.id,
                    "service": "trello",
                    "raw_name": f"{tcard.name}",
                    "name": f"<a href='{tcard.url}'>{tlist.name}</a>: {pretty_name}",
                    "note": tcard.description.replace('\n', '<br>'),
                    "list_name": tlist.name,
                    "subtask_id": None,
                    "length_minutes": None,
                }
                items.append(item)

        user.cached_trello_data = json.dumps(items)
        db.session.commit()

    return json.loads(user.cached_trello_data)
