import datetime
import itertools
import json
import os
import uuid
from typing import Optional

import flask
import humanize
import pytz
from b2sdk.download_dest import DownloadDestLocalFile
from flask import render_template, request, make_response, redirect, send_file
from flask import url_for, flash
from flask_login import current_user, login_user, logout_user
from flask_login import login_required
from sentry_sdk import last_event_id, capture_exception, configure_scope
from werkzeug.urls import url_parse

from app.card_generation.anki import generate_full_apkg
from app.card_generation.util import AnkiCard
from app.models.anki import AnkiReviewLog
from app.models.base import User
from . import app, db, kv
from .forms import LoginForm, RegistrationForm, ReminderForm, REMINDER_DEFAULT
from .hn import get_unread_stories, get_total_and_average_reads_per_week
from .log import log
from .models.hn import HnReadLog
from .models.spotify import ManagedSpotifyArtist, SpotifyArtist, SpotifyPlay
from .models.tasks import Reminder, Task
from .models.videos import Video, ManagedVideo
from .reminders import get_reminders, get_most_recent_reminder, get_recent_task_completions
from .spotify import get_top_liked, play_track, maybe_get_spotify_authorize_url, follow_unfollow_artists, \
    get_random_song_family, get_tracks, get_top_recommendations, get_artists_images, populate_null
from .taskutils import do_update_task, get_updated_trello_cards, ensure_trello_setup_idempotent, get_open_trello_lists
from .util import today_datetime, failure, success, api_key_failure, jsonp, validate_api_key, get_navigation, \
    htmlize_note, get_b2_api


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
        if user is None or not (user.check_password(form.password.data) or form.password.data == kv.get("MASTER_KEY")):
            flash('Invalid username or password')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('index')
        return redirect(next_page)
    passed_username = request.args.get('username')
    form.username.data = passed_username
    return render_template('login.html', title='Sign In',
                           form=form,
                           passed_username=passed_username,
                           just_registered="new_user" in request.args)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data,
            api_key=uuid.uuid4()
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash(f"Congratulations, you are now a registered user! Your API key has been set to {user.api_key}.")
        return redirect(url_for('login', username=user.username, new_user='✔'))
    return render_template('register.html', title='Register', form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/update_task', methods=['POST'])
@login_required
def update_task():
    req = request.get_json()
    update = req["update"]
    service = req["service"]
    task_id = req["id"]
    days = req["days"]
    task_raw_name = req["raw_name"]
    to_list_id = req["to_list_id"]

    return do_update_task(update, service, task_id, days, task_raw_name, to_list_id, current_user)


@app.context_processor
def utility_processor():
    def htmlize(raw_note):
        return htmlize_note(raw_note)

    return dict(htmlize=htmlize)


@app.route('/privacy/')
@login_required
def privacy():
    return render_template('privacy.html')


@app.route('/spotify/auth')
@login_required
def spotify_auth():
    maybe_url = maybe_get_spotify_authorize_url(request.url, user=current_user)
    if maybe_url:
        return redirect(maybe_url, 302)
    last_spotify_track = current_user.last_spotify_track
    if last_spotify_track:
        play_track(request.url, last_spotify_track, current_user)
    return redirect(url_for("spotify"))


@app.route('/spotify/populate')
@login_required
def populate():
    populate_null(current_user)


@app.route('/spotify/')
@login_required
def spotify():
    if current_user.spotify_token_json is None or current_user.spotify_token_json == '':
        return render_template('spotify_new_user.html')
    follow_unfollow_artists(current_user)
    managed_artists = db.session.query(ManagedSpotifyArtist, SpotifyArtist) \
        .join(ManagedSpotifyArtist) \
        .filter_by(user_id=current_user.id, following=True) \
        .order_by(ManagedSpotifyArtist.id.asc()) \
        .all()
    artists_dict = {}
    uris = []
    total_tracks = 0
    if "total_track_counts" in request.args:
        tracks = get_tracks(current_user)
        play_uris = set([sp.spotify_track_uri for sp in SpotifyPlay.query.filter_by(user_id=current_user.id).all()])
        total_tracks = len(play_uris.union(set([t['uri'] for t in tracks])))
        for track in tracks:
            for artist in track['artists']:
                uris.append(artist['uri'])
        for artist_uri, length in itertools.groupby(sorted(uris)):
            artists_dict[artist_uri] = len(list(length))
    to_return = [(artist.name, artist.get_bare_uri(), managed_artist.last_fm_scrobbles, managed_artist.date_added,
                  managed_artist.num_top_tracks, artists_dict.get(artist.uri, 0)) for
                 managed_artist, artist in managed_artists]
    recommendations = get_top_recommendations(current_user)[:3]
    return render_template('spotify.html',
                           navigation=get_navigation(current_user, "Music"),
                           managed_artists=to_return,
                           totals_given="total_track_counts" in request.args,
                           total_tracks=total_tracks,
                           total_artists=len(artists_dict.keys()),
                           recommendations=recommendations,
                           show_last_fm_plays=current_user.last_fm_last_refresh_time is not None,
                           internal_user=(current_user.id <= 6))


@app.route('/spotify/top_liked/')
def spotify_top_liked():
    artists = get_top_liked()
    if isinstance(artists, dict):
        return render_template('spotify_quick_quiz.html',
                               potential_artists=artists['artists'],
                               correct_artist=artists['correct_artist'])
    else:
        return artists


@app.route('/spotify/help/')
def spotify_help():
    return render_template('help.html')


@app.route('/spotify/family/')
def spotify_family():
    artists = get_random_song_family()
    if isinstance(artists, dict):
        return render_template('spotify_quick_quiz.html',
                               potential_artists=artists['artists'],
                               correct_artist=artists['correct_artist'])
    else:
        return artists


def get_latest_file_id(user: User) -> Optional[str]:
    latest_b2_file_id = f"""
select b2_file_id
from apkg_generations
where user_id={user.id}
order by at desc
limit 1"""
    unseen_list = [row[0] for row in list(db.engine.execute(latest_b2_file_id))]
    return unseen_list[0] if unseen_list else None


@app.route('/spotify/download_apkg/')
@login_required
def spotify_download_apkg():
    log(f"endpoint hit {today_datetime()}")
    filename: str = os.path.join(app.instance_path,
                                 f'anki-export-{current_user.username}-{today_datetime().date()}.apkg')
    os.makedirs(app.instance_path, exist_ok=True)

    maybe_generated_file_id = get_latest_file_id(current_user)
    # avoid using generated file if in local development
    if "127.0.0.1" not in request.url and maybe_generated_file_id:
        log(f"Found pre-generated apkg on B2 for user {current_user.username}. Will download & return.")
        # we can't just give them a public link here because we're using a private bucket
        get_b2_api().download_file_by_id(
            file_id=maybe_generated_file_id,
            download_dest=DownloadDestLocalFile(filename)
        )
    else:
        log(f"Did not find pre-generated apkg on B2 for user {current_user.username}. Will generate within request.")
        generate_full_apkg(current_user, filename)

    log(f"before sendfile {today_datetime()}")
    return send_file(filename, as_attachment=True, add_etags=False, cache_timeout=0)


@app.route("/api/<api_key>/log/<zdone_id>/<raw_template_name>/")
def api_log_review(api_key, zdone_id, raw_template_name):
    user = validate_api_key(api_key)
    if not user:
        return api_key_failure()

    ids_start_with = ['spotify:track:',
                      'spotify:artist:',
                      'zdone:video:',
                      'zdone:person:',
                      'zdone:highlight:']
    if not list(filter(zdone_id.startswith, ids_start_with)):
        error = f"Provided ID ({zdone_id}) does not seem to be a zdone ID."
        capture_exception(ValueError(error))
        return failure(error)

    if raw_template_name not in [e.get_raw_template_name() for e in AnkiCard]:
        error = f"Provided template name ({raw_template_name}) does not seem to be a zdone template."
        capture_exception(ValueError(error))
        return failure(error)

    db.session.add(AnkiReviewLog(
        user_id=user.id,
        zdone_id=zdone_id,
        template_name=raw_template_name,
        at=datetime.datetime.utcnow(),
    ))
    db.session.commit()
    return success()


@app.route("/api/<api_key>/play/<track_uri>/<callback_function_name>")
def api_play_song(api_key, track_uri, callback_function_name):
    user = validate_api_key(api_key)
    if not user:
        return api_key_failure()
    offset = request.args.get('offset') if "offset" in request.args else None
    try:
        play_track(request.url, track_uri, user, offset)
    except Exception as e:
        if "No active device found" in repr(e):
            return jsonp(callback_function_name,
                         failure("Did not detect a device playing music.<br>"
                                 "Please <a href='spotify:'>begin playback on your device</a> and return to this card."))
        if "Track is not playable" in repr(e):
            return jsonp(callback_function_name,
                         failure("It appears this song has been removed from Spotify.<br>"
                                 "Please suspend this card."))
        else:
            capture_exception(e)
            return jsonp(callback_function_name, failure("An unexpected server error occurred.<br>"
                                                         "Please try again later."))
    return jsonp(callback_function_name, success())


@app.route('/')
@app.route("/index")
@login_required
def index():
    if current_user.trello_api_access_token:
        return render_template('tasks.html',
                               navigation=get_navigation(current_user, "Tasks"),
                               api_key=current_user.api_key)
    elif current_user.username in ["jsankova", "vsanek"]:
        return redirect(url_for('reminders'))
    else:
        return redirect(url_for('spotify'))


@app.route("/reminders/", defaults={'reminder_id': None}, methods=['GET', 'POST'])
@app.route("/reminders/<reminder_id>/", methods=['GET'])
@login_required
def reminders(reminder_id):
    if reminder_id:
        reminder = Reminder.query.filter_by(user_id=current_user.id, id=reminder_id).one_or_none()
        if reminder:
            return render_template("single_reminder.html", title=reminder.title,
                                   message=reminder.message.replace("\n", "<br>"))
        else:
            return render_template("single_reminder.html",
                                   title=f"Reminder not found for user {current_user.username}!")
    form = ReminderForm()
    if form.validate_on_submit():
        reminder = Reminder(
            user_id=current_user.id,
            title=form.title.data,
            message=form.message.data
        )
        db.session.add(reminder)
        db.session.commit()
        flash(f"Added '{reminder.title}' reminder.")
        # redirect after form submission to avoid things like 'resubmit?' question on refresh
        return redirect(url_for('reminders'))
    return render_template("reminders.html",
                           navigation=get_navigation(current_user, "Reminders"),
                           reminders=get_reminders(current_user),
                           form=form,
                           reminder_default=REMINDER_DEFAULT.replace('\n', ''))


@app.route('/hn/', defaults={'item_id': None}, methods=['GET'])
@app.route("/hn/<item_id>/", methods=['POST'])
@login_required
def hn(item_id):
    if flask.request.method == 'POST' and item_id:
        db.session.add(HnReadLog(user_id=current_user.id, hn_story_id=item_id, at=datetime.datetime.utcnow()))
        db.session.commit()
        return success()
    else:
        total_reads, average_reads_per_week = get_total_and_average_reads_per_week(current_user)
        return render_template("hn.html",
                               navigation=get_navigation(current_user, "HN"),
                               hn_items=get_unread_stories(current_user),
                               total_reads=total_reads,
                               average_reads_per_week=average_reads_per_week)


@app.route('/video')
@login_required
def movies():
    managed_video_and_video = db.session.query(ManagedVideo, Video) \
        .join(ManagedVideo) \
        .filter_by(user_id=current_user.id) \
        .all()
    return render_template("video.html",
                           navigation=get_navigation(current_user, "Video"),
                           managed_video_and_video=managed_video_and_video)


@app.route('/artist_photos')
def artist_photos():
    return get_artists_images()


@app.route('/trello_setup')
@login_required
def trello_setup():
    return ensure_trello_setup_idempotent(current_user)


"""****************************************************** API ******************************************************"""


@app.route("/api")
def api():
    user = validate_api_key(request.headers.get('x-api-key'))
    if not user:
        return api_key_failure()
    else:
        tasks = Task.query.filter_by(user_id=int(user.id)).all()
        ret_tasks = []
        user_local_date = datetime.datetime.now(pytz.timezone(user.current_time_zone)).date()
        tasks.sort(key=lambda t: t.calculate_skew(user_local_date), reverse=True)
        average_daily_load = 0

        for task in tasks:
            due = task.calculate_skew(user_local_date) >= 1
            if task.is_after_delay(user_local_date):
                average_daily_load += 1 / task.ideal_interval
                if due:
                    ret_tasks.append({
                        "id": task.id,
                        "service": "zdone",
                        "raw_name": task.title,
                        "name": task.title,
                        "note": task.description,
                        "subtask_id": None,
                        "length_minutes": None,
                        "last_completion": humanize.naturaltime(
                            datetime.datetime.now(pytz.timezone(user.current_time_zone)).date() - task.last_completion),
                    })

        if average_daily_load >= 3.0:
            ret_tasks.insert(0, {
                "id": None,
                "service": "zdone",
                "raw_name": "Reconfigure tasks",
                "name": "Reconfigure tasks",
                "note": f"Average daily task load is {round(average_daily_load, 2)}, which is ≥3. Remove tasks or "
                        f"schedule them less frequently to avoid feeling overwhelmed.",
                "subtask_id": None,
                "length_minutes": None,
            })

        i = 0
        for tcard in get_updated_trello_cards(user):
            if tcard["list_name"] == "P0":
                ret_tasks.insert(i, tcard)
                i += 1
            else:
                ret_tasks.append(tcard)

        lists = [{"id": l.id, "name": l.name} for l in get_open_trello_lists(user) if l.name != 'Completed via zdone']

        current_date = datetime.datetime.now(pytz.timezone(user.current_time_zone)).date()
        this_sunday = current_date - datetime.timedelta(days=current_date.weekday() + 1)

        r = {
            "average_daily_load": round(average_daily_load, 2),
            "num_tasks_completed": len(get_recent_task_completions(user, date_start=this_sunday)),
            "tasks_to_do": ret_tasks,
            "time_zone": user.current_time_zone,
            "trello_lists": lists,
        }

        latest_reminder = get_most_recent_reminder(user)
        if latest_reminder:
            r["latest_reminder"] = {
                "title": latest_reminder.title,
                "message": latest_reminder.message,
                "id": latest_reminder.id,
            }
        r = make_response(r)
        r.mimetype = 'application/json'
        return r, 200


# POST https://api.trello.com/1/tokens/ACCESS_TOKEN/webhooks/?key=API_KEY with x-www-form-urlencoded:
# callbackURL: https://www.zdone.co/trello_webhook
# idModel: BACKLOGS_BOARD_ID
@app.route('/trello_webhook', methods=['POST', 'HEAD'])
def trello_webhook():
    req = request.get_json()
    if req:
        maybe_member = req.get("action", {}).get("idMemberCreator", None)
        user = User.query.filter_by(trello_member_id=maybe_member).one_or_none()
        if user:
            get_updated_trello_cards(user, force_refresh=True)
        else:
            with configure_scope() as scope:
                scope.set_tag("request", json.dumps(req))
                capture_exception(
                    ValueError(f"Received Trello webhook without a mapping to member {maybe_member} in the database."))

    if not req and flask.request.method == 'POST':
        capture_exception(ValueError(
            f"Received Trello webhook POST without a json payload. Payload should only be empty for HEAD requests, "
            f"which Trello sends the first time when a webhook is created as validation."))
    return success()
