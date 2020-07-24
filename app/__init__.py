import sentry_sdk
from flask import Flask
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_talisman import Talisman
from sentry_sdk.integrations.flask import FlaskIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

from app import make_json_serializable
from app.config import Config

app = Flask(__name__)
if not app.debug:
    sentry_sdk.init(
        dsn="https://4dbd095718e34cb7bc4f7d64ecf488c4@sentry.io/1678958",
        integrations=[FlaskIntegration(), SqlalchemyIntegration()],
        send_default_pii=True
    )
Talisman(app, content_security_policy={
    'default-src': [
        '\'self\'',
        '\'unsafe-inline\'',
        '*.cloudflare.com',
        '*.datatables.net',
        '*.fontawesome.com',
        '*.google-analytics.com',
        '*.googleapis.com',
        '*.googletagmanager.com',
        '*.gstatic.com',
        '*.jquery.com',
        '*.sentry.io',
        '*.sentry-cdn.com',
        '*.w3schools.com',
        '*.tmdb.org',
        '*.youtube.com',
        '*.ytimg.com',
    ]
})
app.config.from_object(Config)
db = SQLAlchemy(app)

migrate = Migrate(app, db)
login = LoginManager(app)
login.login_view = 'login'

from . import routes
