# -*- coding: utf-8 -*-
#
# Plugin Setup
#
# ------------------------------------------------


# imports
# -------
import os
import atexit
import subprocess
from datetime import datetime
import logging
import click
import json
from functools import reduce
from flask import g, current_app
from flask.cli import AppGroup
from werkzeug.local import LocalProxy
from celery import Celery as CeleryFactory
from celery.exceptions import TaskRevokedError
from celery.schedules import crontab

from .cli import cli, entrypoint
from .futures import Future, FuturePool
from .managers import CommandManager, TaskManager


# config
# ------
PROCESSES = {}


# proxies
# -------
def get_current_task():
    """
    Local proxy getter for managing current task and
    associated operations (i.e. state management).
    """
    if 'task' not in g:
        return None
    else:
        return g.task


current_task = LocalProxy(get_current_task)


# helpers
# -------
def dispatch(func, *args, **kwargs):
    """
    Dynamic abstracted task for pre-registration of
    celery tasks.
    """
    return func(*args, **kwargs)


@atexit.register
def stop_processes(timeout=5):
    """
    Clean all processes spawned by this plugin.
    """
    global PROCESSES
    for key in PROCESSES:
        PROCESSES[key].terminate()
        PROCESSES[key].wait()
    return


# plugin
# ------
class Celery(object):
    """
    Plugin for managing celery task execution in Flask.
    """

    def __init__(self, app=None):
        self._started = False
        self.logs = []
        self.task = TaskManager()
        self.inspect = CommandManager('inspect')
        self.control = CommandManager('control')
        if app is not None:
            self.init_app(app)
        return

    def init_app(self, app):

        # defaults
        self.app = app
        self.app.config.setdefault('CELERY_BROKER_URL', 'redis://localhost:6379')
        self.app.config.setdefault('CELERY_RESULT_BACKEND', 'redis://localhost:6379')
        self.app.config.setdefault('CELERY_WORKERS', 1)
        self.app.config.setdefault('CELERY_START_LOCAL_WORKERS', True)
        self.app.config.setdefault('CELERY_START_TIMEOUT', 10)
        self.app.config.setdefault('CELERY_ACCEPT_CONTENT', ['json', 'pickle'])
        self.app.config.setdefault('CELERY_TASK_SERIALIZER', 'pickle')
        self.app.config.setdefault('CELERY_RESULT_SERIALIZER', 'pickle')
        self.app.config.setdefault('CELERY_ALWAYS_EAGER', False)
        self.app.config.setdefault('CELERY_LOG_LEVEL', 'info')
        self.app.config.setdefault('CELERY_LOG_DIR', os.getcwd())
        self.app.config.setdefault('CELERY_FLOWER', True)
        self.app.config.setdefault('CELERY_FLOWER_PORT', 5555)
        self.app.config.setdefault('CELERY_FLOWER_ADDRESS', '127.0.0.1')

        # set up controller
        self.controller = CeleryFactory(
            self.app.name,
            backend=self.app.config['CELERY_RESULT_BACKEND'],
            broker=self.app.config['CELERY_BROKER_URL'],
        )
        self.controller.conf.update(self.app.config)

        # add custom task wrapping app context
        class ContextTask(self.controller.Task):
            """
            Custom celery task object that creates application context
            before dispatching celery command.
            """
            config = self.app.config

            def __call__(self, *args, **kwargs):
                # if eager, run without creating new context
                if self.config['CELERY_ALWAYS_EAGER']:
                    g.task = self.request
                    return self.run(*args, **kwargs)

                # otherwise, create new context and run the command
                else:
                    from flask.cli import ScriptInfo
                    info = ScriptInfo()
                    app = info.load_app()
                    with app.app_context():
                        g.task = self.request
                        return self.run(*args, **kwargs)

        self.controller.Task = ContextTask

        # link celery  extension to registered application
        if not hasattr(self.app, 'extensions'):
            self.app.extensions = {}
        self.app.extensions['celery'] = self

        # register dynamic task
        self.wrapper = self.controller.task(dispatch)
        self.task.init_celery(self.controller)

        # register cli entry points
        self.app.cli.add_command(entrypoint)
        return

    @property
    def processes(self):
        """
        Plugin proxy for global processes data.
        """
        global PROCESSES
        return PROCESSES

    def start(self, timeout=None):
        """
        Start local celery workers specified in config.
        """
        timeout = timeout or self.app.config['CELERY_START_TIMEOUT']
        running = self.status()

        # reformat worker specification
        if isinstance(self.app.config['CELERY_WORKERS'], int):
            workers = [
                'worker{}'.format(i + 1)
                for i in range(self.app.config['CELERY_WORKERS'])
            ]
        elif isinstance(self.app.config['CELERY_WORKERS'], (list, tuple)):
            workers = self.app.config['CELERY_WORKERS']
        else:
            raise AssertionError(
                'No rule for processing input type {} for `CELERY_WORKERS` '
                'option.'.format(type(self.app.config['CELERY_WORKERS'])))

        # make sure log directory exists
        if not os.path.exists(self.app.config['CELERY_LOG_DIR']):
            os.makedirs(self.app.config['CELERY_LOG_DIR'])

        # spawn local workers
        for worker in workers:

            # don't start worker if already running
            available = False
            for name, status in running.items():
                if worker + '@' in name:
                    available = status == 'OK'
                    break
            if available:
                continue

            # configure logging
            level = self.app.config['CELERY_LOG_LEVEL']
            cmd = 'worker --loglevel={} -n {}@%h'.format(level, worker)

            # add logging to command
            logfile = os.path.join(self.app.config['CELERY_LOG_DIR'], worker + '.log')
            self.logs.append(logfile)
            cmd += ' --logfile={}'.format(logfile)

            # start worker
            self.processes[worker] = cli.popen(cmd)

        # start flower (if specified)
        if self.app.config['CELERY_FLOWER']:

            # set up flower logs
            self.logs.append(os.path.join(current_app.config['CELERY_LOG_DIR'], 'flower.log'))

            # run flower and monitor
            self.processes['flower'] = cli.popen(
                'flower --address={} --port={} --logging={} --log-file-prefix={}'.format(
                    current_app.config['CELERY_FLOWER_ADDRESS'],
                    current_app.config['CELERY_FLOWER_PORT'],
                    current_app.config['CELERY_LOG_LEVEL'],
                    os.path.join(current_app.config['CELERY_LOG_DIR'], 'flower.log')
                )
            )

        # wait for workers to start
        then, delta = datetime.now(), 0
        while delta < timeout:
            delta = (datetime.now() - then).seconds
            if self.status():
                break
        if delta >= timeout:
            raise AssertionError(
                'Could not connect to celery workers after {} seconds. '
                'See worker logs for details.'.format(timeout)
            )
        return

    def stop(self, timeout=5):
        """
        Stop all processes started by this plugin.
        """
        return stop_processes(timeout=5)

    def schedule(self, func, *args, **kwargs): # schedule, args=tuple(), kwargs=dict(), name=None, **kwargs):
        """
        Schedule task to run according to specified CRON schedule.
        """
        # sargs = kwargs.pop('args', ())
        # skwargs = kwargs.pop('kwargs', {})
        # if not len(args):
        #     cargs = {}
        #     for param in []:
        #     args = [crontab(**kwargs)]
        def decorator(func):
            def _(*args, **kwargs):
                return func(*args, **kwargs)
            return _
        return decorator

    def submit(self, func, *args, **kwargs):
        """
        Submit function to celery worker for processing.
        """
        # start celery if first ``submit()`` call.
        if not self.app.config['CELERY_ALWAYS_EAGER'] and \
           self.app.config['CELERY_START_LOCAL_WORKERS'] and \
           not self._started:
            self.start()
            self._started = True

        # reimport function for serialization if not using flask cli
        if '__main__' in func.__module__:
            mod = func.__module__.replace('__main__', self.app.name)
            app = __import__(mod, fromlist=[func.__name__])
            func = getattr(app, func.__name__)

        # evaluate context locals to avoid pickling issues
        args = list(args)
        for idx, arg in enumerate(args):
            if isinstance(arg, LocalProxy):
                args[idx] = arg._get_current_object()
        for key in kwargs:
            if isinstance(kwargs[key], LocalProxy):
                kwargs[key] = kwargs[key]._get_current_object()

        # submit
        return Future(self.wrapper.delay(func, *args, **kwargs))

    def map(self, func, *args, **kwargs):
        """
        Submit iterable of functions/arguments to celery and
        """
        futures = []
        for arg in args:
            futures.append(self.submit(func, *arg, **kwargs))
        return FuturePool(futures)

    def get(self, ident):
        """
        Retrieve a Future object for the specified task.
        """
        from celery.result import AsyncResult
        task = AsyncResult(ident)
        return Future(task)

    def status(self):
        """
        Return status of celery server.
        """
        workers = {}
        try:
            output = cli.output('status')
            for stat in output.split('\n'):
                if '@' in stat:
                    worker, health = stat.split(': ')
                    workers[worker] = health
        except subprocess.CalledProcessError:
            pass
        return workers
