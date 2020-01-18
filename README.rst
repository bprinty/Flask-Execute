
.. Uncomment below for banners

.. |Build status| |Code coverage| |Maintenance yes| |GitHub license| |Documentation Status|

.. .. |Build status| image:: https://travis-ci.com/bprinty/Flask-CeleryStick.png?branch=master
..    :target: https://travis-ci.com/bprinty/Flask-CeleryStick

.. .. |Code coverage| image:: https://codecov.io/gh/bprinty/Flask-CeleryStick/branch/master/graph/badge.svg
..    :target: https://codecov.io/gh/bprinty/Flask-CeleryStick

.. .. |Maintenance yes| image:: https://img.shields.io/badge/Maintained%3F-yes-green.svg
..    :target: https://GitHub.com/Naereen/StrapDown.js/graphs/commit-activity

.. .. |GitHub license| image:: https://img.shields.io/github/license/Naereen/StrapDown.js.svg
..    :target: https://github.com/bprinty/Flask-CeleryStick/blob/master/LICENSE

.. .. |Documentation Status| image:: https://readthedocs.org/projects/Flask-CeleryStick/badge/?version=latest
..    :target: http://Flask-CeleryStick.readthedocs.io/?badge=latest


============================
Flask-CeleryStick
============================

Flask-CeleryStick is a plugin for simplifying the configuration and management of celery integrations.

MORE LATER


Installation
============

To install the latest stable release via pip, run:

.. code-block:: bash

    $ pip install Flask-CeleryStick


Alternatively with easy_install, run:

.. code-block:: bash

    $ easy_install Flask-CeleryStick


To install the bleeding-edge version of the project (not recommended):

.. code-block:: bash

    $ git clone http://github.com/bprinty/Flask-CeleryStick.git
    $ cd Flask-CeleryStick
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

For more detailed documentation, see the `Docs <https://Flask-CeleryStick.readthedocs.io/en/latest/>`_.


Questions/Feedback
==================

File an issue in the `GitHub issue tracker <https://github.com/bprinty/Flask-CeleryStick/issues>`_.
