from datetime import datetime, timedelta
import os
basedir = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = '/tmp'
KEY_LENGTH = 6
NGINX_UPLOAD_MODULE_ENABLED = False
DELETE_KEY_LENGTH = 4






class Config(object):
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

