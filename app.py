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
    currently_sorted_in_db = kv.get("priorities").split("|||")
    sorted_tasks = []
    unsorted_task = []
    for task in toodledo.GetTasks(params={"fields": "length,repeat,parent"}):
        if task.completedDate is None and task.length != 0:
            if task.title in currently_sorted_in_db:
                sorted_tasks.append(task)
            else:
                unsorted_task.append(task)

    return render_template('prioritize.html',
                           sorted_tasks=sorted_tasks,
                           unsorted_tasks=unsorted_task)


@app.route('/set_priorities', methods=['POST'])
def update_priorities():
    kv.put("priorities", request.get_json()["priorities"])
    return "{'result': 'success'}"


@app.route('/')
def homepage():
    return "hi"


if __name__ == '__main__':
    app.run(debug=True, use_reloader=True)
