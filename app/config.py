import os

from app.log import log

basedir = os.path.abspath(os.path.dirname(__file__))

PRODUCTION = "production"
CI = "ci"
ENV_TO_SENTRY_REPORT_MAP = {PRODUCTION: True, "qa": False, "development": False, CI: False}


class Config(object):
    SECRET_KEY = os.environ.get("SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False


def filter_non_prod(event, hint):
    if ENV_TO_SENTRY_REPORT_MAP.get(event["environment"], False):
        return event
    return None


def is_prod():
    return get_environment_from_environment_variable() == PRODUCTION


def is_ci():
    return get_environment_from_environment_variable() == CI


def get_environment_from_environment_variable(should_log: bool = False):
    valid_environments = ENV_TO_SENTRY_REPORT_MAP.keys()
    maybe_environment = os.environ.get("ZDONE_ENVIRONMENT")
    if maybe_environment not in valid_environments:
        raise ValueError(f"You need to set environment variable ZDONE_ENVIRONMENT to one of {valid_environments}!")
    if maybe_environment and should_log:
        will_or_will_not = "WILL" if ENV_TO_SENTRY_REPORT_MAP[maybe_environment] else "WILL NOT"
        log(
            f"zdone is running in the '{maybe_environment}' environment. "
            f"Exceptions {will_or_will_not} be reported to Sentry."
        )
    return maybe_environment
