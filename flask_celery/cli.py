# -*- coding: utf-8 -*-
#
# Plugin Setup
#
# ------------------------------------------------


# imports
# -------
import os
import sys
import json
import click
import subprocess
from flask import current_app
from flask.cli import with_appcontext


# helpers
# -------
class cli:
    """
    Data structure for wrapping celery internal celery commands
    executed throughout the plugin.
    """

    @classmethod
    def popen(cls, cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE):
        """
        Run subprocess.popen for executing celery command in background.
        """
        args = 'celery -A flask_celery.ext.celery {}'.format(cmd).split(' ')
        return subprocess.Popen(args, stderr=stderr, stdout=stdout)

    @classmethod
    def call(cls, cmd, stderr=None, stdout=None):
        """
        Run subprocess.call for executing celery command.
        """
        args = 'celery -A flask_celery.ext.celery {}'.format(cmd).split(' ')
        return subprocess.call(args, stderr=stderr, stdout=stdout)

    @classmethod
    def output(cls, cmd, stderr=subprocess.STDOUT):
        """
        Run subprocess.check_output for command.
        """
        args = 'celery -A flask_celery.ext.celery {}'.format(cmd).split(' ')
        return subprocess.check_output(args, stderr=stderr).decode('utf-8')


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


# entry points
# ------------
@click.command('celery', context_settings=dict(
    ignore_unknown_options=True,
))
@click.option('-h', '--help', is_flag=True, help='Returns celery cli help.')
@click.argument('args', nargs=-1, type=click.UNPROCESSED)
@with_appcontext
def entrypoint(help, args):
    """
    Run celery command, wrapping application context and references.

    Examples:

    .. code-block:: python

        # start local worker
        ~$ flask celery worker

        # start flower monitoring tool
        ~$ flask celery flower

        # inspect worker stats
        ~$ flask celery inspect stats

    For more information on the commands available, see the celery
    documentation. You can also use ``-h`` to see the celery cli documentation:

    .. code-block:: python

        ~$ flask celery -h

    Along with celery commands, this CLI method also adds the
    ``cluster`` entrypoint for starting all workers associated
    with an application, alongside the ``flower`` monitoring tool.

    Example:

        # start workers (writing to worker logs), and flower (stream output)
        ~$ flask celery cluster

        # start workers, flower, and stream output from all (-f)
        ~$ flask celery cluster --foreground

        # start workers and stream output to foreground (no flower)
        ~$ flask celery cluster --foreground --no-flower

    To change the nubmer of workers bootstrapped by this command,
    see the ``CELERY_WORKERS`` configuration option with this plugin.
    """
    # add config options
    if 'worker' in args:
        args = list(args)
        args.append('--loglevel={}'.format(current_app.config['CELERY_LOG_LEVEL']))

    # dispatch additional entry point
    if 'cluster' in args:
        # TODO: print out help args if -h
        return cluster(args)

    # call command with arguments
    help = ' --help' if help else ''
    return cli.call(' '.join(args) + help)


def cluster(args):
    """
    Start local cluster of celery workers and flower
    monitoring tool (if specified).

    This is an internal function used alongside the proxy
    for issuing celery commands. It shouldn't be directly
    used by developers outside this plugin.

    Args:
        args (list): celery command arguments.
    """
    celery = current_app.extensions['celery']

    # starting configured celery workers
    celery.start()

    # starting flower monitor (if specified)
    if '-n' not in args and '--no-flower' not in args and \
       current_app.config['CELERY_FLOWER']:
        # make sure log dir is specified
        if not os.path.exists(current_app.config['CELERY_LOG_DIR']):
            os.makedirs(current_app.config['CELERY_LOG_DIR'])

        # start flower
        proc = cli.popen(
            'flower --address={} --port={} --logging={} --log-file-prefix={}'.format(
                current_app.config['CELERY_FLOWER_ADDRESS'],
                current_app.config['CELERY_FLOWER_PORT'],
                current_app.config['CELERY_LOG_LEVEL'],
                os.path.join(current_app.config['CELERY_LOG_DIR'], 'flower.log')
            )
        )

        # monitor logs and process
        celery.logs.append(os.path.join(current_app.config['CELERY_LOG_DIR'], 'flower.log'))
        celery.processes['flower'] = proc

    # check available processes
    if not len(celery.logs):
        sys.stderr.write('\nCelery cluster could not be started - workers already running or error starting workers. See worker logs for details\n')
        return

    # tail logs
    proc = subprocess.Popen(['tail', '-F'] + celery.logs, stdout=subprocess.PIPE)
    celery.processes['tail'] = proc
    while True:
        for line in iter(proc.stdout.readline, b''):
            sys.stderr.write(line.decode('utf-8'))
    return
