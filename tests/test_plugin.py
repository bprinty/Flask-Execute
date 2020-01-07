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


# session
# -------
class TestBase:

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

    def test_get(self, celery):
        future = celery.submit(add, 1, 2)
        future = celery.get(future.id)
        result = future.result(timeout=1)
        assert isinstance(future, Future)
        assert result == 3
        return

    # def test_registration(self):
    #     future = task.delay()
    #     future.wait(timeout=1)
    #     result = future.result
    #     assert result
    #     return


class TestFuture:

    def test_result(self, celery):
        # submit long command
        future = celery.submit(add, 1, 2)
        assert future.status == 'PENDING'
        assert not future.done()
        assert future.running()

        # wait for timeout
        result = future.result(timeout=1)
        assert result == 3
        assert not future.running()
        assert future.done()
        assert not future.running()
        assert not future.cancelled()
        assert future.status == 'SUCCESS'
        return

    def test_exception(self, celery):
        # submit failing task and assert result
        future = celery.submit(fail)
        with pytest.raises(AssertionError):
            future.result(timeout=1)

        # assert exception details
        exe = future.exception()
        assert isinstance(exe, AssertionError)
        assert str(exe) == 'fail'
        assert future.state == 'FAILURE'
        assert not future.running()
        return

    def test_cancel(self, celery):
        # submit long command
        future = celery.submit(sleep, 3)
        assert future.status == 'PENDING'
        assert future.running()
        assert not future.done()

        # cancel task and look at result
        future.cancel(wait=True, timeout=1)
        assert future.status == 'REVOKED'
        assert future.cancelled()
        assert not future.running()
        assert future.done()
        return

    def test_callback(self, celery):
        # add callback function
        def callback(task):  ## noqa
            task = Item(name='callback')
            db.session.add(task)
            db.session.commit()
            return

        # submit task and add callback
        future = celery.submit(add, 1, 2)
        future.add_done_callback(callback)

        # assert item hasn't been created yet
        item = Item.query.filter_by(name='callback').first()
        assert item is None
        future.result(timeout=1)

        # after task finishes, assert item is created
        item = Item.query.filter_by(name='callback').first()
        assert item is not None
        return

    def test_running(self, celery):
        # implicitly tested by other methods\
        return

    def test_cancelled(self, celery):
        # implicitly tested by other methods
        return

    def test_done(self, celery):
        # implicitly tested by other methods
        return


class TestFuturePool:
    pass


class TestStatus:

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

    def test_status_checks(self, celery):
        celery.submit(sleep).cancel(wait=True)
        celery.map(add, [1, 1], [1, 1], [1, 1])
        celery.map(sleep, [10], [10], [10], [10], [10])

        # active
        active = celery.active(collapse=True)
        assert len(active) > 0
        future = celery.get(active[0])
        assert active[0] == future.id
        workers = celery.active()
        assert len(workers) == 1

        # revoked
        revoked = celery.revoked(collapse=True)
        assert len(revoked) > 0
        future = celery.get(revoked[0])
        assert revoked[0] == future.id
        assert future.cancelled()
        workers = celery.revoked()
        assert len(workers) == 1

        # scheduled
        # TODO
        # scheduled = celery.scheduled()
        # print('scheduled {}'.format(scheduled))
        return

    def test_celery_stats(self, celery):
        celery.map([[add, 1, 2], [add, 3, 4], [add, 5, 6]])
        celery.submit(add, 7, 8).result(timeout=1)
        celery.submit(sleep)

        # stats
        stats = celery.stats()
        assert len(stats) == 1
        key = list(stats.keys())[0]
        stat = stats[key]
        assert 'broker' in stat
        return
