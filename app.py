import os
from datetime import datetime

import psycopg2
from flask import Flask

app = Flask(__name__)
DATABASE_URL = os.environ['DATABASE_URL']


@app.route('/')
def homepage():
    conn = psycopg2.connect(DATABASE_URL, sslmode='require')
    cur = conn.cursor()
    print('PostgreSQL database version:')
    cur.execute('SELECT version()')
    db_version = cur.fetchone()
    cur.close()

    the_time = datetime.now().strftime("%A, %d %b %Y")

    return """
    <h1>Hello heroku</h1>
    <p>It is currently {time}. Db version is {version}</p>

    <img src="http://loremflickr.com/600/400">
    """.format(time=the_time, version=db_version)


if __name__ == '__main__':
    app.run(debug=True, use_reloader=True)
