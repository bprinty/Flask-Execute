#!/usr/bin/env python

from flask import Flask, jsonify
from flask_celery import Celery
from celery.schedules import crontab

app = Flask(__name__)
celery = Celery(app)

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

@app.route('/')
def index():
    return jsonify(status='ok')

@app.route('/ping')
def ping_handler():
    future = celery.submit(ping)
    result = future.result(timeout=1)
    return jsonify(msg=result)

@app.route('/task')
def task_handler():
    task1 = celery.task.noop.delay()
    task1.wait()
    task2 = celery.task['test'].delay()
    task2.wait()
    return jsonify(success=task1.result & task2.result)

if __name__ == '__main__':
    app.run()