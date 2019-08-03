from flask import Flask, render_template
from toodledo import Toodledo

import kv
from storage import TokenStoragePostgres

app = Flask(__name__)
toodledo = Toodledo(
    clientId=kv.get('TOODLEDO_CLIENT_ID'),
    clientSecret=kv.get('TOODLEDO_CLIENT_SECRET'),
    tokenStorage=TokenStoragePostgres("TOODLEDO_TOKEN_JSON"),
    scope="basic tasks notes outlines lists share write folders")


@app.route('/')
def homepage():
    to_print = ""
    for task in toodledo.GetTasks(params={"fields": "length,repeat,parent"}):
        if task.completedDate is None and (task.length != 0 or hasattr(task, "repeat")):
            to_print += task.title + '  ' + '<br>'

    return render_template('index.html', username="fdsfds")


if __name__ == '__main__':
    app.run(debug=True, use_reloader=True)
