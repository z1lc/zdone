import os
from datetime import datetime

import psycopg2
from flask import Flask

app = Flask(__name__)
DATABASE_URL = os.environ['DATABASE_URL']
conn = psycopg2.connect(DATABASE_URL, sslmode='require')


@app.route('/')
def homepage():
    the_time = datetime.now().strftime("%A, %d %b %Y")

    return """
    <h1>Hello heroku</h1>
    <p>It is currently {time}. Db version is {version}</p>
    """.format(time=the_time, version=get('TOODLEDO_CLIENT_ID'))


def get(key):
    cur = conn.cursor()
    cur.execute("SELECT v FROM zkv WHERE k='{key}'".format(key=key))
    res = cur.fetchone()
    cur.close()
    return res


if __name__ == '__main__':
    app.run(debug=True, use_reloader=True)
