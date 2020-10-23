#
# All manager objects for complex operations provided
# by plugin properties.
#
# ------------------------------------------------


# imports
# -------
import re
import sys
import json
import subprocess
from celery.schedules import crontab

from .cli import cli


# classes
# -------
class TaskManager(object):
    """
    Object for managing registered celery tasks, providing
    users a way of submitting tasks via the celery API when
    using the factory pattern for configuring a flask application.

    This proxy for the @celery.task decorator is designed to
    manage two things:

    1. For applications set up with the flask application directly,
       register tasks with the celery application directly. This
       has the same effect as the original mechanism for configuring
       celery alongside a Flask application.

    2. For applications set up using the factory pattern,
       store all registered tasks internally so they can be
       registered with the celery application once the plugin
       as been initialized with a flask application instance.
    """

    def __init__(self):
        self.__app__ = None
        self.__registered__ = {}
        self.__tasks__ = {}
        self.__funcs__ = {}
        return

    def __call__(self, *args, **kwargs):
        """
        Internal decorator logic for ``celery.task``.
        """
        # plugin hasn't been initialized
        if self.__app__ is None:
            def _(func):
                self.__registered__[func.__name__] = {'func': func, 'args': args, 'kwargs': kwargs}
                return func

        # plugin has been initialized
        else:
            def _(func):
                func = self.__app__.task(*args, **kwargs)(func)
                if func.name not in self.__tasks__:
                    self.__tasks__[func.name] = func
                    self.__funcs__[func.__name__] = func
                return func

        # return decorated function if called directly
        if len(args) == 1 and len(kwargs) == 0 and callable(args[0]):
            func, args = args[0], args[1:]
            return _(func)

        # return inner decorator
        else:
            return _

    def __getattr__(self, key):
        if key not in self.__tasks__:
            if key not in self.__funcs__:
                raise AttributeError('Task ``{}`` has not been registered'.format(key))
            return self.__funcs__[key]
        return self.__tasks__[key]

    def __getitem__(self, key):
        return self.__getattr__(key)

    def init_celery(self, controller):
        """
        Initialize the task manager with a celery controller. This
        will register all decorated tasks with the specified
        ``controller`` (celery application).

        Args:
            controller (Celery): Celery application instance to
                register tasks for.
        """
        self.__app__ = controller
        for key, item in self.__registered__.items():
            if not len(item['args']) and not len(item['kwargs']):
                self(item['func'])
            else:
                self(*item['args'], **item['kwargs'])(item['func'])
        return


class ScheduleManager(object):
    """
    Object for managing scheduled celery tasks, providing
    users a way of scheduling tasks via the celery API when
    using the factory pattern for configuring a flask application.

    This proxy for the @celery.task decorator is designed to
    manage two things:

    1. For applications set up with the flask application directly,
       schedule tasks with the celery application directly. This
       has the same effect as the original mechanism for configuring
       celery alongside a Flask application.

    2. For applications set up using the factory pattern,
       store all scheduled tasks internally so they can be
       registered with the celery application once the plugin
       as been initialized with a flask application instance.
    """

    def __init__(self):
        self.__app__ = None
        self.__registered__ = {}
        self.__tasks__ = {}
        self.__funcs__ = {}
        return

    def __call__(self, schedule=None, name=None, args=tuple(), kwargs=dict(), options=dict(), **skwargs):
        """
        Internal decorator logic for ``celery.schedule``.
        """
        # handle ambiguous schedule input
        if schedule is not None and len(skwargs):
            raise AssertionError(
                'Invalid schedule arguments - please see documentation for '
                'how to use @celery.schedule'
            )

        # handle crontab input
        if schedule is None and len(skwargs):
            schedule = crontab(**skwargs)

        # handle missing schedule input
        if schedule is None:
            raise AssertionError('Schedule for periodic task must be defined, either via numeric arguments or crontab keywords. See documentation for details.')

        # plugin hasn't been initialized
        if self.__app__ is None:
            def _(func):
                key = name or func.__module__ + '.' + func.__name__
                self.__registered__[key] = {
                    'func': func,
                    'schedule': schedule,
                    'args': args,
                    'kwargs': kwargs,
                    'options': options,
                }
                return func

        # plugin has been initialized
        else:
            def _(func):
                if not hasattr(func, 'name'):
                    func = self.__app__.task(func)

                # add schedule to beat manager
                self.__app__.conf['CELERYBEAT_SCHEDULE'][name] = {
                    'task': func.name,
                    'schedule': schedule,
                    'args': args,
                    'kwargs': kwargs,
                    'options': options
                }

                # save in scheduled registry
                if func.name not in self.__tasks__:
                    self.__tasks__[func.name] = func
                    self.__funcs__[func.__name__] = func

                return func

        # return inner decorator
        return _

    def __getattr__(self, key):
        if key not in self.__tasks__:
            if key not in self.__funcs__:
                raise AttributeError('Task {} has not been registered'.format(key))
            return self.__funcs__[key]
        return self.__tasks__[key]

    def __getitem__(self, key):
        return self.__getattr__(key)

    def init_celery(self, controller):
        """
        Initialize the task manager with a celery controller. This
        will register all decorated tasks with the specified
        ``controller`` (celery application).

        Args:
            controller (Celery): Celery application instance to
                register tasks for.
        """
        self.__app__ = controller
        for key, item in self.__registered__.items():
            self(
                schedule=item['schedule'],
                args=item['args'],
                kwargs=item['kwargs'],
                options=item['options'],
                name=key,
            )(item['func'])
        return


class CommandManager(object):
    """
    Manager for issuing celery ``inspect`` or ``control`` calls
    to the celery API.

    Example:

        .. code-block:: python

            >>> inspect = CommandManager('inspect')

            # no options
            >>> inspect.active()

            # options
            >>> inspect.active(timeout=5, destination=['w1@e.com', 'w2@e.com'])

    This tool is primarily used alongside the ``Celery`` plugin
    object, allowing developers to issue celery commands via
    property.

    Examples:

        .. code-block:: python

            >>> celery = Celery(app)

            # ``inspect`` command manager.
            >>> celery.inspect.ping()
            {'worker@localhost': {'ok': 'pong'}}

            # ``control`` command manager.
            >>> celery.control.pool_shrink(1)
            {'worker@localhost': {'ok': 'pool will shrink'}}
            >>> celery.control.shutdown()
            Shutdown signal sent to workers.

    Use ``celery.inspect.help()`` and ``celery.control.help()`` to see
    available celery commands.
    """

    def __init__(self, name):
        self.name = name
        return

    def __getattr__(self, key):
        def _(*args, **kwargs):
            return self.call(self.name + ' ' + key, *args, **kwargs)
        return _

    def __getitem__(self, key):
        return self.__getattr__(key)

    def help(self):
        """
        Return help message for specific command.
        """
        output = cli.output(self.name + ' --help', stderr=None)
        sys.stderr.write('\n>>> celery.' + self.name + '.command()\n\n')
        sys.stderr.write('Issue celery command to {} workers.\n\n'.format(self.name))
        sys.stderr.write('Commands:')
        for line in output.split('\n'):
            if line and line[0] == '|':
                sys.stderr.write(line + '\n')
        return

    def call(self, cmd, timeout=None, destination=None, quiet=False):
        """
        Issue celery subcommand and return output.

        Args:
            cmd (str): Command to call.
            timeout (float): Timeout in seconds (float) waiting for reply.
            destination (str, list): List of destination node names.
        """
        cmd += ' --json'

        # parse timeout
        if timeout is not None:
            cmd += ' --timeout={}'.format(timeout)

        # parse destination
        if destination is not None:
            if isinstance(destination, str):
                destination = destination.split(',')
            cmd += ' --destination={}'.format(','.join(destination))

        # make call accounting for forced error
        try:
            output = cli.output(cmd)
        except subprocess.CalledProcessError as err:
            if not quiet:
                if 'shutdown' in cmd:
                    print('Shutdown signal sent to workers.')
                else:
                    print(err.stdout.decode('utf-8'))
            return

        # make call and parse result
        output = output.split('\n')[0]
        try:
            data = json.loads(output)
        except json.JSONDecodeError:
            data = {}
        if isinstance(data, (list, tuple)):
            result = {}
            for item in data:
                result.update(item)
            data = result
        return data
