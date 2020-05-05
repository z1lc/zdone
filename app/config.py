import os

basedir = os.path.abspath(os.path.dirname(__file__))


class Config(object):
    SECRET_KEY = os.environ.get('SECRET_KEY')
    REDIS_URL = 'redis://h:pf86b269c32e3c33a7cae0e2fbd7e6e3b03a616909cf4ab54d8b8d84199fb3946@ec2-54-210-195-121.compute-1.amazonaws.com:14149' #os.environ.get('REDIS_URL')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
                              'sqlite:///' + os.path.join(basedir, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
