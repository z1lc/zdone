from datetime import timedelta
from typing import List, Tuple

from flask import render_template, request
from flask import url_for, flash
from flask_login import current_user, login_user, logout_user
from flask_login import login_required
from werkzeug.urls import url_parse
from werkzeug.utils import redirect

from . import redis_client, app, db
from .forms import LoginForm
from .models import User
from .taskutils import get_toodledo_tasks, get_habitica_tasks, complete_habitica_task, complete_toodledo_task
from .util import today
from .ztasks import ZDTask

DEFAULT_TOTAL_MINUTES = 120


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('index')
        return redirect(next_page)
    return render_template('login.html', title='Sign In', form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/priorities')
@login_required
def show_priorities():
    prioritized_tasks, unprioritizsed_tasks = get_task_order_from_db("priorities")

    return render_template('prioritize_and_order.html',
                           sorted_tasks=prioritized_tasks,
                           unsorted_tasks=unprioritizsed_tasks,
                           type='priorities')


@app.route('/dependencies')
@login_required
def show_dependencies():
    dependencies_ordered, dependencies_to_order = get_task_order_from_db("dependencies")
    index_insert = 0
    for i, e in enumerate(dependencies_ordered):
        if e.name == "Mail":
            index_insert = i

    dependencies_ordered.insert(index_insert, ZDTask(
        "-1", "[all unordered Toodledo tasks]", 0, None, None, "", "unorderedToodledo", []))

    return render_template('prioritize_and_order.html',
                           sorted_tasks=dependencies_ordered,
                           unsorted_tasks=dependencies_to_order,
                           type='dependencies')


def get_all_tasks() -> List[ZDTask]:
    return get_toodledo_tasks(redis_client) + get_habitica_tasks()


def get_task_order_from_db(order_type) -> (List[ZDTask], List[ZDTask]):
    currently_sorted_in_db = getattr(current_user, order_type).split("|||")
    sorted_tasks, unsorted_tasks = [], []
    all_tasks: List[ZDTask] = get_all_tasks()
    all_recurring_tasks = [t for t in all_tasks if t.length_minutes != 0]
    task_map = {t.name: t for t in all_recurring_tasks}
    for name in currently_sorted_in_db:
        if name in task_map:
            sorted_tasks.append(task_map[name])
            del task_map[name]

    for v in task_map.values():
        unsorted_tasks.append(v)

    return sorted_tasks, unsorted_tasks


@app.route('/set_priorities', methods=['POST'])
@login_required
def update_priorities():
    current_user.priorities = request.get_json()["priorities"]
    db.session.commit()
    return "{'result': 'success'}"


@app.route('/set_dependencies', methods=['POST'])
@login_required
def update_dependencies():
    current_user.dependencies = request.get_json()["dependencies"]
    db.session.commit()
    return "{'result': 'success'}"


@app.route('/update_task', methods=['POST'])
@login_required
def update_task():
    req = request.get_json()
    update = req["update"]
    service = req["service"]
    task_id = req["id"]

    if update == "defer":
        redis_client.append("hidden:" + current_user.username + ":" + str(today), (task_id + "|||").encode())
        redis_client.expire("hidden:" + current_user.username + ":" + str(today), timedelta(days=7))
        # can no longer use cached tasks since we have to re-sort
        redis_client.delete("toodledo:" + current_user.username + ":last_mod")
    elif update == "complete":
        if service == "habitica":
            complete_habitica_task(task_id)
        elif service == "toodledo":
            complete_toodledo_task(task_id)
        else:
            return "{'result': 'failure: unexpected service type \"" + service + "\"'}"
    else:
        return "{'result': 'failure: unexpected update type \"" + update + "\"'}"

    return "{'result': 'success'}"


@app.route('/')
@app.route("/index")
@login_required
def homepage():
    minutes_completed_today = 0
    tasks_completed, tasks_to_do, tasks_backlog = set(), set(), set()
    prioritized_tasks, unprioritized_tasks = get_task_order_from_db("priorities")
    for task in prioritized_tasks + unprioritized_tasks:
        if task.completed_today() and task.length_minutes > 0:
            minutes_completed_today += task.length_minutes
            tasks_completed.add(task)

    task_ids_to_hide = redis_client.get("hidden:" + current_user.username + ":" + str(today))
    task_ids_to_hide = [] if task_ids_to_hide is None else task_ids_to_hide.decode().split("|||")

    total_minutes = DEFAULT_TOTAL_MINUTES if request.args.get('time') is None else int(request.args.get('time'))
    minutes_left_to_schedule = total_minutes - minutes_completed_today
    i = 0
    minutes_allocated = 0
    while i < len(prioritized_tasks):
        prioritized_task = prioritized_tasks[i]
        if prioritized_task.due_date <= today:
            if prioritized_task.length_minutes <= (minutes_left_to_schedule + 5) \
                    and prioritized_task.id not in task_ids_to_hide \
                    and not prioritized_task.completed_today():
                tasks_to_do.add(prioritized_task)
                minutes_left_to_schedule -= prioritized_task.length_minutes
                minutes_allocated += prioritized_task.length_minutes
            else:
                tasks_backlog.add(prioritized_task)
        i += 1

    ordering = [t.name for t in get_task_order_from_db("dependencies")[0]]
    sorted_tasks_to_do: List[Tuple[int, ZDTask]] = []  # int in Tuple is priority; lower is better
    for task in tasks_to_do:
        if task.name in ordering:
            sorted_tasks_to_do.append((ordering.index(task.name), task))
        else:
            # TODO: unify this search for Mail and the one in show_dependencies
            sorted_tasks_to_do.append((ordering.index("Mail"), task))

    sorted_tasks_to_do.sort(key=lambda tup: tup[0])

    times = {
        'minutes_completed_today': minutes_completed_today,
        'minutes_allocated': minutes_allocated
    }
    percent_done = int(times['minutes_completed_today'] * 100 / (
            times['minutes_completed_today'] + times['minutes_allocated']))
    return render_template('index.html',
                           tasks_completed=tasks_completed,
                           tasks_to_do=[task for _, task in sorted_tasks_to_do],
                           tasks_backlog=tasks_backlog,
                           times=times,
                           num_unsorted_tasks=len(unprioritized_tasks),
                           percentage=min(100, max(1, percent_done)))
