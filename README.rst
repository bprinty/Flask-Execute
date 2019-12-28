
.. Uncomment below for banners

.. |Build status| |Code coverage| |Maintenance yes| |GitHub license| |Documentation Status|

.. .. |Build status| image:: https://travis-ci.com/bprinty/Flask-Celery.png?branch=master
..    :target: https://travis-ci.com/bprinty/Flask-Celery

.. .. |Code coverage| image:: https://codecov.io/gh/bprinty/Flask-Celery/branch/master/graph/badge.svg
..    :target: https://codecov.io/gh/bprinty/Flask-Celery

.. .. |Maintenance yes| image:: https://img.shields.io/badge/Maintained%3F-yes-green.svg
..    :target: https://GitHub.com/Naereen/StrapDown.js/graphs/commit-activity

.. .. |GitHub license| image:: https://img.shields.io/github/license/Naereen/StrapDown.js.svg
..    :target: https://github.com/bprinty/Flask-Celery/blob/master/LICENSE

.. .. |Documentation Status| image:: https://readthedocs.org/projects/Flask-Celery/badge/?version=latest
..    :target: http://Flask-Celery.readthedocs.io/?badge=latest


============================
Flask-Celery
============================

Flask-Celery is a plugin for simplifying the configuration and management of celery integrations.

MORE LATER


Installation
============

To install the latest stable release via pip, run:

.. code-block:: bash

    $ pip install Flask-Celery


Alternatively with easy_install, run:

.. code-block:: bash

    $ easy_install Flask-Celery


To install the bleeding-edge version of the project (not recommended):

.. code-block:: bash

    $ git clone http://github.com/bprinty/Flask-Celery.git
    $ cd Flask-Celery
    $ python setup.py install


Usage
=====

Below is a minimal application configured to take advantage of some of the extension's core features:

.. code-block:: python

    from flask import Flask
    from flask_celery import Celery

    app = Flask(__name__)
    app.config.from_object(Config)
    plugin = Celery(app)


The following is a minimal application highlighting most of the major features provided by the extension:

.. code-block:: python

    INSERT CODE


Documentation
=============

For more detailed documentation, see the `Docs <https://Flask-Celery.readthedocs.io/en/latest/>`_.


Questions/Feedback
==================

File an issue in the `GitHub issue tracker <https://github.com/bprinty/Flask-Celery/issues>`_.
