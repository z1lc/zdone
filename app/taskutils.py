import collections
import datetime
import pickle
import re
from json import loads, dumps
from typing import List, Dict, Tuple, Optional

import pytz
import requests
from dateutil import parser
from flask import g, Response
from flask_login import current_user
from habitipy import Habitipy
from requests import HTTPError
from toodledo import Toodledo
# watch out, this dependency is actually py-trello
from trello import TrelloClient, trellolist

from app import kv, redis_client, db, socketio
from app.models import User, TaskCompletion
from app.storage import TokenStoragePostgres
from app.util import today, today_datetime, failure, success, JsonDict
from app.ztasks import ZDTask, ZDSubTask

TOODLEDO_UNORDERED_TASKS_PLACEHOLDER: ZDTask = ZDTask(
    "-1", "[all unordered Toodledo Tasks]", 0, None, None, "", "", "unorderedToodledo", [])


def get_all_tasks(user: User = current_user) -> List[ZDTask]:
    return get_toodledo_tasks(redis_client, user) + get_habitica_tasks(user)


def get_task_order_from_db(order_type: str, user: User = current_user) -> Tuple[List[ZDTask], List[ZDTask]]:
    currently_sorted_in_db = getattr(user, order_type)
    if currently_sorted_in_db:
        currently_sorted_in_db = currently_sorted_in_db.split("|||")
    else:
        currently_sorted_in_db = []
    sorted_tasks, unsorted_tasks = [], []
    all_tasks: List[ZDTask] = get_all_tasks(user)
    task_map = {t.name: t for t in all_tasks}
    task_map[TOODLEDO_UNORDERED_TASKS_PLACEHOLDER.name] = TOODLEDO_UNORDERED_TASKS_PLACEHOLDER
    for name in currently_sorted_in_db:
        if name in task_map:
            sorted_tasks.append(task_map[name])
            del task_map[name]

    for task in task_map.values():
        if task.is_repeating():
            unsorted_tasks.append(task)

    if TOODLEDO_UNORDERED_TASKS_PLACEHOLDER in unsorted_tasks:
        del unsorted_tasks[unsorted_tasks.index(TOODLEDO_UNORDERED_TASKS_PLACEHOLDER)]

    return sorted_tasks, unsorted_tasks


def do_update_task(update: str,
                   service: str,
                   task_id: str,
                   subtask_id: str,
                   duration_seconds: int = 0,
                   user: User = current_user) -> Tuple[Response, int]:
    if update == "defer":
        redis_client.append("hidden:" + user.username + ":" + str(today()), (task_id + "|||").encode())
        redis_client.expire("hidden:" + user.username + ":" + str(today()), datetime.timedelta(days=7))
        # can no longer use cached tasks since we have to re-sort
        redis_client.delete("toodledo:" + user.username + ":last_mod")
    elif update == "complete":
        if service == "habitica":
            complete_habitica_task(task_id, subtask_id, user)
        elif service == "toodledo":
            if subtask_id:
                complete_toodledo_task(subtask_id, user)
            else:
                complete_toodledo_task(task_id, user)
        else:
            return failure(f"unexpected service type '{service}'")

        task_completion = TaskCompletion(user_id=user.id, service=service, task_id=task_id, subtask_id=subtask_id,
                                         duration_seconds=duration_seconds, at=datetime.datetime.now())
        db.session.add(task_completion)
        db.session.commit()
    else:
        return failure(f"unexpected update type '{update}'")

    length = 0.0
    if not subtask_id:
        length = [t.length_minutes for i, t in enumerate(get_all_tasks(user))
                  if t.service == service and t.id == task_id][0]
    socketio.emit(user.api_key, {
        'update': update,
        'service': service,
        'task_id': task_id,
        'subtask_id': subtask_id if subtask_id else '',
        'length_minutes': length
    })
    return success()


def do_update_time(time: int, user: User = current_user) -> Tuple[Response, int]:
    user.maximum_minutes_per_day = max(0, min(1440, time))
    db.session.commit()
    return success()


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


def needs_to_cron_habitica(dailys: List[JsonDict]) -> bool:
    dailys_with_history: List[JsonDict] = [daily for daily in dailys if len(daily['history']) > 0]
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
            dailys: List[JsonDict] = get_habitica(user).tasks.user.get(type='dailys')
            if needs_to_cron_habitica(dailys):
                get_habitica(user).cron.post()
                dailys = get_habitica(user).tasks.user.get(type='dailys')
        except HTTPError:
            dailys = []

        habit_list: List[ZDTask] = []
        habitica_day_string: str = {0: "m", 1: "t", 2: "w", 3: "th", 4: "f", 5: "s", 6: "su"}[today().weekday()]
        for habit in dailys:
            due: datetime.date
            if habit['repeat'][habitica_day_string] and not habit['completed']:
                due = today()
            else:
                if any(habit['repeat'].values()):
                    due = parser.parse(habit['nextDue'][0]).date()
                else:  # filter out tasks that are never due
                    continue

            completed_datetime: Optional[datetime.datetime] = None
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

            sub_tasks: List[ZDSubTask] = []
            for subtask in habit['checklist']:
                sub_tasks.append(ZDSubTask(
                    subtask['id'],
                    subtask['text'],
                    today_datetime() if subtask['completed'] else None,
                    "",
                    "habitica"))

            time_and_notes: str = habit['notes'].split("\n")
            time: float = float(time_and_notes[0]) if re.match("^\\d+(\\.\\d+)?$", time_and_notes[0]) else 0.0
            notes: str = "\n".join(time_and_notes[1:])

            task: ZDTask = ZDTask(
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


def complete_habitica_task(task_id: str, subtask_id: str, user: User = current_user) -> None:
    if subtask_id:
        get_habitica(user).tasks[task_id].checklist[subtask_id].score.post()
    else:
        get_habitica(user).tasks[task_id].score.up.post()


def complete_toodledo_task(task_id, user: User = current_user) -> requests.Response:
    tasks: List[JsonDict] = [{
        "id": task_id,
        # unclear what timestamp should be used here. manual testing suggested this was the right one
        "completed": int(datetime.datetime(today().year, today().month, today().day).timestamp()),
        "reschedule": "1"
    }]
    endpoint: str = f"http://api.toodledo.com/3/tasks/edit.php?access_token={loads(user.toodledo_token_json)}" \
                    f"&tasks={dumps(tasks)}"
    return requests.post(url=endpoint)


def add_toodledo_task(name, due_date, length_minutes, user: User = current_user) -> requests.Response:
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


def get_homepage_info(user: User = current_user, skew_sort: bool = False) -> JsonDict:
    minutes_completed_today = 0.0
    tasks_completed, tasks_to_do, tasks_backlog, nonrecurring_tasks_coming_up = [], [], [], []
    prioritized_tasks, unprioritized_tasks = get_task_order_from_db("priorities", user)
    for task in prioritized_tasks:
        if task.completed_today() and task not in tasks_completed:
            minutes_completed_today += task.length_minutes
            tasks_completed.append(task)

    task_ids_to_hide = redis_client.get("hidden:" + user.username + ":" + str(today()))
    task_ids_to_hide = [] if task_ids_to_hide is None else task_ids_to_hide.decode().split("|||")

    total_minutes = user.maximum_minutes_per_day
    minutes_left_to_schedule = total_minutes - minutes_completed_today

    i = 0
    minutes_allocated = 0.0
    all_tasks: List[ZDTask] = get_all_tasks(user)
    # try sorting by skew
    if skew_sort:
        all_tasks.sort(key=lambda t: (t.skew, -t.interval), reverse=True)
    while i < len(all_tasks):
        task = all_tasks[i]
        if task.id not in task_ids_to_hide \
                and not task.completed_today():
            if task.due_date is not None and task.due_date <= today():
                # add 4 minutes to allow some space for non-round-number tasks to be scheduled
                if task.length_minutes <= (minutes_left_to_schedule + 4) and task not in tasks_to_do:
                    tasks_to_do.append(task)
                    minutes_left_to_schedule -= task.length_minutes
                    minutes_allocated += task.length_minutes
                elif task not in tasks_backlog:
                    tasks_backlog.append(task)
            elif not task.is_repeating() and \
                    (task.due_date is not None and task.due_date <= (today() + datetime.timedelta(days=1))) and \
                    task not in nonrecurring_tasks_coming_up:
                nonrecurring_tasks_coming_up.append(task)
        i += 1

    ordering = [t.name for t in get_task_order_from_db("dependencies", user)[0]]
    sorted_tasks_to_do: List[Tuple[int, ZDTask]] = []  # int in Tuple is priority; lower is better
    for task in tasks_to_do:
        if task.name in ordering:
            sorted_tasks_to_do.append((ordering.index(task.name), task))
        else:
            sorted_tasks_to_do.append((ordering.index(TOODLEDO_UNORDERED_TASKS_PLACEHOLDER.name)
                                       if TOODLEDO_UNORDERED_TASKS_PLACEHOLDER.name in ordering else 0,
                                       task))

    sorted_tasks_to_do.sort(key=lambda tup: tup[0])

    times = {
        'minutes_completed_today': minutes_completed_today,
        'minutes_allocated': minutes_allocated,
        'maximum_minutes_per_day': user.maximum_minutes_per_day
    }
    denom = times['minutes_completed_today'] + times['minutes_allocated']
    percent_done = int(times['minutes_completed_today'] * 100 / denom) if denom > 0 else 0
    tasks_without_required_fields = get_tasks_without_required_fields(all_tasks)
    return {
        "tasks_completed": list(tasks_completed),
        "tasks_to_do": tasks_to_do if skew_sort else [task for _, task in sorted_tasks_to_do],
        "tasks_backlog": list(tasks_backlog),
        "tasks_without_required_fields": tasks_without_required_fields,
        "nonrecurring_tasks_coming_up": list(nonrecurring_tasks_coming_up),
        "times": times,
        "num_unsorted_tasks": len(unprioritized_tasks),
        "percentage": min(100, max(0, percent_done)),
        "background": "red !important" if times['minutes_completed_today'] < 30 else "#2196F3 !important"
    }


def get_tasks_without_required_fields(all_tasks: List[ZDTask]) -> List[ZDTask]:
    bad_tasks = []
    for task in all_tasks:
        if task.completed_datetime is None:
            if (task.length_minutes is None or task.length_minutes == 0) or \
                    task.due_date is None:
                bad_tasks.append(task)

    return bad_tasks


def get_open_trello_lists() -> List[trellolist.List]:
    if current_user.trello_api_key and current_user.trello_api_access_token:
        client = TrelloClient(
            api_key=current_user.trello_api_key,
            api_secret=current_user.trello_api_access_token
        )
        backlog_board = [board for board in client.list_boards() if board.name == 'Backlogs'][0]

        return backlog_board.list_lists('open')
    return []
