import collections
import datetime
import pickle
import re
from json import loads, dumps
from typing import List, Dict

import pytz
import requests
from dateutil import parser
from flask_login import current_user
from habitipy import Habitipy
from toodledo import Toodledo

from . import kv
from .storage import TokenStoragePostgres
from .util import today
from .ztasks import ZDTask, ZDSubTask


def get_habitica(user=current_user):
    return Habitipy({
        'url': 'https://habitica.com',
        'login': user.habitica_user_id,
        'password': user.habitica_api_token,
        'show_numbers': 'y',
        'show_style': 'wide'
    })


def get_toodledo(user=current_user):
    return Toodledo(
        clientId=kv.get('TOODLEDO_CLIENT_ID'),
        clientSecret=kv.get('TOODLEDO_CLIENT_SECRET'),
        tokenStorage=TokenStoragePostgres(user.id),
        scope="basic tasks notes outlines lists share write folders")


def get_habitica_tasks(user=current_user) -> List[ZDTask]:
    # https://habitica.fandom.com/wiki/Cron
    # cron rolls over to next day in the case of uncompleted dailys yesterday
    # however, seems to send back 502's occasionally if called frequently.
    # TODO examine next_due dates for existing tasks to see if we need to call cron() or not
    get_habitica(user).cron.post()
    habit_list = []
    habitica_day_string = {0: "m", 1: "tu", 2: "w", 3: "th", 4: "f", 5: "s", 6: "su"}[today.weekday()]
    for habit in get_habitica(user).tasks.user.get(type='dailys'):
        if habit['repeat'][habitica_day_string] and not habit['completed']:
            due = today
        else:
            due = parser.parse(habit['nextDue'][0], '').date()

        completed_date = None
        if habit['completed']:
            completed_date = today
        else:
            sorted_history = sorted(habit['history'], key=lambda date_plus_val: -date_plus_val['date'])
            i = 1
            while i < len(sorted_history):
                if sorted_history[i - 1]['value'] > sorted_history[i]['value']:
                    completed_date = datetime.datetime.fromtimestamp(int(sorted_history[i - 1]['date'] / 1000),
                                                                     tz=pytz.timezone('US/Pacific'))
                    break
                i += 1

        task = ZDTask(
            habit['_id'],
            habit['text'],
            # use notes field in habitica for estimated minutes
            float(habit['notes']) if re.match("^\\d+(\\.\\d+)?$", habit['notes']) else 0,
            due,
            completed_date,
            "",
            'habitica',
            [])
        habit_list.append(task)
    return habit_list


def complete_habitica_task(task_id, user=current_user):
    get_habitica(user).tasks[task_id].score.up.post()


def complete_toodledo_task(task_id, user=current_user):
    tasks = [{
        "id": task_id,
        # unclear what timestamp should be used here. manual testing suggested this was the right one
        "completed": int(datetime.datetime.now().timestamp()),
        "reschedule": "1"
    }]
    endpoint = "http://api.toodledo.com/3/tasks/edit.php?access_token={access_token}&tasks={tasks}".format(
        access_token=loads(user.toodledo_token_json)["access_token"], tasks=dumps(tasks))
    requests.post(url=endpoint)


def get_toodledo_tasks(redis_client, user=current_user) -> List[ZDTask]:
    account = get_toodledo(user).GetAccount()
    server_last_mod = max(account.lastEditTask.timestamp(), account.lastDeleteTask.timestamp())
    db_last_mod = redis_client.get("toodledo:" + user.username + ":last_mod")
    if db_last_mod is None or float(db_last_mod) < server_last_mod:
        # TODO: add support for repeat
        all_uncomplete = get_toodledo().GetTasks(params={"fields": "duedate,length,parent,note", "comp": 0})
        recent_complete = get_toodledo().GetTasks(
            params={"fields": "duedate,length,parent,note", "comp": 1,
                    "after": int((datetime.datetime.today() - datetime.timedelta(days=2)).timestamp())})
        full_api_response = all_uncomplete + recent_complete
        redis_client.set("toodledo:" + user.username, pickle.dumps(full_api_response))
        redis_client.set("toodledo:" + user.username + ":last_mod", server_last_mod)
    else:
        full_api_response = pickle.loads(redis_client.get("toodledo:" + user.username))

    zd_tasks = []
    parent_id_to_subtask_list: Dict[int, List[ZDSubTask]] = collections.defaultdict(list)
    for task in full_api_response:
        if task.parent != 0:
            parent_id_to_subtask_list[task.parent].append(
                ZDSubTask(str(task.id_), task.title, task.completedDate, task.note, "toodledo"))

    for task in full_api_response:
        if task.parent == 0 and (task.completedDate is None or task.completedDate == today):
            zd_tasks.append(
                ZDTask(str(task.id_), task.title, float(task.length), task.dueDate, task.completedDate,
                       task.note, "toodledo", parent_id_to_subtask_list[task.id_]))

    return zd_tasks
