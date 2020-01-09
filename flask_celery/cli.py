# -*- coding: utf-8 -*-
#
# Plugin Setup
#
# ------------------------------------------------


# imports
# -------
import sys
import json
import click
import logging
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

    def call(self, cmd, timeout=None, destination=None):
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

        # make call and parse result
        output = cli.output(cmd)
        return json.loads(output)


# entry points
# ------------
@click.command('celery', context_settings=dict(
    ignore_unknown_options=True,
))
@click.argument('args', nargs=-1, type=click.UNPROCESSED)
@with_appcontext
def entrypoint(args):
    """
    Run celery command, wrapping application context and references.

    Example:

        # start local worker
        ~$ flask celery worker

        # start flower monitoring tool
        ~$ flask celery flower

        # inspect worker stats
        ~$ flask celery inspect stats

    For more information on the commands available, see the celery
    documentation.

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
    if not len(args):
        return cli.call('-h')

    # add config options
    if 'worker' in args:
        args = list(args)
        args.append('--loglevel={}'.format(current_app.config['CELERY_LOG_LEVEL']))

    if 'cluster' in args:
        return cluster(args)

    # parse subcommand
    return cli.call(' '.join(args))


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
    foreground = '-f' in args or '--foreground' in args
    procs = []

    # starting configured celery workers
    celery.start(log=not foreground)

    # starting flower monitor (if specified)
    if '-n' not in args and '--no-flower' not in args and \
       current_app.config['CELERY_FLOWER']:
        proc = cli.popen(
            'flower --address={} --port={}'.format(
                current_app.config['CELERY_FLOWER_ADDRESS'],
                current_app.config['CELERY_FLOWER_PORT'],
            )
        )
        celery.processes['flower'] = proc

    # wait for termination signal
    while True:
        for key in celery.processes:
            proc = celery.processes[key]
            for line in iter(proc.stderr.readline, b''):
                sys.stderr.write(line.decode('utf-8'))
    return
