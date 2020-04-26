import collections
import datetime
import pickle
import re
from json import loads, dumps
from typing import List, Dict

import pytz
import requests
from dateutil import parser
from flask import g
from flask_login import current_user
from habitipy import Habitipy
from requests import HTTPError
from toodledo import Toodledo

from app import kv
from app.models import User
from app.storage import TokenStoragePostgres
from app.util import today, today_datetime
from app.ztasks import ZDTask, ZDSubTask


def get_habitica(user: User = current_user):
    return Habitipy({
        'url': 'https://habitica.com',
        'login': user.habitica_user_id,
        'password': user.habitica_api_token,
        'show_numbers': 'y',
        'show_style': 'wide'
    })


def get_toodledo(user: User = current_user):
    return Toodledo(
        clientId=kv.get('TOODLEDO_CLIENT_ID'),
        clientSecret=kv.get('TOODLEDO_CLIENT_SECRET'),
        tokenStorage=TokenStoragePostgres(user.id),
        scope="basic tasks notes outlines lists share write folders")


def needs_to_cron_habitica(dailys):
    dailys_with_history = [daily for daily in dailys if len(daily['history']) > 0]
    most_recent_completed_at = max(
        [max(daily['history'], key=lambda v: v['date'])['date'] for daily in dailys_with_history])
    most_recent_completed_at = datetime.datetime.fromtimestamp(int(most_recent_completed_at / 1000),
                                                               tz=pytz.timezone('US/Pacific'))
    # need to cron if most recent completed at is not today
    return most_recent_completed_at.date() < today()


def get_habitica_tasks(user: User = current_user) -> List[ZDTask]:
    if 'habitica' not in g:
        g.habitica = []
        # https://habitica.fandom.com/wiki/Cron
        # cron rolls over to next day in the case of uncompleted dailys yesterday
        # however, seems to send back 502's occasionally if called frequently.
        try:
            dailys = get_habitica(user).tasks.user.get(type='dailys')
            if needs_to_cron_habitica(dailys):
                get_habitica(user).cron.post()
                dailys = get_habitica(user).tasks.user.get(type='dailys')
        except HTTPError:
            dailys = []

        habit_list = []
        habitica_day_string = {0: "m", 1: "t", 2: "w", 3: "th", 4: "f", 5: "s", 6: "su"}[today().weekday()]
        for habit in dailys:
            if habit['repeat'][habitica_day_string] and not habit['completed']:
                due = today()
            else:
                if any(habit['repeat'].values()):
                    due = parser.parse(habit['nextDue'][0]).date()
                else:  # filter out tasks that are never due
                    continue

            completed_datetime = None
            if habit['completed']:
                completed_datetime = today_datetime()
            else:
                sorted_history = sorted(habit['history'], key=lambda date_plus_val: -date_plus_val['date'])
                i = 1
                while i < len(sorted_history):
                    if sorted_history[i - 1]['value'] > sorted_history[i]['value']:
                        completed_datetime = datetime.datetime.fromtimestamp(int(sorted_history[i - 1]['date'] / 1000),
                                                                             tz=pytz.timezone('US/Pacific'))
                        break
                    i += 1

            sub_tasks = []
            for subtask in habit['checklist']:
                sub_tasks.append(ZDSubTask(
                    subtask['id'],
                    subtask['text'],
                    today() if subtask['completed'] else None,
                    "",
                    "habitica"))

            time_and_notes = habit['notes'].split("\n")
            time = float(time_and_notes[0]) if re.match("^\\d+(\\.\\d+)?$", time_and_notes[0]) else 0
            notes = "\n".join(time_and_notes[1:])

            task = ZDTask(
                habit['_id'],
                habit['text'],
                # use notes field in habitica for estimated minutes
                time,
                due,
                completed_datetime,
                "FREQ=DAILY",
                notes,
                'habitica',
                sub_tasks)
            habit_list.append(task)
            g.habitica = habit_list

    return g.habitica


def complete_habitica_task(task_id, subtask_id, user: User = current_user):
    if subtask_id:
        get_habitica(user).tasks[task_id].checklist[subtask_id].score.post()
    else:
        get_habitica(user).tasks[task_id].score.up.post()


def complete_toodledo_task(task_id, user: User = current_user):
    tasks = [{
        "id": task_id,
        # unclear what timestamp should be used here. manual testing suggested this was the right one
        "completed": int(datetime.datetime(today().year, today().month, today().day).timestamp()),
        "reschedule": "1"
    }]
    endpoint = "http://api.toodledo.com/3/tasks/edit.php?access_token={access_token}&tasks={tasks}".format(
        access_token=loads(user.toodledo_token_json)["access_token"], tasks=dumps(tasks))
    requests.post(url=endpoint)


def add_toodledo_task(name, due_date, length_minutes, user: User = current_user):
    tasks = [{
        "title": name,
        "duedate": int(parser.parse(due_date).timestamp()),
        "duration": length_minutes
    }]
    endpoint = "http://api.toodledo.com/3/tasks/add.php?access_token={access_token}&tasks={tasks}".format(
        access_token=loads(user.toodledo_token_json)["access_token"], tasks=dumps(tasks))
    return requests.post(url=endpoint)


def get_toodledo_tasks(redis_client, user: User = current_user) -> List[ZDTask]:
    if 'toodledo' not in g:
        account = get_toodledo(user).GetAccount()
        last_deleted = account.lastDeleteTask or datetime.datetime.now()
        server_last_mod = max(account.lastEditTask.timestamp(), last_deleted.timestamp())
        db_last_mod = redis_client.get("toodledo:" + user.username + ":last_mod")
        if db_last_mod is None or float(db_last_mod) < server_last_mod:
            # TODO: add support for repeat
            fields = "duedate,length,note,parent,repeat"
            all_uncomplete = get_toodledo(user).GetTasks(params={"fields": fields, "comp": 0})
            recent_complete = get_toodledo(user).GetTasks(
                params={"fields": fields, "comp": 1,
                        "after": int((datetime.datetime.today() - datetime.timedelta(days=2)).timestamp())})
            full_api_response = all_uncomplete + recent_complete
            redis_client.set("toodledo:" + user.username, pickle.dumps(full_api_response))
            redis_client.set("toodledo:" + user.username + ":last_mod", server_last_mod)
        else:
            full_api_response = pickle.loads(redis_client.get("toodledo:" + user.username))

        zd_tasks = []
        parent_id_to_subtask_list: Dict[int, List[ZDSubTask]] = collections.defaultdict(list)
        for task in full_api_response:
            if hasattr(task, "parent") and task.parent != 0:
                parent_id_to_subtask_list[task.parent].append(
                    ZDSubTask(str(task.id_), task.title, task.completedDate, task.note, "toodledo"))

        for task in full_api_response:
            if (not hasattr(task, "parent") or task.parent == 0) and \
                    (task.completedDate is None or task.completedDate == today()):
                zd_tasks.append(
                    ZDTask(str(task.id_), task.title, float(task.length), task.dueDate, task.completedDate,
                           task.repeat, task.note, "toodledo", parent_id_to_subtask_list[task.id_]))

        g.toodledo = zd_tasks

    return g.toodledo
