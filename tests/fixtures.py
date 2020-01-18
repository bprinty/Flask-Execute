# -*- coding: utf-8 -*-
#
# Fixtures for administration.
#
# ------------------------------------------------


# imports
# -------
import os
import time
from flask import Flask, Blueprint, jsonify
from flask_sqlalchemy import SQLAlchemy

from flask_execute import Celery, current_task

from . import SANDBOX


# helpers
# -------
class timeout(object):

    def __init__(self, seconds):
        self.seconds = seconds

    def __enter__(self):
        self.expiration = time.time() + self.seconds
        return self

    def __exit__(self, type, value, traceback):
        pass

    def tick(self, seconds=1):
        time.sleep(seconds)
        return

    @property
    def expired(self):
        return time.time() > self.expiration


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
    CELERY_LOG_DIR = SANDBOX
    CELERY_WORKERS = ['quorra']
    CELERYD_CONCURRENCY = 4


# factory
# -------
def create_app():
    """
    Application factory to use for spinning up development
    server tests.
    """
    app = Flask(__name__)
    app.config.from_object(Config)
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
    return True


def add(*args):
    from functools import reduce
    import time
    time.sleep(0.1)
    return reduce(lambda x, y: x + y, args)


def fail():
    raise AssertionError('fail')


def task_id():
    return current_task.id


@celery.task
def registered():
    return True


@celery.schedule(hour=0, minute=0, name='scheduled-task')
# @celery.schedule(5, name='scheduled-task')
def scheduled():
    return True


# endpoints
# ---------
@api.route('/submit', methods=['POST'])
def submit():
    pool = celery.map(add, [1, 2], [3, 4])
    pool.add(celery.submit(fail))
    pool.add(celery.submit(sleep))
    pool.add(celery.submit(task_id))
    return jsonify([future.id for future in pool])


@api.route('/monitor/<ident>', methods=['GET'])
def monitor(ident):
    return jsonify(status=celery.get(ident).status)


@api.route('/ping', methods=['POST'])
def ping():
    result = celery.submit(add, 1, 1).result(timeout=1)
    return jsonify(result='pong' if result == 2 else 'miss')


# models
# ------
class Item(db.Model):
    __tablename__ = 'items'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
