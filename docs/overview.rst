
Overview
========

Flask-Execute is a plugin for simplifying the configuration and management of Celery alongside a Flask application. It also slightly changes the paradigm for registering and dispatching celery tasks, exposing an API similar to the ``concurrent.futures`` API for submitting tasks to a separate executor.

Other features of the plugin include:

* Automatic spin-up of local workers, queues, schedulers, and monitoring tools via configuration.
* Automatic application context wrapping for celery workers.
* Simpler API for submitting tasks to workers that doesn't require pre-registration of tasks.
* Result object API similar to ``concurrent.futures.Future`` API.
* Flask CLI wrapper around the ``celery`` command that automatically wraps celery commands with an application context.

The Flask `documentation <https://flask.palletsprojects.com/en/1.1.x/patterns/celery/>`_ details how to configure Celery with Flask without this plugin, and readers are encouraged to check out that documentation before working with this plugin.

.. Other alternatives to consider when choosing an execution engine for your app are:
..
..   * `Flask-Dask <https://flask-dask.readthedocs.io/en/latest/>`_
..   * `Flask-Executor <https://flask-executor.readthedocs.io/en/latest/>`_


A Minimal Application
---------------------

To set up an application with the extension, you can register the application directly:

.. code-block:: python

    from flask import Flask
    from flask_execute import Celery

    app = Flask(__name__)
    plugin = Celery(app)


Or, via factory pattern:

.. code-block:: python

    celery = Celery()
    app = Flask(__name__)
    celery.init_app(app)


Once the plugin has been registered, you can submit a task using:

.. code-block:: python

    def add(x, y):
      return x + y

    future = celery.submit(add, 1, 2)

    # wait for result (not required)
    future.result(timeout=1)

    # cancel result
    future.cancel()

    # add callback function
    def callback():
      # do something ...
      return

    future.add_done_callback(callback)


Note that this plugin does not require users to pre-register tasks via the ``@celery.task`` decorator. This enables developers to more easily control whether or not task execution happens within the current session or on a separate worker. It also makes the API similar to the API provided by `Dask <https://docs.dask.org/en/latest/>`_ and `concurrent.futures <https://docs.python.org/3/library/concurrent.futures.html>`_. Also note that the ``celery`` command-line tool for spinning up local workers is no longer necessary. If no workers are connected, this plugin will automatically spin them up the first time a ``celery.submit()`` call is made.

Once a task as been submitted, you can monitor the state via:

.. code-block:: python

    task_id = future.id

    # later in code

    future = celery.get(task_id)
    print(future.state)


You can also manage state updates within tasks with a more Flask-y syntax:

.. code-block:: python

  from flask_execute import current_task

  def add(a, b):
    current_task.update_state(state='PROGRESS')
    return a + b


This plugin will also manage the process of spinning up local workers bound to your application the first time a ``celery.submit()`` call is made (if configured to do so). Additionally, the plugin will automatically wrap ``celery`` cli calls with your flask application (using the factory method or not), so you can more easily interact with celery:

.. code-block:: bash

    # start local celery cluster with workers, flower monitor, and celerybeat scheduler
    ~$ flask celery cluster

    # start local worker
    ~$ flask celery worker

    # check status of running workers
    ~$ flask celery status

    # shutdown all celery workers
    ~$ flask celery control shutdown

    # shutdown all celery workers
    ~$ flask celery control shutdown


If your application uses the factory pattern with a ``create_app`` function for registering blueprints and plugin, you can use the standard ``flask cli`` syntax for automatically wrapping ``celery`` commands with your application context:

.. code-block:: bash

    # check status of running workers
    ~$ FLASK_APP=app:create_app flask celery status


For more in-depth discussion on design considerations and how to fully utilize the plugin, see the `User Guide <./usage.html>`_.
