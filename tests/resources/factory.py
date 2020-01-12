#!/usr/bin/env python
#
# Script for testing factory pattern plugin instantiation.
#
# Testing of different celery applications on the same
# machine can be difficult, so this script is provide
# a manual way of checking that functionality around
# plugin configuration doesn't regress. To test this
# instantiation method via this file, run (from the
# root directory of the repository):
#
# TODO: STOPPED HERE - FINISH
# --------------------------------------------------------

from flask import Flask, Blueprint, jsonify
from flask_celery import Celery
from celery.schedules import crontab

celery = Celery()
url = Blueprint('url', __name__)

def create_app():
    app = Flask(__name__)
    app.register_blueprint(url)
    celery.init_app(app)
    return app

def ping():
    return 'pong'

@celery.schedule(
    crontab(
        hour=0,
        minute=0
    ),
    args=(True,),
    kwargs={}
)
def beat(input):
    return input

@celery.task
def noop():
    return True

@celery.task(name='test')
def nope():
    return True

@url.route('/')
def index():
    return jsonify(status='ok')

@url.route('/ping')
def ping_handler():
    future = celery.submit(ping)
    result = future.result(timeout=1)
    return jsonify(msg=result)

@url.route('/task')
def task_handler():
    task1 = celery.task.noop.delay()
    task1.wait()
    task2 = celery.task['test'].delay()
    task2.wait()
    return jsonify(success=task1.result & task2.result)

if __name__ == '__main__':
    app = create_app()
    app.run()
