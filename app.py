from datetime import datetime, timedelta
from typing import List

import pytz
from dateutil import parser
from flask import Flask, render_template, request
from flask_talisman import Talisman
from habitipy import Habitipy
from toodledo import Toodledo

import kv
from storage import TokenStoragePostgres
from uniformtasks import ZDTask

app = Flask(__name__)
Talisman(app)
toodledo = Toodledo(
    clientId=kv.get('TOODLEDO_CLIENT_ID'),
    clientSecret=kv.get('TOODLEDO_CLIENT_SECRET'),
    tokenStorage=TokenStoragePostgres("TOODLEDO_TOKEN_JSON"),
    scope="basic tasks notes outlines lists share write folders")
habitica = Habitipy({
    'url': 'https://habitica.com',
    'login': kv.get('HABITICA_USER_ID'),
    'password': kv.get('HABITICA_API_TOKEN'),
    'show_numbers': 'y',
    'show_style': 'wide'
})
today = datetime.now(pytz.timezone('US/Pacific')).date()
cached_tasks = []


def get_habitica_tasks() -> List[ZDTask]:
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


@app.route('/prioritize')
def show_prioritized_list():
    sorted_tasks, unsorted_tasks = get_sorted_and_unsorted_tasks()

    return render_template('prioritize.html',
                           sorted_tasks=sorted_tasks,
                           unsorted_tasks=unsorted_tasks)


@app.route('/dependencies')
def show_dependency_list():
    return ""


def get_sorted_and_unsorted_tasks() -> (List[ZDTask], List[ZDTask]):
    currently_sorted_in_db = kv.get("priorities").split("|||")
    sorted_tasks, unsorted_tasks = [], []
    all_tasks: List[ZDTask] = get_toodledo_tasks() + get_habitica_tasks()
    all_recurring_tasks = [t for t in all_tasks if t.length_minutes != 0]
    task_map = {t.name: t for t in all_recurring_tasks}
    for name in currently_sorted_in_db:
        if name in task_map:
            sorted_tasks.append(task_map[name])
            del task_map[name]

    for v in task_map.values():
        unsorted_tasks.append(v)

    return sorted_tasks, unsorted_tasks


@app.route('/set_priorities', methods=['POST'])
def update_priorities():
    kv.put("priorities", request.get_json()["priorities"])
    return "{'result': 'success'}"


def get_toodledo_tasks() -> List[ZDTask]:
    zd_tasks = []
    # TODO: add support for repeat,parent
    all_uncomplete = toodledo.GetTasks(params={"fields": "duedate,length,", "comp": 0})
    recent_complete = toodledo.GetTasks(params={"fields": "duedate,length", "comp": 1,
                                                "after": int((datetime.today() - timedelta(days=2)).timestamp())})
    for task in all_uncomplete + recent_complete:
        if task.completedDate is None or task.completedDate == today:
            zd_tasks.append(
                ZDTask(task.id_, task.title, task.length, task.dueDate, task.completedDate == today, "toodledo"))
    global cached_tasks
    if not cached_tasks:
        cached_tasks = zd_tasks
    return cached_tasks


@app.route('/')
def homepage():
    minutes_completed_today = 0
    tasks_completed, tasks_to_do, tasks_backlog = [], [], []
    all_tasks = get_toodledo_tasks()
    for task in all_tasks:
        if task.completed_today and task.length_minutes > 0:
            minutes_completed_today += task.length_minutes
            tasks_completed.append(task)
    minutes_left_to_schedule = 120 - minutes_completed_today
    tasks, _ = get_sorted_and_unsorted_tasks()
    i = 0
    minutes_allocated = 0
    while minutes_left_to_schedule > 0 and i < len(tasks):
        if tasks[i].due <= today:
            if tasks[i].length_minutes <= (minutes_left_to_schedule + 5):
                tasks_to_do.append(tasks[i])
                minutes_left_to_schedule -= tasks[i].length_minutes
                minutes_allocated += tasks[i].length_minutes
            else:
                tasks_backlog.append(tasks[i])
        i += 1

    times = {
        'minutes_total': 120,
        'minutes_completed_today': minutes_completed_today,
        'minutes_allocated': minutes_allocated
    }
    return render_template('index.html',
                           tasks_completed=tasks_completed,
                           tasks_to_do=tasks_to_do,
                           tasks_backlog=tasks_backlog,
                           times=times)


if __name__ == '__main__':
    app.run(debug=True, use_reloader=True)
