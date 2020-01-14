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
