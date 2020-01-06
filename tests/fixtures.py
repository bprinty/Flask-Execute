# -*- coding: utf-8 -*-
#
# Fixtures for administration.
#
# ------------------------------------------------


# imports
# -------
import os
from flask import Flask, Blueprint, jsonify
from flask_sqlalchemy import SQLAlchemy

from flask_celery import Celery, current_task

from . import SANDBOX

# plugins
# -------
db = SQLAlchemy()
celery = Celery()
api = Blueprint('api', __name__)


# configs
# -------
class Config:
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False
    PROPAGATE_EXCEPTIONS = False
    SQLALCHEMY_DATABASE_URI = 'sqlite:///{}/dev.db'.format(SANDBOX)


class DevConfig(Config):
    ENV = 'development'
    CELERY_WORKERS = ['foo', 'bar']


class TestConfig(Config):
    ENV = 'testing'
    CELERY_ALWAYS_EAGER = True


# factory
# -------
def create_app(env='development'):
    """
    Application factory to use for spinning up development
    server tests.
    """
    env = os.environ.get('FLASK_ENV', env)
    if env == 'development':
        config = DevConfig
    elif env == 'testing':
        config = TestConfig

    app = Flask(__name__)
    app.config.from_object(config)
    db.init_app(app)
    celery.init_app(app)
    app.register_blueprint(api)
    return app


# functions
# ---------
def sleep(n=5):
    import time
    for count in range(n):
        time.sleep(0.1)
    return


def add(*args):
    from functools import reduce
    import time
    time.sleep(0.1)
    return reduce(lambda x, y: x + y, args)


def fail():
    raise AssertionError('fail')


# endpoints
# ---------
@api.route('/submit', methods=['POST'])
def submit():
    pool = celery.map(
        [add, 1, 2],
        [add, 3, 4],
        [sleep]
    )
    return jsonify([future for future in pool])


@api.route('/monitor/<ident>', methods=['GET'])
def monitor(ident):
    return jsonify(status=celery.get(ident).status)


@api.route('/ping', methods=['POST'])
def ping():
    def _(): return 'pong'
    result = celery.submit(_).result(timeout=1)
    return jsonify(result=result)


# models
# ------
class Task(db.Model):
    __tablename__ = 'tasks'

    # basic
    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.String)
