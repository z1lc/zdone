import os
from datetime import datetime

import psycopg2
from flask import Flask

app = Flask(__name__)


@app.route('/')
def homepage():
    the_time = datetime.now().strftime("%A, %d %b %Y")
    put('time', the_time)

    return """
    <h1>Hello heroku</h1>
    <p>It is currently {time}. Db version is {version}</p>
    """.format(time=the_time, version=get('time'))


def get_con():
    return psycopg2.connect(os.environ['DATABASE_URL'], sslmode='require')


def get(key):
    conn = get_con()
    cur = conn.cursor()
    cur.execute("SELECT v FROM kv WHERE k='{key}'".format(key=key))
    res = cur.fetchone()[0]
    cur.close()
    conn.close()
    return res


def put(key, value):
    conn = get_con()
    cur = conn.cursor()
    cur.execute("INSERT INTO kv(k, v) VALUES (%s, %s) ON CONFLICT (k) DO UPDATE SET v = %s",
                (key, value, value))
    conn.commit()
    cur.close()
    conn.close()


if __name__ == '__main__':
    app.run(debug=True, use_reloader=True)
