# -*- coding: utf-8 -*-
#
# Pytest configuration
#
# ------------------------------------------------


# imports
# -------
import os
import pytest
import logging

from .fixtures import db, create_app


# config
# ------
SETTINGS = dict(
    teardown=True,
    echo=False,
)
APP = None
CLIENT = None
logging.basicConfig(level=logging.ERROR)


# plugins
# -------
def pytest_addoption(parser):
    parser.addoption("-N", "--no-teardown", default=False, help="Do not tear down sandbox directory after testing session.")
    parser.addoption("-E", "--echo", default=False, help="Be verbose in query logging.")
    return


def pytest_configure(config):
    global TEARDOWN
    SETTINGS['teardown'] = not config.getoption('-N')
    SETTINGS['echo'] = config.getoption('-E')
    return


@pytest.fixture(autouse=True, scope='session')
def sandbox(request):
    from . import SANDBOX
    global SETTINGS, APP, CLIENT

    # create sandbox for testing
    if not os.path.exists(SANDBOX):
        os.makedirs(SANDBOX)

    yield

    # teardown sandbox
    if SETTINGS['teardown']:
        import shutil
        shutil.rmtree(SANDBOX)
    return


@pytest.fixture(scope='session')
def server(sandbox):
    import requests
    from . import SANDBOX
    global SETTINGS, APP, CLIENT

    # create application
    app = create_app('development')

    # create default user
    with app.app_context():
        db.drop_all()
        db.create_all()

    proc = subprocess.popen('FLASK_ENV=development FLASK_APP=tests.conftest::create_app exec flask run')
    client = requests.Session()

    yield client
    return


@pytest.fixture(scope='session')
def application(sandbox):
    from . import SANDBOX
    global SETTINGS, APP, CLIENT

    # create application
    app = create_app('testing')
    if SETTINGS['echo']:
        app.config['SQLALCHEMY_ECHO'] = True

    # create default user
    with app.app_context():
        db.drop_all()
        db.create_all()
        yield app
    return


@pytest.fixture(scope='session')
def client(application):
    global CLIENT
    if CLIENT is not None:
        yield CLIENT
    else:
        with application.test_client() as CLIENT:
            yield CLIENT
    return


@pytest.fixture(scope='session')
def celery(application, client):
    yield application.extensions['celery']
    return
