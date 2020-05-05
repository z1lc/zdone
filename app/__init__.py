import sentry_sdk
from flask import Flask
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_redis import FlaskRedis
from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy
from flask_talisman import Talisman
from sentry_sdk.integrations.flask import FlaskIntegration

from app import make_json_serializable
from app.config import Config

sentry_sdk.init(
    dsn="https://4dbd095718e34cb7bc4f7d64ecf488c4@sentry.io/1678958",
    integrations=[FlaskIntegration()],
    send_default_pii=True
)

app = Flask(__name__)
Talisman(content_security_policy={
    'default-src': [
        '\'self\'',
        '*.jquery.com',
        '*.w3schools.com'
    ]
})
app.config.from_object(Config)
db = SQLAlchemy(app)
socketio = SocketIO(app)

migrate = Migrate(app, db)
redis_client = FlaskRedis(app)
login = LoginManager(app)
login.login_view = 'login'

from . import routes
