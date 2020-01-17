# -*- coding: utf-8 -*-
#
# Testing for application pattern setup differences.
#
# ------------------------------------------------


# imports
# -------
import os
import requests
import subprocess
import pytest
import signal

from ..fixtures import timeout


# fixtures
# --------
@pytest.fixture(scope='session')
def app(sandbox):
    # start application
    proc = subprocess.Popen(
        'FLASK_ENV=development FLASK_APP=tests.resources.factory '
        'flask run --host=127.0.0.1 --port=5000',
        stderr=subprocess.STDOUT, stdout=subprocess.PIPE, shell=True
    )

    # wait for server to start
    with timeout(10) as to:
        while True:
            try:
                response = requests.get('http://127.0.0.1:5000')
                assert response.json() == {'status': 'ok'}
                break
            except requests.exceptions.ConnectionError:
                pass
            assert not to.expired, 'Flask application did not start - check for port collisions.'

    yield

    # stop cluster process (can't just use proc.terminate()
    # because of the forking process)
    os.killpg(os.getpgid(proc.pid), signal.SIGINT)
    return


# tests
# -----
def test_pattern(app):
    # ping
    response = requests.get('http://127.0.0.1:5000/ping')
    assert response.json() == {'msg': 'pong'}

    # task
    response = requests.get('http://127.0.0.1:5000/task')
    assert response.json() == {'success': True}

    # wait for flower availability
    with timeout(10) as to:
        while True:
            try:
                response = requests.get('http://127.0.0.1:5555/api/workers')
                assert True
                break
            except requests.exceptions.ConnectionError:
                pass
            assert not to.expired, 'Could not access flower.'
    return
