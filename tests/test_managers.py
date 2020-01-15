# -*- coding: utf-8 -*-
#
# Testing for pl
#
# ------------------------------------------------


# imports
# -------
import pytest

from flask_celery.plugin import Future, FuturePool

from .fixtures import add, sleep, fail, task_id, task
from .fixtures import db, Item


# tests
# -----
class TestRegistrationManager:

    def test_task(self, celery):
        # check if task is registered
        data = celery.inspect.registered()
        worker = list(data.keys())[0]
        assert 'tests.fixtures.task' in data[worker]

        # run registered task
        assert celery.task.task()

        # run registered task with celery api
        task = celery.task.task.delay()
        task.wait()
        assert task.result
        return

    def test_schedule(self, celery):
        data = celery.inspect.scheduled()
        worker = list(data.keys())[0]
        assert 'tests.fixtures.scheduled' in data[worker]

        # run scheduled task
        assert celery.schedule.scheduled()

        # run registered task with celery api
        task = celery.task.scheduled.delay()
        task.wait()
        assert task.result
        return

class TestCommandManagers:

    def test_inspect(self, celery):
        celery.submit(sleep).cancel(wait=True)
        celery.map(add, [1, 1], [1, 1], [1, 1])

        # revoked
        workers = celery.inspect.revoked()
        revoked = workers[list(workers.keys())[0]]
        assert len(revoked) > 0
        future = celery.get(revoked[0])
        assert revoked[0] == future.id

        # stats
        stats = celery.inspect.stats()
        assert len(stats) > 0
        key = list(stats.keys())[0]
        stat = stats[key]
        assert 'broker' in stat
        return

    def test_control(self, celery):
        workers = celery.control.heartbeat()
        beat = workers[list(workers.keys())[0]]
        assert beat is None
        return
