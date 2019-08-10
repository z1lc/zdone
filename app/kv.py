import os

import psycopg2


def get_con():
    return psycopg2.connect(os.environ['DATABASE_URL'], sslmode='require')


def get(key):
    conn = get_con()
    cur = conn.cursor()
    cur.execute("SELECT v FROM kv WHERE k='{key}'".format(key=key))
    res = cur.fetchone()
    if res:
        res = res[0]
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
