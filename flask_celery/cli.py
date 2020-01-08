# -*- coding: utf-8 -*-
#
# Plugin Setup
#
# ------------------------------------------------


# imports
# -------
import time
import json
import click
import subprocess
from flask import current_app
from flask.cli import AppGroup


# config
# ------
entrypoint = AppGroup('celery')


# helpers
# -------
class cli:
    """
    Data structure for wrapping celery internal celery commands
    executed throughout the plugin.
    """

    @classmethod
    def popen(cls, cmd, stderr=subprocess.STDOUT, stdout=None):
        """
        Run subprocess.popen for executing celery command in background.
        """
        return subprocess.Popen(
            'exec celery -A flask_celery.ext.celery {}'.format(cmd),
            stderr=stderr, stdout=stdout, shell=True
        )

    @classmethod
    def call(cls, cmd, stderr=subprocess.STDOUT, stdout=None):
        """
        Run subprocess.call for executing celery command.
        """
        return subprocess.call(
            'exec celery -A flask_celery.ext.celery {}'.format(cmd),
            stderr=stderr, stdout=stdout, shell=True
        )

    @classmethod
    def output(cls, cmd, stderr=subprocess.STDOUT):
        """
        Run subprocess.check_output for command.
        """
        return subprocess.check_output(
            'celery -A flask_celery.ext.celery {}'.format(cmd),
            stderr=stderr, shell=True
        ).decode('utf-8')


# entry points
# ------------

# TODO: CONSIDER EXTENDING ALL ENTRY POINTS FROM CELERY VIA FLASK

@entrypoint.command('worker', context_settings=dict(
    ignore_unknown_options=True,
))
@click.argument('args', nargs=-1, type=click.UNPROCESSED)
def worker(args):
    """
    Start single celery worker from configuration.
    """
    # TODO: parse args for worker names and consolidate with
    #       configuration
    from flask import current_app
    return cli.call(
        "worker --loglevel={} {}".format(
            current_app.config['CELERY_LOG_LEVEL'], ' '.join(args)
        )
    )


@entrypoint.command('cluster')
def cluster():
    """
    Start local cluster of celery workers and flower
    monitoring tool (if specified).
    """
    celery = current_app.extensions['celery']
    celery.start()
    if current_app.config['CELERY_FLOWER']:
        flower = cli.popen(
            '--address={} --port={}'.format(
                current_app.config['CELERY_FLOWER_ADDRESS'],
                current_app.config['CELERY_FLOWER_PORT'],
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


@entrypoint.command('status')
def status():
    """
    Check statuses of celery workers.
    """
    result = {'ping': False, 'workers': {}}
    celery = current_app.extensions['celery']
    workers = celery.status()
    if len(workers):
        result['workers'] = workers
        result['ping'] = celery.ping()
    print(json.dumps(result, indent=2))
    return result
