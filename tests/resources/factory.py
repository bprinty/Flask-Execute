#!/usr/bin/env python
#
# Application config testing factory method for instnatiating
# flask application and associated plugins. To run the tests
# associated with this file, execute:
#
# .. code-block:: bash
#
#      ~$ pytest tests/isolated/test_factory.py
# --------------------------------------------------------

from flask import Flask, Blueprint, jsonify
from flask_execute import Celery
from celery.schedules import crontab
from .. import SANDBOX

celery = Celery()
url = Blueprint('url', __name__)

def create_app():
    app = Flask(__name__)
    app.config['CELERY_LOG_DIR'] = SANDBOX
    app.config['CELERYD_CONCURRENCY'] = 4
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
