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
import atexit
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
        return subprocess.Popen(args, stderr=stderr, stdout=stdout, env=os.environ.copy())

    @classmethod
    def call(cls, cmd, stderr=None, stdout=None):
        """
        Run subprocess.call for executing celery command.
        """
        args = 'celery -A flask_celery.ext.celery {}'.format(cmd).split(' ')
        return subprocess.call(args, stderr=stderr, stdout=stdout, env=os.environ.copy())

    @classmethod
    def output(cls, cmd, stderr=subprocess.STDOUT):
        """
        Run subprocess.check_output for command.
        """
        args = 'celery -A flask_celery.ext.celery {}'.format(cmd).split(' ')
        return subprocess.check_output(args, stderr=stderr, env=os.environ.copy()).decode('utf-8')




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
