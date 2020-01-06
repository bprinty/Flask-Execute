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
import logging
import click
import json
from flask import g, current_app
from flask.cli import AppGroup
from werkzeug.local import LocalProxy
from celery import Celery as CeleryFactory


# config
# ------
WORKERS = {}


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
def stop_workers(timeout=5):
    """
    Clean all processes spawned by this plugin.

    TODO: MIGHT NOT BE NECESSARY
    """
    global WORKERS
    for key in WORKERS:
        logging.info('Shutting down worker {}'.format(key))
        WORKERS[key].terminate()
    return


def ping(input):
    """
    NOOP function for pinging workers.
    """
    return input


# classes
# -------
class cli:
    """
    Data structure for wrapping celery internal celery commands
    executed throughout the plugin.
    """
    def popen(self, cmd, stderr=subprocess.STDOUT, stdout=None):
        """
        Run subprocess.popen for executing celery command in background.
        """
        return subprocess.popen(
            'exec celery -A flask_celery.celery {}'.format(cmd),
            stderr=stderr, stdout=stdout, shell=True
        )

    def call(self, cmd, stderr=subprocess.STDOUT, stdout=None):
        """
        Run subprocess.call for executing celery command.
        """
        return subprocess.call(
            'exec celery -A flask_celery.celery {}'.format(cmd),
            stderr=stderr, stdout=stdout, shell=True
        )

    def status(self):
        """
        Run subprocess.check_output for checking celery status.
        """
        return subprocess.check_output(
            'celery -A flask_celery.celery status',
            stderr=subprocess.STDOUT, shell=True
        ).decode('utf-8')


class Future(object):
    """
    Wrapper around celery.AsyncResult to provide an API similar
    to the ``concurrent.futures`` API.
    """

    def __init__(self, result):
        self.__proxy__ = result
        return

    def __getattr__(self, key):
        return getattr(self.__proxy__, key)

    def result(self, timeout=0):
        self.__proxy__.wait(timeout=timeout)
        return self.__proxy__.result

    def cancel(self):
        self.__proxy__.revoke()
        return

    def running(self):
        return self.__proxy__.state in ['STARTED']

    def done(self):
        return self.__proxy__.state in ['FAILURE', 'SUCCESS']

    def exception(self):
        # parse from traceback?
        return

    def traceback(self):
        return self.__proxy__.traceback

    def add_done_callback(self, callback):
        self.__proxy__.then(callback)
        return


class FuturePool(object):
    """
    Class for managing pool of futures for grouped operations.
    """

    def __init__(self, futures):
        self.futures = futures
        return

    def __iter__(self):
        for future in self.futures:
            yield future
        return

    def result(timeout=0):
        return [
            future.result(timeout=timeout)
            for future in self.futures
        ]

    def cancel(self):
        return [
            future.cancel()
            for future in self.futures
        ]

    def running(self):
        for future in self.futures:
            if future.running():
                return True
        return False

    def done(self):
        for future in self.futures:
            if not future.done():
                return False
        return True

    def exception(self):
        # TODO
        return

    def traceback(self):
        # TODO
        return


# plugin
# ------
class Celery(object):
    """
    Plugin for managing celery task execution in Flask.
    """

    def __init__(self, app=None):
        if app is not None:
            self.init_app(app)
        return

    def init_app(self, app):
        # defaults
        self.app = app
        self.app.config.setdefault('CELERY_BROKER_URL', 'redis://localhost:6379')
        self.app.config.setdefault('CELERY_RESULT_BACKEND', 'redis://localhost:6379')
        self.app.config.setdefault('CELERY_WORKERS', 1)
        self.app.config.setdefault('CELERY_START_LOCAL_WORKERS', False)
        self.app.config.setdefault('CELERY_START_LOCAL_MONITOR', False)
        self.app.config.setdefault('CELERY_MONITOR_PORT', None)
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
            self.app.import_name,
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
                    g.task = self
                    return self.run(*args, **kwargs)

                # otherwise, create new context and run the command
                else:
                    from flask.cli import ScriptInfo
                    info = ScriptInfo()
                    app = info.load_app()
                    with app.app_context():
                        g.task = self
                        return self.run(*args, **kwargs)

        self.controller.Task = ContextTask
        if not hasattr(self.app, 'extensions'):
            self.app.extensions = {}
        self.app.extensions['celery'] = self

        # register dynamic task
        self.wrapper = self.controller.task(dispatch)

        # add cli commands for starting workers
        celery = AppGroup('celery')

        @celery.command('worker')
        @click.argument('args', nargs=-1, type=click.UNPROCESSED)
        def worker(args):
            """
            Start single celery worker from configuration.
            """
            # TODO: parse args for worker names and consolidate with
            #       configuration
            return cli.call(
                "worker --loglevel={} {}".format(
                    self.app.config['CELERY_LOG_LEVEL'], ' '.join(args)
                )
            )

        @celery.command('cluster')
        def cluster():
            """
            Start local cluster of celery workers and flower
            monitoring tool (if specified).
            """
            self.start()
            if self.app.config['CELERY_FLOWER']:
                flower = cli.popen(
                    '--address={} --port={}'.format(
                        self.app.config['CELERY_FLOWER_ADDRESS'],
                        self.app.config['CELERY_FLOWER_PORT'],
                    )
                )

            while True:
                time.sleep(1)

            # TODO: figure out how to stream logs from workers
            # global WORKERS
            # while True:
            #     for worker in WORKERS:
            #         print('in!')
            #         print('out!')
            return

        @celery.command('status')
        def status():
            """
            Check statuses of celery workers.
            """
            result = self.status()
            print(json.dumps(result, indent=2))
            return result

        self.app.cli.add_command(celery)

        # spawn local worker (if specified)
        if self.app.config['CELERY_START_LOCAL_WORKERS']:

            # TODO: FIGURE OUT HOW TO DO THIS WHENEVER THE FIRST CELERY.SUBMIT() CALL IS MADE
            @self.app.before_first_request
            def spawn_workers():
                """
                Start local workers on appolication boot.
                """
                self.start()
                if not self.ping():
                    raise AssertionError('Could not fork local celery workers. See celery logs for details.')
                return

        return

    def status(self):
        """
        Return status of celery server.
        """
        # quick check with ping
        ping = self.ping()
        if not ping:
            return dict(
                ping=ping,
                error='Could not poll status of celery workers. Workers are all down or unavailable.'
            )

        # poll specific statuses
        workers = {}
        for stat in cli.status().split('\n'):
            if '@' in stat:
                worker, health = stat.split(': ')
                workers[worker] = health

        return dict(
            ping=ping,
            workers=workers,
        )

    def start(self, log=True):
        """
        Start local celery workers specified in config.
        """
        # check if workers are already running and connected
        if self.ping(1):
            return

        # reformat worker specification
        global WORKERS
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

        # spawn local workers
        for worker in workers:
            current_app.logger.info('spawning local worker: {}'.format(worker))
            level = self.app.config['CELERY_LOG_LEVEL']
            logfile = os.path.join(self.app.config['CELERY_LOG_DIR'], worker + '.log')
            with open(logfile, 'a') as lf:
                proc = cli.popen("worker --loglevel={} -n {}@%h".format(level, worker), stdout=lf)
            WORKERS[worker] = proc
        return

    def ping(self, timeout=3, tries=2):
        """
        Ping celery workers by running simple task and
        return worker health status.
        """
        future = self.submit(ping, 'pong')
        for i in range(tries):
            try:
                future.wait(timeout)
                return future.successful()
            except Exception:
                pass
        return False

    def submit(self, func, *args, **kwargs):
        """
        Submit function to celery worker for processing.
        """
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
            self.submit(func, *arg, **kwargs)

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

    def get(self, ident):
        """
        Retrieve a Future object for the specified task.
        """
        from celery.result import AsyncResult
        task = AsyncResult(ident)
        return Future(task)
