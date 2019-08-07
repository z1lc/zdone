import datetime
from typing import List

import pytz
from flask import Flask, render_template, request
from habitipy import Habitipy
from toodledo import Toodledo

import kv
from habitica import HabiticaTask
from storage import TokenStoragePostgres

app = Flask(__name__)
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
today = datetime.datetime.now(pytz.timezone('US/Pacific')).date()
cached_tasks = []


@app.route('/habitica')
def habitica_today_tasks():
    habit_list = []
    # habitica_day_string = {0: "m", 1: "tu", 2: "w", 3: "th", 4: "f", 5: "s", 6: "su"}[today.weekday()]
    priority_to_length = {0.1: 5, 1: 15, 1.5: 30, 2: 60}
    for habit in habitica.tasks.user.get(type='dailys'):
        task = HabiticaTask(habit['_id'], habit['title'], 0)
        habit_list.append(task)
    return str(habit_list)


@app.route('/prioritize')
def show_prioritized_list():
    sorted_tasks, unsorted_tasks = get_sorted_and_unsorted_tasks()

    return render_template('prioritize.html',
                           sorted_tasks=sorted_tasks,
                           unsorted_tasks=unsorted_tasks)


def get_sorted_and_unsorted_tasks() -> (List, List):
    currently_sorted_in_db = kv.get("priorities").split("|||")
    sorted_tasks, unsorted_tasks = [], []
    all_tasks = get_all_tasks_from_api()
    all_recurring_tasks = [t for t in all_tasks if t.completedDate is None and t.length != 0]
    task_map = {t.title: t for t in all_recurring_tasks}
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


def get_all_tasks_from_api():
    global cached_tasks
    if not cached_tasks:
        cached_tasks = toodledo.GetTasks(params={"fields": "duedate,star,length,repeat,parent"})
    return cached_tasks


@app.route('/')
def homepage():
    minutes_completed_today = 0
    tasks_completed, tasks_to_do, tasks_backlog = [], [], []
    all_tasks = get_all_tasks_from_api()
    for task in all_tasks:
        if task.completedDate == today and task.length > 0:
            minutes_completed_today += task.length
            tasks_completed.append(task)
    minutes_left_to_schedule = 120 - minutes_completed_today
    tasks, _ = get_sorted_and_unsorted_tasks()
    i = 0
    minutes_allocated = 0
    while minutes_left_to_schedule > 0 and i < len(tasks):
        if tasks[i].dueDate <= today:
            if tasks[i].length <= (minutes_left_to_schedule + 5):
                tasks_to_do.append(tasks[i])
                minutes_left_to_schedule -= tasks[i].length
                minutes_allocated += tasks[i].length
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
