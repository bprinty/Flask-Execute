# -*- coding: utf-8 -*-
#
# Testing for pl
#
# ------------------------------------------------


# imports
# -------
import pytest

from .fixtures import add, sleep, fail
from .fixtures import db, Item


# tests
# -----
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
        future = celery.submit(sleep, 10)
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

    def test_result(self, celery):
        # submit long command
        pool = celery.map(add, [1, 2], [1, 2], [1, 2])
        assert pool.status == 'PENDING'
        assert not pool.done()
        assert pool.running()

        # wait for timeout
        result = pool.result(timeout=1)
        assert result == [3, 3, 3]
        assert not pool.running()
        assert pool.done()
        assert not pool.running()
        assert not pool.cancelled()
        assert pool.status == 'SUCCESS'
        return

    def test_exception(self, celery):
        # submit failing task and assert result
        pool = celery.map(fail, [], [])
        with pytest.raises(AssertionError):
            pool.result(timeout=1)

        # assert exception details
        exe = pool.exception()[0]
        assert isinstance(exe, AssertionError)
        assert str(exe) == 'fail'
        assert pool.state == 'FAILURE'
        assert not pool.running()
        return

    def test_cancel(self, celery):
        # submit long command
        pool = celery.map(sleep, [3], [3], [3])
        assert pool.status == 'PENDING'
        assert pool.running()
        assert not pool.done()

        # cancel task and look at result
        pool.cancel(wait=True, timeout=1)
        assert pool.status == 'REVOKED'
        assert pool.cancelled()
        assert not pool.running()
        assert pool.done()
        return

    def test_callback(self, celery):
        # add callback function
        def callback(task):  ## noqa
            task = Item(name='pool-callback')
            db.session.add(task)
            db.session.commit()
            return

        # submit task and add callback
        pool = celery.map(add, [1, 2], [1, 2])
        pool.add_done_callback(callback)

        # assert item hasn't been created yet
        item = Item.query.filter_by(name='pool-callback').first()
        assert item is None
        pool.result(timeout=1)

        # after task finishes, assert item is created
        item = Item.query.filter_by(name='pool-callback').first()
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
