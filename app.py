import time
from typing import List

from flask import Flask, render_template, request
from toodledo import Toodledo

import kv
from storage import TokenStoragePostgres

app = Flask(__name__)
toodledo = Toodledo(
    clientId=kv.get('TOODLEDO_CLIENT_ID'),
    clientSecret=kv.get('TOODLEDO_CLIENT_SECRET'),
    tokenStorage=TokenStoragePostgres("TOODLEDO_TOKEN_JSON"),
    scope="basic tasks notes outlines lists share write folders")


@app.route('/prioritize')
def show_prioritized_list():
    sorted_tasks, unsorted_tasks = get_sorted_and_unsorted_tasks()

    return render_template('prioritize.html',
                           sorted_tasks=sorted_tasks,
                           unsorted_tasks=unsorted_tasks)


def get_sorted_and_unsorted_tasks() -> (List, List):
    currently_sorted_in_db = kv.get("priorities").split("|||")
    sorted_tasks, unsorted_tasks = [], []
    all_tasks = toodledo.GetTasks(params={"fields": "duedate,star,length,repeat,parent"})
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


@app.route('/')
def homepage():
    minutes_left_to_schedule = 120
    tasks, _ = get_sorted_and_unsorted_tasks()
    i = 0
    tasks_to_do = []
    while minutes_left_to_schedule > 0 and i < len(tasks):
        if tasks[i].dueDate <= time.time() and tasks[i].length <= (minutes_left_to_schedule + 5):
            tasks_to_do.append(tasks[i])
            minutes_left_to_schedule -= tasks[i].length
    return render_template('index.html',
                           tasks=tasks_to_do)


if __name__ == '__main__':
    app.run(debug=True, use_reloader=True)
