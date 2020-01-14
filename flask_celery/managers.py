# -*- coding: utf-8 -*-
#
# All manager objects for complex operations provided
# by plugin properties.
#
# ------------------------------------------------


# imports
# -------
import json
import subprocess

from .cli import cli


# classes
# -------
class TaskManager(object):
    """
    Object for managing registered celery tasks, providing
    users a way of submitting tasks via the celery API when
    using the factory pattern for configuring a flask application.
    """

    def __init__(self):
        self.__app__ = None
        self.__registered__ = {}
        self.__tasks__ = {}
        self.__funcs__ = {}
        return

    def __call__(self, *args, **kwargs):
        """
        Proxy for @celery.task decorator to manage two things:

        1. Registration of celery tasks with the Flask-Celery plugin,
           so the celery application can be configured using an
           application factory pattern.

        2. Reistration of celery tasks with an instantiated celery
           application instance.

        .. TODO: More documentation
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

    def init_celery(self, controller):
        self.__app__ = controller
        for key, item in self.__registered__.items():
            if not len(item['args']) and not len(item['kwargs']):
                self(item['func'])
            else:
                self(*item['args'], **item['kwargs'])(item['func'])
        return

    def __getattr__(self, key):
        if key not in self.__tasks__:
            if key not in self.__funcs__:
                raise AttributeError('Task {} has not been registered'.format(key))
            return self.__funcs__[key]
        return self.__tasks__[key]

    def __getitem__(self, key):
        return self.__getattr__(key)


class CommandManager(object):

    def __init__(self, name):
        self.name = name
        return

    def __getattr__(self, key):
        def _(*args, **kwargs):
            return self.call(self.name + ' ' + key, *args, **kwargs)
        return _

    def call(self, cmd, timeout=None, destination=None, quiet=False):
        """
        Call celery subcommand and return output.

        Example:

            >>> inspect = CommandManager('inspect')

            # no options
            >>> inspect.active()

            # options
            >>> inspect.active(timeout=5, destination=['w1@e.com', 'w2@e.com'])

        This tool is primarily used alongside the ``Celery`` plugin
        object, allowing developers to issue celery commands via
        property.

        Example:

            >>> celery = Celery(app)
            >>> celery.inspect.active()
            >>> celery.control.shutdown()

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
                print(err.stdout.decode('utf-8'))
            return

        # make call and parse result
        data = json.loads(output)
        if isinstance(data, (list, tuple)):
            result = {}
            for item in data:
                result.update(item)
            data = result
        return data
