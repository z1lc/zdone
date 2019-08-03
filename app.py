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
    put('time', the_time)

    return """
    <h1>Hello heroku</h1>
    <p>It is currently {time}. Db version is {version}</p>
    """.format(time=the_time, version=get('time'))


def get(key):
    cur = conn.cursor()
    cur.execute("SELECT v FROM kv WHERE k='{key}'".format(key=key))
    res = cur.fetchone()[0]
    cur.close()
    return res


def put(key, value):
    cur = conn.cursor()
    cur.execute("INSERT INTO kv(k, v) VALUES ('{key}', '{value}') ON CONFLICT (k) DO UPDATE SET v = {value}"
                .format(key=key, value=value))
    cur.close()


if __name__ == '__main__':
    app.run(debug=True, use_reloader=True)
