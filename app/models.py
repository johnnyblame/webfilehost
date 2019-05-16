from flask import abort
import shutil
from app import db, app
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from flask_login import UserMixin
from app import login
import uuid
import os
import simplejson
from app.jsondate import date_decoder, date_encoder
from datetime import datetime, timedelta
from config import DELETE_KEY_LENGTH






class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))

    def __repr__(self):
        return '<User {}>'.format(self.username)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


@login.user_loader
def load_user(id):
    return User.query.get(int(id))


class SharedFile():
    GEN_KEY_ATTEMPTS = 10
    JSON_FILENAME = '.data.json'

    @classmethod
    def generate_key(cls):
        count = 0
        while count < cls.GEN_KEY_ATTEMPTS:
            key=uuid.uuid4().hex[:app.config['KEY_LENGTH']]
            relative_path = cls.key_to_path(key)
            path = os.path.join(app.config['UPLOAD_FOLDER'], relative_path)
            if not os.path.exists(path):
                return key
        raise Exception("Unable to generate a unique key after %s attempts." %
                        cls.GEN_KEY_ATTEMPTS)

    @classmethod
    def key_to_path(cls, key):
        relative_path = os.path.join(key[0], key[1], key)
        return relative_path


    @classmethod
    def get(cls, key):
        relative_path = cls.key_to_path(key)
        path = os.path.join(app.config['UPLOAD_FOLDER'], relative_path)
        with open(os.path.join(path, key + cls.JSON_FILENAME)) as json_file:
            infos = simplejson.load(json_file, object_hook=date_decoder)
            return cls(**infos)

    @classmethod
    def get_or_404(cls, key):
        try:
            return cls.get(key)
        except IOError:
            abort(404)

    @classmethod
    def find_all(cls):
        upload_folder = app.config['UPLOAD_FOLDER']
        for root, dirs, files in os.walk(upload_folder):
            current_dir = os.path.basename(root)
            if current_dir + cls.JSON_FILENAME in files:
                key = current_dir
                yield cls.get(key)

    def __init__(self, *args, **kwargs):
        self.filename = kwargs.get('filename')
        self.key = kwargs.get('key')
        self.path = kwargs.get('path')
        self.upload_date = kwargs.get('upload_date', datetime.today())
        self.expire_date = kwargs.get('expire_date', datetime.today())
        self.delete_key = kwargs.get('delete_key')
        self.remote_ip = kwargs.get('remote_ip')
        self.size = kwargs.get('size', 0)

    def save(self):
        self.filename = secure_filename(self.upload_file.filename)
        self.key = self.generate_key()
        self.relative_path = self.key_to_path(self.key)
        path = os.path.join(app.config['UPLOAD_FOLDER'], self.relative_path)
        os.makedirs(path)
        self.upload_file.save(os.path.join(path, self.filename))
        self.size = os.path.getsize(os.path.join(path, self.filename))

        self.delete_key = uuid.uuid4().hex[:DELETE_KEY_LENGTH]

        self.expire_date = datetime.today() + timedelta()
        infos = {}
        infos['filename'] = self.filename
        infos['key'] = self.key
        infos['path'] = self.relative_path
        infos['upload_date'] = datetime.today()
        infos['expire_date'] = self.expire_date
        infos['delete_key'] = self.delete_key
        infos['remote_ip'] = self.remote_ip
        infos['size'] = self.size
        path = os.path.join(app.config['UPLOAD_FOLDER'], self.relative_path)
        with open(os.path.join(path, self.key + self.JSON_FILENAME), 'w') as json_file:
            simplejson.dump(infos, json_file, cls=date_encoder)


    def delete(self):
        shutil.rmtree(os.path.join(app.config['UPLOAD_FOLDER'], self.path))


class NginxUploadFile(object):
    def __init__(self, filename, path, content_type=None, size=None):
        self.filename = filename
        self.path = path
        self.content_type = content_type
        self.size = size

    def save(self, dst):
        shutil.move(self.path, dst)


