import os
from typing import List

from flask import Flask, render_template, request
from flask_talisman import Talisman

import kv
from taskutils import get_toodledo_tasks, get_habitica_tasks
from uniformtasks import ZDTask
from util import today
from flask_redis import FlaskRedis

csp = {
    'default-src': [
        '\'self\'',
        '*.jquery.com',
        '*.w3schools.com'
    ]
}
app = Flask(__name__)
Talisman(content_security_policy=csp)
app.config['REDIS_URL'] = os.environ.get('REDIS_URL')
redis_client = FlaskRedis(app)


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
    all_tasks: List[ZDTask] = get_toodledo_tasks(redis_client) + get_habitica_tasks()
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


@app.route('/')
def homepage():
    minutes_completed_today = 0
    tasks_completed, tasks_to_do, tasks_backlog = [], [], []
    tasks, unsorted_tasks = get_sorted_and_unsorted_tasks()
    for task in tasks + unsorted_tasks:
        if task.completed_today and task.length_minutes > 0:
            minutes_completed_today += task.length_minutes
            tasks_completed.append(task)
    minutes_left_to_schedule = 120 - minutes_completed_today
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
                           times=times,
                           num_unsorted_tasks=len(unsorted_tasks))


if __name__ == '__main__':
    app.run(debug=True, use_reloader=True)
