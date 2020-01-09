#!/usr/bin/env python

from flask import Flask, jsonify
from flask_celery import Celery

app = Flask(__name__)
celery = Celery(app)

def ping():
    return 'pong'

@celery.schedule(hour=0, minute=0)
def beat():
    return True

@celery.task
def noop():
    return

@app.route('/ping')
def ping_handler():
    future = celery.submit(ping)
    result = future.result(timeout=1)
    return jsonify(msg=result)

@app.route('/task')
def task_handler():
    task = noop.delay()
    task.wait()
    return jsonify(msg='done' if task.result is None else 'fail')

import os
if __name__ == '__main__':
    import pdb; pdb.set_trace()
    app.run()
