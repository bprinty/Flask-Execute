
Overview
========

Flask-Celery is a plugin aimed at simplifying the process of configuring Celery alongside a Flask application. It also slightly changes the paradigm for registering and dispatching celery tasks, exposing an API similar to the ``concurrent.futures`` API for submitting tasks to a separate executor.

Other features of the plugin include:

* Automatic spin-up of local workers via configuration.
* Automatic application context wrapping for celery workers.
* Simpler API for submitting tasks to workers.
* Result object API similar to ``concurrent.futures.Future`` API.
* Flask CLI commands for status checking, spinning up workers, worker cluster, and `flower <https://flower.readthedocs.io/en/latest/>`_ monitor.

The Flask `documentation <https://flask.palletsprojects.com/en/1.1.x/patterns/celery/>`_ details how to configure Celery with Flask without this plugin, and readers are encouraged to check out that documentation before working with this plugin.


A Minimal Application
---------------------

To set up an application with the extension, you can register the application directly:

.. code-block:: python

    from flask import Flask
    from flask_celery import Celery

    app = Flask(__name__)
    app.config.from_object(Config)
    plugin = Celery(app)


Or, via factory pattern:

.. code-block:: python

    celery = Celery()
    app = Flask(__name__)
    app.config.from_object(Config)
    celery.init_app(app)


Once the plugin has been registered, you can submit a task using:

.. code-block:: python

    def add(x, y):
      return x + y

    future = celery.submit(add, 1, 2)

    # wait for result (not required)
    future.result(timeout=1)


Note that this plugin does not require users to pre-register tasks via the ``@celery.task`` decorator. This enables developers to more easily control whether or not task execution happens within the current session or on a separate worker. It also makes the API similar to the API provided by `Dask <https://docs.dask.org/en/latest/>`_ and `concurrent.futures <https://docs.python.org/3/library/concurrent.futures.html>`_.

Another thing to note is that there is no need to create a ``ContextTask`` wrapper for celery with this module. All celery processes are automatically wrapped with a fresh application context, and the current task can be accessed via the ``current_task`` proxy.

This plugin can also be configured to manage the process of starting local workers the first time a task is submitted. If you want to run workers locally, you can have the application spin up workers via the  ``CELERY_START_LOCAL_WORKERS=True`` configuration option. This is particularly useful during development, where developers no longer need to manually spin up celery workers to run the application in development mode.

For more in-depth discussion on design considerations and how to fully utilize the plugin, see the `User Guide <./usage.html>`_.
