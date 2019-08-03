from flask import Flask
from toodledo import Toodledo

import kv
from storage import TokenStoragePostgres

app = Flask(__name__)


@app.route('/')
def homepage():
    storage = TokenStoragePostgres("TOODLEDO_TOKEN_JSON")
    toodledo = Toodledo(
        clientId=kv.get('TOODLEDO_CLIENT_ID'),
        clientSecret=kv.get('TOODLEDO_CLIENT_SECRET'),
        tokenStorage=storage,
        scope="basic tasks notes outlines lists share write folders")
    to_print = ""
    for task in toodledo.GetTasks(params={"fields": "length,repeat"}):
        if task.completedDate is None and (task.length != 0 or hasattr(task, "repeat")):
            to_print += task.title + '  ' + '<br>'

    return to_print


if __name__ == '__main__':
    app.run(debug=True, use_reloader=True)
