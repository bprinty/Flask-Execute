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
class TestPlugin:

    def test_submit(self, celery):
        future = celery.submit(add, 1, 2)
        result = future.result(timeout=1)
        assert isinstance(future, Future)
        assert result == 3
        return

    def test_map(self, celery):
        pool = celery.map(add, [1, 2], [3, 4], [5, 6])
        assert len(pool) == 3
        results = pool.result(timeout=1)
        assert isinstance(pool, FuturePool)
        assert results == [3, 7, 11]
        return

    def test_current_task(self, celery):
        # check current task metadata from proxy
        future = celery.submit(task_id)
        ident = future.result()
        assert ident is not None

        # get the result and check the status
        future = celery.get(ident)
        assert not future.running()
        assert future.done()
        return

    def test_status(self, celery):
        status = celery.status()
        assert len(status)
        worker = list(status.keys())[0]
        assert status[worker] == 'OK'
        return

    def test_get(self, celery):
        future = celery.submit(add, 1, 2)
        future = celery.get(future.id)
        result = future.result(timeout=1)
        assert isinstance(future, Future)
        assert result == 3
        return

    def test_registered(self, celery):
        data = celery.inspect.registered()
        worker = list(data.keys())[0]
        assert 'tests.fixtures.task' in data[worker]
        return

    def test_scheduled(self, celery):
        data = celery.inspect.registered()
        worker = list(data.keys())[0]
        assert 'tests.fixtures.scheduled' in data[worker]
        return


class TestIntegration:

    def test_api(self, client, celery):
        # submit tasks via api
        response = client.post('/submit')
        assert response.status_code == 200
        assert len(response.json) == 5
        tasks = response.json

        # monitor results
        sleep = tasks[3]
        response = client.get('/monitor/{}'.format(sleep))
        assert response.status_code == 200
        assert response.json == {'status': 'PENDING'}

        # wait for something to finish and check statuses of other tasks
        celery.get(sleep).result()
        success = 0
        for task in tasks:
            response = client.get('/monitor/{}'.format(task))
            assert response.status_code == 200
            if 'SUCCESS' in response.json['status']:
                success += 1
        assert success > 0
        return
