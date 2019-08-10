import pickle
from datetime import datetime, timedelta, timezone
from json import loads, dumps
from typing import List

import requests
from dateutil import parser
from habitipy import Habitipy
from toodledo import Toodledo

from . import kv
from .storage import TokenStoragePostgres
from .util import today
from .ztasks import ZDTask

habitica = Habitipy({
    'url': 'https://habitica.com',
    'login': kv.get('HABITICA_USER_ID'),
    'password': kv.get('HABITICA_API_TOKEN'),
    'show_numbers': 'y',
    'show_style': 'wide'
})
toodledo = Toodledo(
    clientId=kv.get('TOODLEDO_CLIENT_ID'),
    clientSecret=kv.get('TOODLEDO_CLIENT_SECRET'),
    tokenStorage=TokenStoragePostgres("TOODLEDO_TOKEN_JSON"),
    scope="basic tasks notes outlines lists share write folders")


def get_habitica_daily_ordering() -> List[str]:
    return habitica.user.get(userFields='tasksOrder')['tasksOrder']['dailys']


def get_habitica_tasks() -> List[ZDTask]:
    # cron rolls over to next day in the case of uncompleted dailys yesterday
    # idempotent so fine to call every time
    habitica.cron.post()
    habit_list = []
    habitica_day_string = {0: "m", 1: "tu", 2: "w", 3: "th", 4: "f", 5: "s", 6: "su"}[today.weekday()]
    for habit in habitica.tasks.user.get(type='dailys'):
        if habit['repeat'][habitica_day_string] and not habit['completed']:
            due = today
        else:
            due = parser.parse(habit['nextDue'][0], '').date()
        task = ZDTask(
            habit['_id'],
            habit['text'],
            float(habit['notes']),  # use notes field in habitica for estimated minutes
            due,
            habit['completed'],
            'habitica')
        habit_list.append(task)
    return habit_list


def complete_habitica_task(task_id):
    habitica.tasks[task_id].score.up.post()


def complete_toodledo_task(task_id):
    tasks = [{
        "id": task_id,
        # https://stackoverflow.com/a/8778548
        "completed": int(datetime.now().replace(tzinfo=timezone.utc).timestamp()),
        "reschedule": "1"
    }]
    endpoint = "http://api.toodledo.com/3/tasks/edit.php?access_token={access_token}&tasks={tasks}".format(
        access_token=loads(kv.get("TOODLEDO_TOKEN_JSON"))["access_token"], tasks=dumps(tasks))
    requests.post(url=endpoint)


def get_toodledo_tasks(redis_client) -> List[ZDTask]:
    account = toodledo.GetAccount()
    server_last_mod = max(account.lastEditTask.timestamp(), account.lastDeleteTask.timestamp())
    db_last_mod = redis_client.get("toodledo:last_mod")
    if db_last_mod is None or float(db_last_mod) < server_last_mod:
        zd_tasks = []
        # TODO: add support for repeat,parent
        all_uncomplete = toodledo.GetTasks(params={"fields": "duedate,length,", "comp": 0})
        recent_complete = toodledo.GetTasks(params={"fields": "duedate,length", "comp": 1,
                                                    "after": int((datetime.today() - timedelta(days=2)).timestamp())})
        for task in all_uncomplete + recent_complete:
            if task.completedDate is None or task.completedDate == today:
                zd_tasks.append(
                    ZDTask(str(task.id_), task.title, float(task.length), task.dueDate, task.completedDate == today,
                           "toodledo"))
        redis_client.set("toodledo", pickle.dumps(zd_tasks))
        redis_client.set("toodledo:last_mod", server_last_mod)

        return zd_tasks
    else:
        return pickle.loads(redis_client.get("toodledo"))
