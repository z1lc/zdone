import collections
import datetime
import pickle
from datetime import datetime, timedelta
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


def get_habitica():
    return Habitipy({
        'url': 'https://habitica.com',
        'login': current_user.habitica_user_id,
        'password': current_user.habitica_api_token,
        'show_numbers': 'y',
        'show_style': 'wide'
    })


def get_toodledo():
    return Toodledo(
        clientId=kv.get('TOODLEDO_CLIENT_ID'),
        clientSecret=kv.get('TOODLEDO_CLIENT_SECRET'),
        tokenStorage=TokenStoragePostgres(current_user.id),
        scope="basic tasks notes outlines lists share write folders")


def get_habitica_tasks() -> List[ZDTask]:
    # https://habitica.fandom.com/wiki/Cron
    # cron rolls over to next day in the case of uncompleted dailys yesterday
    # however, seems to send back 502's occasionally if called frequently.
    # TODO examine next_due dates for existing tasks to see if we need to call cron() or not
    get_habitica().cron.post()
    habit_list = []
    habitica_day_string = {0: "m", 1: "tu", 2: "w", 3: "th", 4: "f", 5: "s", 6: "su"}[today.weekday()]
    for habit in get_habitica().tasks.user.get(type='dailys'):
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
                    completed_date = datetime.fromtimestamp(int(sorted_history[i - 1]['date'] / 1000),
                                                            tz=pytz.timezone('US/Pacific'))
                    break
                i += 1

        task = ZDTask(
            habit['_id'],
            habit['text'],
            float(habit['notes']),  # use notes field in habitica for estimated minutes
            due,
            completed_date,
            "",
            'habitica',
            [])
        habit_list.append(task)
    return habit_list


def complete_habitica_task(task_id):
    get_habitica().tasks[task_id].score.up.post()


def complete_toodledo_task(task_id):
    tasks = [{
        "id": task_id,
        # https://stackoverflow.com/a/8778548
        "completed": int(datetime.now().replace(tzinfo=datetime.timezone.utc).timestamp()),
        "reschedule": "1"
    }]
    endpoint = "http://api.toodledo.com/3/tasks/edit.php?access_token={access_token}&tasks={tasks}".format(
        access_token=loads(current_user.toodledo_token_json)["access_token"], tasks=dumps(tasks))
    requests.post(url=endpoint)


def get_toodledo_tasks(redis_client) -> List[ZDTask]:
    account = get_toodledo().GetAccount()
    server_last_mod = max(account.lastEditTask.timestamp(), account.lastDeleteTask.timestamp())
    db_last_mod = redis_client.get("toodledo:" + current_user.username + ":last_mod")
    if db_last_mod is None or float(db_last_mod) < server_last_mod:
        zd_tasks = []
        # TODO: add support for repeat
        all_uncomplete = get_toodledo().GetTasks(params={"fields": "duedate,length,parent,note", "comp": 0})
        recent_complete = get_toodledo().GetTasks(params={"fields": "duedate,length,parent,note", "comp": 1,
                                                          "after": int(
                                                              (datetime.today() - timedelta(days=2)).timestamp())})
        parent_id_to_subtask_list: Dict[int, List[ZDSubTask]] = collections.defaultdict(list)

        for task in all_uncomplete + recent_complete:
            if task.parent != 0:
                parent_id_to_subtask_list[task.parent].append(
                    ZDSubTask(str(task.id_), task.title, task.completedDate, task.note, "toodledo"))

        for task in all_uncomplete + recent_complete:
            if task.parent == 0 and (task.completedDate is None or task.completedDate == today):
                zd_tasks.append(
                    ZDTask(str(task.id_), task.title, float(task.length), task.dueDate, task.completedDate,
                           task.note, "toodledo", parent_id_to_subtask_list[task.id_]))
        redis_client.set("toodledo:" + current_user.username, pickle.dumps(zd_tasks))
        redis_client.set("toodledo:" + current_user.username + ":last_mod", server_last_mod)

        return zd_tasks
    else:
        return pickle.loads(redis_client.get("toodledo:" + current_user.username))
