
Usage
=====

The sections below detail how to fully use this module, along with context for design decisions made during development of the plugin.


Task Execution
--------------

Submitting Task to Workers
++++++++++++++++++++++++++

ADD OVERVIEW

.. code-block:: python

    def add(x, y):
      return x + y

    celery.submit(add, 1, 2)
    celery.submit(add, 1, y=2)
    celery.submit(add, x=1, y=2)


The result of ``celery.submit`` will return a ``Future`` object that can be used to query the status of the task


Database Operations
+++++++++++++++++++

TALK ABOUT WRITING THREAD-SAFE CODE


Working with Futures
++++++++++++++++++++

The return value for submitting a task is a ``Future`` object, which wraps the ``celery.AsyncResult`` object with an API similar to the ``concurrent.futures`` `Future <https://docs.python.org/3/library/concurrent.futures.html#concurrent.futures.Future>`_ API. With this object you can do the following:

.. code-block:: python

    # submitting future
    future = celery.submit(add, 1, 2)

    # cancel task
    future.cancel()

    # check if task has been cancelled
    future.cancelled() # True

    # check if task is currently running
    future.running() # True

    # check if task is finished running
    future.done()

    # wait for result (with optional timeout)
    future.result(timeout=1)

    # return exception raised during the call
    exc = future.exception()


Finally, you can also add a callback to be executed when the task finishes running.

.. code-block:: python

    def callback():
      # callback function
      return

    # submitting future
    future = celery.submit(add, 1, 2)

    # adding callback
    future.add_done_callback(callback)


This will ensure that the specified callback function is automatically executed when the task returns a ``done`` status.


Status Updates
++++++++++++++

This plugin creates a proxied ``current_task`` that allows users to access the current celery task within a function.

.. code-block:: python

  from flask_celery import current_task

  def add(a, b):
    current_task.update_state(state='PROGRESS')
    return a + b

If the function is not currently running in a task, this will return an error. To check if the ``current_task`` proxy is avaialble, you can check for it in a conditional:

.. code-block:: python

    def add(x, y):
      if current_task:
          current_task.update_state(state='PROGRESS')
      return x + y



Monitoring Tools
----------------

This extension also provides tools for monitoring the state of celery workers, along with inspecting various types of tasks that have been submitted to the worker queue.

To see a status overview of all workers registered with the application, you can use the ``status()`` method.

.. code-block:: python

    >>> celery.status()
    {
      "ping": True,
      "workers": {
        "foo@localhost": "OK",
        "bar@localhost": "OK"
      }
    }


Celery also provides different utilities for `inspecting <https://docs.celeryproject.org/en/latest/userguide/monitoring.html#management-command-line-utilities-inspect-control>`_ the state of submitted tasks and general stats about workers. These utilities are all available on the extension object once the application has been registered and workers started.

.. code-block:: python

    # inspect active tasks
    >>> celery.active()

    # inspect scheduled tasks
    >>> celery.scheduled()

    # inspect reserved tasks
    >>> celery.reserved()

    # inspect revoked tasks
    >>> celery.revoked()

    # inspect registered tasks
    >>> celery.registered()

    # inspect worker stats
    >>> celery.stats()


Note that all of this inspection information is available via the ``Flower`` monitoring tool.


Command-Line Extensions
-----------------------

One of the more helpful features this plugin provides is automatic registration of cli entry points for managing celery.

MORE INFORMATION


``status``
++++++++++

Query the status of all celery workers and submit a simple task to celery.

.. code-block:: bash

    ~$ flask celery status


``worker``
++++++++++

Spin up local worker with specific name.

.. code-block:: bash

    ~$ flask celery worker -n worker1
    {
      "ping": true,
      "workers": {
        "foo@localhost": "OK",
        "bar@localhost": "OK",
        "baz@localhost": "OK"
      }
    }


``flower``
++++++++++

Spin up `Flower <https://flower.readthedocs.io/en/latest/>`_ monitor for dashboard analytics on celery workers.

.. code-block:: bash

    ~$ flask celery flower


``cluster``
++++++++++

Spin up all local workers referenced in configuration, along with Flower monitor.

.. code-block:: bash

    ~$ flask celery cluster



Configuration
-------------

The majority of customizations for this plugin happen via configuration, and this section covers the various types of customizations available.


Configuration Keys
++++++++++++++++++

A list of configuration keys currently understood by the extension:

.. tabularcolumns:: |p{6.5cm}|p{10cm}|

================================== =========================================
``PLUGIN_DEFAULT_VARIABLE``        A variable used in the plugin for
                                   something important.
================================== =========================================


Other Customizations
++++++++++++++++++++

As detailed in the `Overview <./overview.html>`_ section of the documentation,
the plugin can be customized with specific triggers. The following detail
what can be customized:

* ``option`` - An option for the plugin.

The code below details how you can override all of these configuration options:

.. code-block:: python

    from flask import Flask
    from flask_plugin import Plugin
    from werkzeug.exceptions import HTTPException

    app = Flask(__name__)
    plugin = Plugin(option=True)
    plugin.init_app(app)


For even more in-depth information on the module and the tools it provides, see the `API <./api.html>`_ section of the documentation.
