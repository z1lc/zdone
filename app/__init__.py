from flask import Flask
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_redis import FlaskRedis
from flask_sqlalchemy import SQLAlchemy
from flask_talisman import Talisman

from app.config import Config

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

migrate = Migrate(app, db)
redis_client = FlaskRedis(app)
login = LoginManager(app)
login.login_view = 'login'

from . import routes
