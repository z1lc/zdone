import os

import psycopg2


def get_con():
    return psycopg2.connect(os.environ['DATABASE_URL'], sslmode='require')


def get(key: str) -> str:
    conn = get_con()
    cur = conn.cursor()
    cur.execute(f"SELECT v FROM kv WHERE k='{key}'")
    res = cur.fetchone()
    if res:
        res = res[0]
    cur.close()
    conn.close()
    return res


def put(key: str, value: str) -> None:
    conn = get_con()
    cur = conn.cursor()
    cur.execute(f"INSERT INTO kv(k, v) VALUES ({key}, {value}) ON CONFLICT (k) DO UPDATE SET v = {value}")
    conn.commit()
    cur.close()
    conn.close()
