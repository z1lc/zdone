import os

basedir = os.path.abspath(os.path.dirname(__file__))

PRODUCTION_ENV = "production"
DEVELOPMENT_ENV = "development"


class Config(object):
    SECRET_KEY = os.environ.get('SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False


def filter_non_prod(event, hint):
    if event.environment == PRODUCTION_ENV:
        return event
    return None


def get_environment_from_environment_variable():
    valid_environments = [PRODUCTION_ENV, DEVELOPMENT_ENV]
    maybe_environment = os.environ.get('ZDONE_ENVIRONMENT')
    if maybe_environment not in valid_environments:
        raise ValueError(f"You need to set environment variable ZDONE_ENVIRONMENT to one of {valid_environments}!")
    return maybe_environment
