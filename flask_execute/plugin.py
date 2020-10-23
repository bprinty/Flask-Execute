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
from flask import g, current_app
from werkzeug.local import LocalProxy
from celery import Celery as CeleryFactory

from .cli import cli, entrypoint
from .futures import Future, FuturePool
from .managers import CommandManager, TaskManager, ScheduleManager


# config
# ------
PROCESSES = {}


# proxies
# -------
def get_current_db():
    if hasattr(current_app, 'extensions') and \
       'sqlalchemy' in current_app.extensions:
        return current_app.extensions['sqlalchemy'].db
    else:
        return None


def get_current_task():
    """
    Local proxy getter for managing current task and
    associated operations (i.e. state management).
    """
    if 'task' not in g:
        return None
    else:
        return g.task


current_db = LocalProxy(get_current_db)
current_task = LocalProxy(get_current_task)


# helpers
# -------
def dispatch(func, *args, **kwargs):
    """
    Dynamic abstracted task for pre-registration of
    celery tasks.

    Arguments:
        func (callable): Function to deserialize and call.
        *args (list, tuple): Arguments to pass to function.
        **kwargs (dict): Keyword arguments to pass to function.
    """
    return func(*args, **kwargs)


@atexit.register
def stop_processes(timeout=None):
    """
    Clean all processes spawned by this plugin.

    timeout (int): Timeout to wait for processes to join
        after termination signal is sent.
    """
    global PROCESSES
    for key in PROCESSES:
        PROCESSES[key].terminate()
        PROCESSES[key].wait(timeout=timeout)
    return


def requery(args, kwargs):
    """
    Re-query database models passed into function to enable
    safer threaded operations. This is typically reserved
    for api methods that submit asyncronous tasks to a separate
    executor that uses a different database session.
    """
    # get local db proxy
    db = current_db

    # re-query processor
    def process(obj):
        if db is not None:
            if isinstance(obj, db.Model):
                if hasattr(obj, 'id'):
                    obj = obj.__class__.query.filter_by(id=obj.id).first()
        return obj

    # arg processing
    args = list(args)
    for idx, arg in enumerate(args):
        args[idx] = process(arg)

    # kwarg processing
    for key in kwargs:
        kwargs[key] = process(kwargs[key])

    return args, kwargs


def deproxy(args, kwargs):
    """
    Query local objects from proxies passed into function for
    safer threaded operations.
    """
    # deproxy processor
    def process(obj):
        if isinstance(obj, LocalProxy):
            obj = obj._get_current_object()
        return obj

    # arg processing
    args = list(args)
    for idx, arg in enumerate(args):
        args[idx] = process(arg)

    # kwarg processing
    for key in kwargs:
        kwargs[key] = process(kwargs[key])

    return args, kwargs


# plugin
# ------
class Celery(object):
    """
    Plugin for managing celery task execution in Flask.

    Arguments:
        app (Flask): Flask application object.
        base_task (celery.Task): Celery task object to
            use as base task for celery operations.
    """

    def __init__(self, app=None, base_task=None):
        self._started = False
        self.base_task = None
        self.logs = []
        self.task = TaskManager()
        self.schedule = ScheduleManager()
        self.inspect = CommandManager('inspect')
        self.control = CommandManager('control')
        if app is not None:
            self.init_app(app)
        return

    def init_app(self, app):

        # defaults
        self.app = app
        self.app.config.setdefault('CELERY_BROKER_URL', 'redis://localhost:6379')
        self.app.config.setdefault('CELERY_RESULT_BACKEND', 'redis://')
        self.app.config.setdefault('CELERY_WORKERS', 1)
        self.app.config.setdefault('CELERY_START_LOCAL_WORKERS', True)
        self.app.config.setdefault('CELERY_START_TIMEOUT', 10)
        self.app.config.setdefault('CELERY_ACCEPT_CONTENT', ['json', 'pickle'])
        self.app.config.setdefault('CELERY_TASK_SERIALIZER', 'pickle')
        self.app.config.setdefault('CELERY_RESULT_SERIALIZER', 'pickle')
        self.app.config.setdefault('CELERY_SANITIZE_ARGUMENTS', True)
        self.app.config.setdefault('CELERY_ALWAYS_EAGER', False)
        self.app.config.setdefault('CELERY_LOG_LEVEL', 'info')
        self.app.config.setdefault('CELERY_LOG_DIR', os.getcwd())
        self.app.config.setdefault('CELERY_FLOWER', True)
        self.app.config.setdefault('CELERY_FLOWER_PORT', 5555)
        self.app.config.setdefault('CELERY_FLOWER_ADDRESS', '127.0.0.1')
        self.app.config.setdefault('CELERY_SCHEDULER', True)
        self.app.config.setdefault('CELERYBEAT_SCHEDULE', {})

        # set up controller
        self.controller = CeleryFactory(
            self.app.name,
            backend=self.app.config['CELERY_RESULT_BACKEND'],
            broker=self.app.config['CELERY_BROKER_URL'],
        )
        for key in self.app.config:
            self.controller.conf[key] = self.app.config[key]
        if self.base_task is not None:
            self.controller.Task = self.base_task

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
                        if self.config['CELERY_SANITIZE_ARGUMENTS']:
                            args, kwargs = requery(args, kwargs)
                        return self.run(*args, **kwargs)

        self.controller.Task = ContextTask

        # link celery extension to registered application
        if not hasattr(self.app, 'extensions'):
            self.app.extensions = {}
        self.app.extensions['celery'] = self

        # register dynamic task
        self.wrapper = self.controller.task(dispatch)
        self.task.init_celery(self.controller)
        self.schedule.init_celery(self.controller)

        # register cli entry points
        self.app.cli.add_command(entrypoint)
        return

    @property
    def processes(self):
        """
        Proxy with list of all subprocesses managed by the plugin.
        """
        global PROCESSES
        return PROCESSES

    def start(self, timeout=None):
        """
        Start local celery workers specified in config.

        Arguments:
            timeout (int): Timeout to wait for processes to start
                after process is submitted. ``celery status`` is
                used to poll the status of workers.
        """
        timeout = timeout or self.app.config['CELERY_START_TIMEOUT']
        running = self.status()

        # TODO: Add ability to specify worker configuration via nested config option

        # reformat worker specification
        worker_args = {}
        if isinstance(self.app.config['CELERY_WORKERS'], int):
            workers = [
                'worker{}'.format(i + 1)
                for i in range(self.app.config['CELERY_WORKERS'])
            ]
        elif isinstance(self.app.config['CELERY_WORKERS'], (list, tuple)):
            workers = self.app.config['CELERY_WORKERS']
        elif isinstance(self.app.config['CELERY_WORKERS'], dict):
            worker_args = self.app.config['CELERY_WORKERS']
            workers = list(worker_args.keys())
        else:
            raise AssertionError(
                'No rule for processing input type {} for `CELERY_WORKERS` '
                'option.'.format(type(self.app.config['CELERY_WORKERS'])))

        # make sure log directory exists
        if not os.path.exists(self.app.config['CELERY_LOG_DIR']):
            os.makedirs(self.app.config['CELERY_LOG_DIR'])

        # start flower (if specified)
        if self.app.config['CELERY_FLOWER']:
            logfile = os.path.join(self.app.config['CELERY_LOG_DIR'], 'flower.log')
            self.logs.append(logfile)
            self.processes['flower'] = cli.popen(
                'flower --address={} --port={} --logging={} --log-file-prefix={}'.format(
                    self.app.config['CELERY_FLOWER_ADDRESS'],
                    self.app.config['CELERY_FLOWER_PORT'],
                    self.app.config['CELERY_LOG_LEVEL'],
                    logfile
                )
            )

        # start celerybeat (if specified and tasks registered)
        if self.app.config['CELERY_SCHEDULER'] and len(self.app.config['CELERYBEAT_SCHEDULE']):
            logfile = os.path.join(self.app.config['CELERY_LOG_DIR'], 'scheduler.log')
            pidfile = os.path.join(self.app.config['CELERY_LOG_DIR'], 'scheduler.pid')
            schedule = os.path.join(self.app.config['CELERY_LOG_DIR'], 'scheduler.db')
            self.logs.append(logfile)
            self.processes['scheduler'] = cli.popen(
                'beat --loglevel={} --logfile={} --pidfile={} --schedule={}'.format(
                    current_app.config['CELERY_LOG_LEVEL'],
                    logfile, pidfile, schedule
                )
            )

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

            # configure extra arguments
            if worker not in worker_args:
                worker_args[worker] = {}

            # configure logging
            level = self.app.config['CELERY_LOG_LEVEL']
            logfile = os.path.join(self.app.config['CELERY_LOG_DIR'], worker + '.log')
            self.logs.append(logfile)

            # configure worker arg defaults
            worker_args[worker].setdefault('loglevel', level)
            worker_args[worker].setdefault('hostname', worker + '@%h')
            worker_args[worker].setdefault('logfile', logfile)

            # set up command using worker args
            cmd = 'worker'
            for key, value in worker_args[worker].items():
                cmd += ' --{}={}'.format(key, value)

            # start worker
            self.processes[worker] = cli.popen(cmd)

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

    def stop(self, timeout=None):
        """
        Stop all processes started by this plugin.

        Arguments:
            timeout (int): Timeout to wait for processes to join
                after termination signal is sent.
        """
        timeout = timeout or self.app.config['CELERY_START_TIMEOUT']
        return stop_processes(timeout=timeout)

    def submit(self, func, *args, **kwargs):
        """
        Submit function to celery worker for processing.

        Arguments:
            queue (str): Name of queue to submit function to.
            countdown (int): Number of seconds to wait before
                submitting function.
            eta (datetime): Datetime object describing when
                task should be executed.
            retry (bool): Whether or not to retry the task
                upon failure.
            *args (list): Arguments to function.
            **kwargs (dict): Keyword arguments to function.
        """
        options = {}
        for key in ['queue', 'countdown', 'eta', 'retry']:
            if key in kwargs:
                options[key] = kwargs.pop(key)

        return self.apply(func, args=args, kwargs=kwargs, **options)

    def apply(self, func, args=tuple(), kwargs=dict(), **options):
        """
        Submit function to celery worker for processing.

        Arguments:
            args (list): Arguments to function.
            kwargs (dict): Keyword arguments to function.
            **options (dict): Arbitrary celery options to pass to
                underlying ``apply_async()`` function. See celery
                documentation for details.
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

        # submit task and sanitize inputs
        args, kwargs = deproxy(args, kwargs)
        args.insert(0, func)
        return Future(self.wrapper.apply_async(args=args, kwargs=kwargs, **options))

    def map(self, func, *args, **kwargs):
        """
        Submit function with iterable of arguments to celery and
        return ``FuturePool`` object containing all task result
        ``Future`` objects.

        Arguments:
            queue (str): Name of queue to submit function to.
            countdown (int): Number of seconds to wait before
                submitting function.
            eta (datetime): Datetime object describing when
                task should be executed.
            retry (bool): Whether or not to retry the task
                upon failure.
            *args (list): list of arguments to pass to functions.
            **kwargs (dict): Keyword arguments to apply for every
                function.
        """
        futures = []
        for arg in args:
            futures.append(self.submit(func, *arg, **kwargs))
        return FuturePool(futures)

    def get(self, ident):
        """
        Retrieve a Future object for the specified task.

        Arguments:
            ident (str): Identifier for task to query.
        """
        from celery.result import AsyncResult
        task = AsyncResult(ident)
        return Future(task)

    def status(self, timeout=5):
        """
        Return status of celery server as dictionary.
        """
        workers = {}
        try:
            output = cli.output('status', timeout=timeout)
            for stat in output.split('\n'):
                if '@' in stat:
                    worker, health = stat.split(': ')
                    workers[worker] = health
        except subprocess.CalledProcessError:
            pass
        return workers
