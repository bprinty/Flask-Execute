# -*- coding: utf-8 -*-
#
# Testing for pl
#
# ------------------------------------------------


# imports
# -------
from .fixtures import add, sleep


# tests
# -----
class TestTaskManagers:

    def test_task(self, celery):
        # check if task is registered
        data = celery.inspect.registered()
        worker = list(data.keys())[0]
        assert 'tests.fixtures.registered' in data[worker]

        # run registered task
        assert celery.task.registered()

        # run registered task with celery api
        task = celery.task.registered.delay()
        task.wait()
        assert task.result
        return

    def test_schedule(self, celery):
        # assert configuration
        assert 'scheduled-task' in celery.controller.conf['CELERYBEAT_SCHEDULE']
        schedule = celery.controller.conf['CELERYBEAT_SCHEDULE']['scheduled-task']
        assert schedule['task'] == 'tests.fixtures.scheduled'
        assert 'crontab' in str(type(schedule['schedule']))

        # run scheduled task
        assert celery.schedule.scheduled()

        # run registered task with celery api
        task = celery.schedule.scheduled.delay()
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
