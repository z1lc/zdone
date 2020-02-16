import os

from app import kv

basedir = os.path.abspath(os.path.dirname(__file__))


class Config(object):
    SECRET_KEY = os.environ.get('SECRET_KEY')
    REDIS_URL = kv.get('REDIS_URL') if 'z1lc' in os.environ['COMPUTERNAME'] else os.environ.get('REDIS_URL')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
                              'sqlite:///' + os.path.join(basedir, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
