from datetime import timedelta, datetime
from json import dumps
from typing import List, Tuple

from flask import render_template, request, make_response, jsonify, redirect
from flask import url_for, flash
from flask_login import current_user, login_user, logout_user
from flask_login import login_required
from sentry_sdk import last_event_id
from trello import TrelloClient
from werkzeug.urls import url_parse

from . import redis_client, app, db, socketio
from .forms import LoginForm
from .models import User, TaskCompletion
from .spotify import get_artists, get_top_track_uris, play_track, maybe_get_spotify_authorize_url
from .taskutils import get_toodledo_tasks, get_habitica_tasks, complete_habitica_task, complete_toodledo_task, \
    add_toodledo_task
from .util import today
from .ztasks import ZDTask, htmlize_note


@app.errorhandler(500)
def server_error_handler(error):
    return render_template("500.html", sentry_event_id=last_event_id()), 500


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

    return render_template('priorities_and_dependencies.html',
                           sorted_tasks=prioritized_tasks,
                           unsorted_tasks=unprioritizsed_tasks,
                           type='priorities')


TOODLEDO_UNORDERED_TASKS_PLACEHOLDER = ZDTask(
    "-1", "[all unordered Toodledo Tasks]", 0, None, None, "", "", "unorderedToodledo", [])


@app.route('/dependencies')
@login_required
def show_dependencies():
    dependencies_ordered, dependencies_to_order = get_task_order_from_db("dependencies")

    # insert the Toodledo placeholder in case it's not already in the ordering saved in db
    if TOODLEDO_UNORDERED_TASKS_PLACEHOLDER not in dependencies_ordered:
        index_insert = 0
        for i, e in enumerate(dependencies_ordered):
            if e.name == "Mail":
                index_insert = i

        dependencies_ordered.insert(index_insert, TOODLEDO_UNORDERED_TASKS_PLACEHOLDER)

    return render_template('priorities_and_dependencies.html',
                           sorted_tasks=dependencies_ordered,
                           unsorted_tasks=dependencies_to_order,
                           type='dependencies')


def get_all_tasks(user=current_user) -> List[ZDTask]:
    return get_toodledo_tasks(redis_client, user) + get_habitica_tasks(user)


def get_task_order_from_db(order_type, user=current_user) -> (List[ZDTask], List[ZDTask]):
    currently_sorted_in_db = getattr(user, order_type)
    if currently_sorted_in_db:
        currently_sorted_in_db = currently_sorted_in_db.split("|||")
    else:
        currently_sorted_in_db = []
    sorted_tasks, unsorted_tasks = [], []
    all_tasks: List[ZDTask] = get_all_tasks(user)
    task_map = {t.name: t for t in all_tasks}
    task_map[TOODLEDO_UNORDERED_TASKS_PLACEHOLDER.name] = TOODLEDO_UNORDERED_TASKS_PLACEHOLDER
    for name in currently_sorted_in_db:
        if name in task_map:
            sorted_tasks.append(task_map[name])
            del task_map[name]

    for task in task_map.values():
        if task.is_repeating():
            unsorted_tasks.append(task)

    if TOODLEDO_UNORDERED_TASKS_PLACEHOLDER in unsorted_tasks:
        del unsorted_tasks[unsorted_tasks.index(TOODLEDO_UNORDERED_TASKS_PLACEHOLDER)]

    return sorted_tasks, unsorted_tasks


def success():
    return jsonify({
        'result': 'success'
    }), 200


def api_key_failure():
    return jsonify({
        'result': 'failure',
        'reason': 'Make sure you are passing a valid API key in the x-api-key header.'
    }), 401


@app.route('/set_priorities', methods=['POST'])
@login_required
def update_priorities():
    current_user.priorities = request.get_json()["priorities"]
    db.session.commit()
    return success()


@app.route('/set_dependencies', methods=['POST'])
@login_required
def update_dependencies():
    current_user.dependencies = request.get_json()["dependencies"]
    db.session.commit()
    return success()


def do_update_task(update, service, task_id, subtask_id, duration_seconds=0, user=current_user):
    if update == "defer":
        redis_client.append("hidden:" + user.username + ":" + str(today()), (task_id + "|||").encode())
        redis_client.expire("hidden:" + user.username + ":" + str(today()), timedelta(days=7))
        # can no longer use cached tasks since we have to re-sort
        redis_client.delete("toodledo:" + user.username + ":last_mod")
    elif update == "complete":
        if service == "habitica":
            complete_habitica_task(task_id, subtask_id, user)
        elif service == "toodledo":
            if subtask_id:
                complete_toodledo_task(subtask_id, user)
            else:
                complete_toodledo_task(task_id, user)
        else:
            return jsonify({
                'result': 'failure',
                'reason': 'unexpected service type "' + service + '"'
            }), 400

        task_completion = TaskCompletion(user_id=user.id, service=service, task_id=task_id, subtask_id=subtask_id,
                                         duration_seconds=duration_seconds, at=datetime.now())
        db.session.add(task_completion)
        db.session.commit()
    else:
        return jsonify({
            'result': 'failure',
            'reason': 'unexpected update type "' + update + '"'
        }), 400

    length = 0
    if not subtask_id:
        length = \
            [t.length_minutes for i, t in enumerate(get_all_tasks(user)) if t.service == service and t.id == task_id][0]
    socketio.emit(user.api_key, {
        'update': update,
        'service': service,
        'task_id': task_id,
        'subtask_id': subtask_id if subtask_id else '',
        'length_minutes': length
    })
    return success()


def do_update_time(time, user=current_user):
    user.maximum_minutes_per_day = max(0, min(1440, int(time)))
    db.session.commit()
    return success()


@app.route('/update_task', methods=['POST'])
@login_required
def update_task():
    req = request.get_json()
    update = req["update"]
    service = req["service"]
    task_id = req["id"]
    subtask_id = req["subtask_id"] if "subtask_id" in req else None
    duration_seconds = req["duration_seconds"] if "duration_seconds" in req else None

    return do_update_task(update, service, task_id, subtask_id, duration_seconds)


@app.route('/add_task', methods=['POST'])
@login_required
def add_task():
    req = request.get_json()
    name = req["name"]
    due_date = req["due_date"]
    length_minutes = req["length_minutes"]

    add_toodledo_task(name, due_date, length_minutes)
    return success()


@app.route('/update_time', methods=['POST'])
@login_required
def update_time():
    return do_update_time(request.get_json()["maximum_minutes_per_day"])


def get_homepage_info(user=current_user):
    minutes_completed_today = 0
    tasks_completed, tasks_to_do, tasks_backlog, nonrecurring_tasks_coming_up = [], [], [], []
    prioritized_tasks, unprioritized_tasks = get_task_order_from_db("priorities", user)
    for task in prioritized_tasks:
        if task.completed_today() and task not in tasks_completed:
            minutes_completed_today += task.length_minutes
            tasks_completed.append(task)

    task_ids_to_hide = redis_client.get("hidden:" + user.username + ":" + str(today()))
    task_ids_to_hide = [] if task_ids_to_hide is None else task_ids_to_hide.decode().split("|||")

    total_minutes = user.maximum_minutes_per_day
    minutes_left_to_schedule = total_minutes - minutes_completed_today

    i = 0
    minutes_allocated = 0
    all_tasks = get_all_tasks(user)
    while i < len(all_tasks):
        task = all_tasks[i]
        if task.id not in task_ids_to_hide \
                and not task.completed_today():
            if task.due_date is not None and task.due_date <= today():
                # add 4 minutes to allow some space for non-round-number tasks to be scheduled
                if task.length_minutes <= (minutes_left_to_schedule + 4) and task not in tasks_to_do:
                    tasks_to_do.append(task)
                    minutes_left_to_schedule -= task.length_minutes
                    minutes_allocated += task.length_minutes
                elif task not in tasks_backlog:
                    tasks_backlog.append(task)
            elif not task.is_repeating() and \
                    (task.due_date is not None and task.due_date <= (today() + timedelta(days=1))) and \
                    task not in nonrecurring_tasks_coming_up:
                nonrecurring_tasks_coming_up.append(task)
        i += 1

    ordering = [t.name for t in get_task_order_from_db("dependencies", user)[0]]
    sorted_tasks_to_do: List[Tuple[int, ZDTask]] = []  # int in Tuple is priority; lower is better
    for task in tasks_to_do:
        if task.name in ordering:
            sorted_tasks_to_do.append((ordering.index(task.name), task))
        else:
            sorted_tasks_to_do.append((ordering.index(TOODLEDO_UNORDERED_TASKS_PLACEHOLDER.name)
                                       if TOODLEDO_UNORDERED_TASKS_PLACEHOLDER.name in ordering else 0,
                                       task))

    sorted_tasks_to_do.sort(key=lambda tup: tup[0])

    times = {
        'minutes_completed_today': minutes_completed_today,
        'minutes_allocated': minutes_allocated,
        'maximum_minutes_per_day': user.maximum_minutes_per_day
    }
    denom = times['minutes_completed_today'] + times['minutes_allocated']
    percent_done = int(times['minutes_completed_today'] * 100 / denom) if denom > 0 else 0
    tasks_without_required_fields = get_tasks_without_required_fields(all_tasks)
    return {
        "tasks_completed": list(tasks_completed),
        "tasks_to_do": [task for _, task in sorted_tasks_to_do],
        "tasks_backlog": list(tasks_backlog),
        "tasks_without_required_fields": tasks_without_required_fields,
        "nonrecurring_tasks_coming_up": list(nonrecurring_tasks_coming_up),
        "times": times,
        "num_unsorted_tasks": len(unprioritized_tasks),
        "percentage": min(100, max(0, percent_done)),
        "background": "red !important" if times['minutes_completed_today'] < 30 else "#2196F3 !important"
    }


def get_tasks_without_required_fields(all_tasks):
    bad_tasks = []
    for task in all_tasks:
        if task.completed_date is None:
            if (task.length_minutes is None or task.length_minutes == 0) or \
                    task.due_date is None:
                bad_tasks.append(task)

    return bad_tasks


def get_open_trello_lists():
    if current_user.trello_api_key and current_user.trello_api_access_token:
        client = TrelloClient(
            api_key=current_user.trello_api_key,
            api_secret=current_user.trello_api_access_token
        )
        backlog_board = [board for board in client.list_boards() if board.name == 'Backlogs'][0]

        return backlog_board.list_lists('open')
    return []


@app.context_processor
def utility_processor():
    def htmlize(raw_note):
        return htmlize_note(raw_note)

    return dict(htmlize=htmlize)


@app.route('/maintenance')
@login_required
def maintenance():
    return render_template('maintenance.html',
                           api_key=current_user.api_key)


@app.route('/spotify/auth')
def spotify_auth():
    maybe_url = maybe_get_spotify_authorize_url(request.url)
    if maybe_url:
        return redirect(maybe_url, 302)
    return "successfully auth'd"


@app.route('/spotify/top_liked')
def spotify():
    artists = get_artists()
    if isinstance(artists, dict):
        return render_template('spotify.html',
                               potential_artists=artists['artists'],
                               correct_artist=artists['correct_artist'])
    else:
        return artists


@app.route('/spotify/anki_import')
def spotify_anki_import():
    return get_top_track_uris()


@app.route("/api/play_track")
def api_play_song():
    args = request.args
    if not args or "track_uri" not in args:
        return jsonify({
            'result': 'failure',
            'reason': 'Request must set parameter \'track_uri\'.'
        }), 400
    else:
        track_uri = args.get('track_uri')
        offset = args.get('offset') if "offset" in args else None

        return play_track(track_uri, offset)


@app.route('/')
@app.route("/index")
@login_required
def index():
    info = get_homepage_info()
    info['times']['minutes_total_rounded'] = \
        round(info['times']['minutes_allocated'] + info['times']['minutes_completed_today'])
    info['times']['minutes_completed_today_rounded'] = \
        round(info['times']['minutes_completed_today'])
    return render_template('index.html',
                           trello_lists=get_open_trello_lists(),
                           today=today(),
                           api_key=current_user.api_key,
                           tasks_completed=info['tasks_completed'],
                           tasks_to_do=info['tasks_to_do'],
                           num_tasks_to_do=len(info['tasks_to_do']),
                           tasks_backlog=info['tasks_backlog'],
                           tasks_without_required_fields=info['tasks_without_required_fields'],
                           num_tasks_without_required_fields=len(info['tasks_without_required_fields']),
                           nonrecurring_tasks_coming_up=info['nonrecurring_tasks_coming_up'],
                           times=info['times'],
                           num_unsorted_tasks=info['num_unsorted_tasks'],
                           percentage=info['percentage'],
                           background=info['background'])


def validate_api_key(api_key):
    return User.query.filter_by(api_key=api_key).first() if api_key else None


@app.route("/api")
def api():
    user = validate_api_key(request.headers.get('x-api-key'))
    if not user:
        return api_key_failure()
    else:
        r = dumps(get_homepage_info(user))
        r = make_response(r)
        r.mimetype = 'application/json'
        return r, 200


@app.route('/api/update_task', methods=['POST'])
def api_update_task():
    user = validate_api_key(request.headers.get('x-api-key'))
    if not user:
        return api_key_failure()
    else:
        req = request.get_json()
        if not req or "update" not in req or "service" not in req or "id" not in req:
            return jsonify({
                'result': 'failure',
                'reason': 'Request body must be application/json with keys \'update\', \'service\', and \'id\'.'
            }), 400
        else:
            update = req["update"]
            service = req["service"]
            task_id = req["id"]
            subtask_id = req["subtask_id"] if "subtask_id" in req else None
            duration_seconds = req["duration_seconds"] if "duration_seconds" in req else None

            try:
                return do_update_task(update, service, task_id, subtask_id, duration_seconds, user)
            except Exception as e:
                return jsonify({
                    'result': 'failure',
                    'reason': str(e)
                }), 400


@app.route('/api/update_time', methods=['POST'])
def api_update_time():
    user = validate_api_key(request.headers.get('x-api-key'))
    if not user:
        return api_key_failure()
    else:
        req = request.get_json()
        if not req or "maximum_minutes_per_day" not in req:
            return jsonify({
                'result': 'failure',
                'reason': 'Request body must be application/json with key \'maximum_minutes_per_day\'.'
            }), 400
        else:
            time = req["maximum_minutes_per_day"]

            try:
                return do_update_time(time, user)
            except Exception as e:
                return jsonify({
                    'result': 'failure',
                    'reason': str(e)
                }), 400


@app.route('/debug-sentry')
def trigger_error():
    division_by_zero = 1 / 0
