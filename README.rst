

|Build status| |Code coverage| |Maintenance yes| |GitHub license| |Documentation Status|

.. |Build status| image:: https://travis-ci.com/bprinty/Flask-Execute.png?branch=master
   :target: https://travis-ci.com/bprinty/Flask-Execute

.. |Code coverage| image:: https://codecov.io/gh/bprinty/Flask-Execute/branch/master/graph/badge.svg
   :target: https://codecov.io/gh/bprinty/Flask-Execute

.. |Maintenance yes| image:: https://img.shields.io/badge/Maintained%3F-yes-green.svg
   :target: https://GitHub.com/Naereen/StrapDown.js/graphs/commit-activity

.. |GitHub license| image:: https://img.shields.io/github/license/Naereen/StrapDown.js.svg
   :target: https://github.com/bprinty/Flask-Execute/blob/master/LICENSE

.. |Documentation Status| image:: https://readthedocs.org/projects/Flask-Execute/badge/?version=latest
   :target: http://Flask-Execute.readthedocs.io/?badge=latest


============================
Flask-Execute
============================

Flask-Execute is a plugin for simplifying the configuration and management of Celery alongside a Flask application. It also slightly changes the paradigm for registering and dispatching celery tasks, exposing an API similar to the ``concurrent.futures`` API for submitting tasks to a separate executor.

Other features of the plugin include:

* Automatic spin-up of local workers, queues, schedulers, and monitoring tools via configuration.
* Automatic application context wrapping for celery workers.
* Simpler API for submitting tasks to workers that doesn't require pre-registration of tasks.
* Result object API similar to ``concurrent.futures.Future`` API.
* Flask CLI wrapper around the ``celery`` command that automatically wraps celery commands with an application context.


Installation
============

To install the latest stable release via pip, run:

.. code-block:: bash

    $ pip install Flask-Execute


Alternatively with easy_install, run:

.. code-block:: bash

    $ easy_install Flask-Execute


To install the bleeding-edge version of the project (not recommended):

.. code-block:: bash

    $ git clone http://github.com/bprinty/Flask-Execute.git
    $ cd Flask-Execute
    $ python setup.py install


Usage
=====

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


For more in-depth discussion on design considerations and how to fully utilize the plugin, see the `User Guide <https://Flask-Execute.readthedocs.io/en/latest/usage.html>`_.


Documentation
=============

For more detailed documentation, see the `Docs <https://Flask-Execute.readthedocs.io/en/latest/>`_.


Questions/Feedback
==================

File an issue in the `GitHub issue tracker <https://github.com/bprinty/Flask-Execute/issues>`_.
