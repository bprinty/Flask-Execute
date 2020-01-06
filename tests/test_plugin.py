# -*- coding: utf-8 -*-
#
# Testing for pl
#
# ------------------------------------------------


# imports
# -------
from .fixtures import add, sleep, fail, celery

from flask_celery.plugin import Future, FuturePool


# session
# -------
class TestSubmit:

    def test_submit(self, celery):
        future = celery.submit(add, 1, 2)
        result = future.result(timeout=1)
        assert isinstance(future, Future)
        assert result == 3
        return

    def test_map(self, celery):
        pool = celery.map([[add, 1, 2], [add, 3, 4], [add, 5, 6]])
        results = pool.result(timeout=1)
        assert isinstance(pool, FuturePool)
        assert results == [3, 7, 11]
        return


class TestFuture:

    def test_cancel(self, celery):
        future = celery.submit(sleep, 3)
        assert future.running()
        assert not future.done()
        assert not future.cancelled()
        future.status ## ??

        future.cancel()
        assert future.cancelled()
        assert future.done()
        assert not future.running()
        future.status ## ??
        return

    def test_result(self, celery):
        future = celery.submit(add, 1, 2)
        assert future.running()
        assert not future.done()
        future.status ## ??

        result = future.result(timeout=1)
        assert result == 3
        assert not future.running()
        assert future.done()
        assert not future.cancelled()
        future.status ## ??
        return

    def test_exception(self, celery):
        future = celery.submit(fail)
        result = future.result(timeout=1)
        exe = future.exception()
        trace = future.traceback()
        assert isinstance(exe.msg, AssertionError)
        assert exe.msg == 'failed'
        future.status ## ??
        return

    def test_callback(self, celery):
        # TODO
        return

    def test_cancelled(self, celery):
        # implicitly tested by other methods
        return

    def test_running(self, celery):
        # implicitly tested by other methods
        return

    def test_done(self, celery):
        # implicitly tested by other methods
        return


class TestStatus:

    def test_api(self, client):
        # submit tasks via api
        response = client.post('/submit')
        assert response.status_code == 200
        assert False ## NOT SURE WHAT TO TEST HERE

        # monitor results
        response = client.get('/monitor')
        assert response.status_code == 200
        return

    def test_status_checks(self, celery):
        celery.submit(add, 1, 2)
        celery.submit(sleep)

        # active
        result = celery.active()
        print(result)
        assert False

        # scheduled
        result = celery.scheduled()
        assert False

        # reserved
        result = celery.reserved()
        assert False

        # revoked
        result = celery.revoked()
        assert False

        # registered
        result = celery.registered()
        assert False
        return

    def test_celery_stats(self, celery):
        celery.map([[add, 1, 2], [add, 3, 4], [add, 5, 6]])
        celery.submit(add, 7, 8).result(timeout=1)
        celery.submit(sleep)

        # get stats
        stats = celery.stats()
        print(stats)
        assert False
        return
