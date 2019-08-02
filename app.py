import os
from datetime import datetime

import psycopg2
from flask import Flask

app = Flask(__name__)
DATABASE_URL = os.environ['DATABASE_URL']


@app.route('/')
def homepage():
    conn = psycopg2.connect(DATABASE_URL, sslmode='require')
    # create a cursor
    cur = conn.cursor()

    # execute a statement
    print('PostgreSQL database version:')
    cur.execute('SELECT version()')

    # display the PostgreSQL database server version
    db_version = cur.fetchone()
    print(db_version)

    # close the communication with the PostgreSQL
    cur.close()

    the_time = datetime.now().strftime("%A, %d %b %Y")

    return """
    <h1>Hello heroku</h1>
    <p>It is currently {time}.</p>

    <img src="http://loremflickr.com/600/400">
    """.format(time=the_time)


if __name__ == '__main__':
    app.run(debug=True, use_reloader=True)
