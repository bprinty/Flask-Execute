
Usage
=====

The sections below detail how to fully use this module, along with context for design decisions made during development of the plugin.


Why is this Necessary?
----------------------

If you've configured Flask to use Celery before, you're likely wondering why this extension is necessary. The truth is that this package is not necessary - you can still configure your application to use celery directly according to the Flask documentation. This package is functionally a wrapper around that paradigm that consolidates the API with other execution tools and makes celery configuration more declarative (i.e. via application config instead of code).


Task Execution
--------------

Submitting Task to Workers
++++++++++++++++++++++++++

There are a couple of divergences this extension introduces against the historical Flask/Celery setup. First, developers aren't required to pre-register tasks to submit them to celery workers. With this extension, you just need to call ``celery.submit`` to send an arbitrary function (with arguments) to a worker for external execution:

.. code-block:: python

    def add(x, y):
      return x + y

    celery.submit(add, 1, 2)
    celery.submit(add, 1, y=2)
    celery.submit(add, x=1, y=2)


The result of ``celery.submit`` will return a ``Future`` object that can be used to query the status of the task:

.. code-block:: python

    >>> future = celery.submit(add, 1, 2)
    >>> future.running()
    True
    >>> future.done()
    False
    >>> future.result(timeout=1) # wait for result
    3

For more information on this ``Future`` object, see the `Working with Futures`_ section of the documentation.

Just like with other executor tools, this extension also provides a built-in ``map`` operator for submitting an iterable object to remote workers:

.. code-block:: python

    >>> futures = celery.map(add, iter([[1, 2], [3, 4], [5, 6]]))
    >>> for future in futures:
    >>>     print(future.result(timeout=1))
    3
    7
    11

If you like the declarative syntax celery uses to register tasks, you can still do so via:

.. code-block:: python

    @celery.task
    def add(x, y):
      return x + y

    add.delay(1, 2)

This declarative mechanism for registering tasks is particularly useful for scheduling tasks to run periodically via Celery's ``cron`` tool.


Database Operations
+++++++++++++++++++

As with any program that doesn't





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

Another divergence from the historical Celery API is how ``Task`` objects are referenced in code. This extension takes a more Flask-y approach to accessing said information, where a proxied object called ``current_task`` is available for developers to reference throughout their application. This paradigm is similar to the ``current_app`` or ``current_user`` object commonly referenced in flask applications. For example, to reference the current task and update the state metadata:

.. code-block:: python

  from flask_celery import current_task

  def add(a, b):
    current_task.update_state(state='PROGRESS')
    return a + b

More information about the ``update_state`` method or ``Task`` objects can be found in the Celery `documentation <https://docs.celeryproject.org/en/latest/userguide/tasks.html>`_.


.. If the function is not currently running in a task, this will return an error because the proxy object will be ``None``. To check if the ``current_task`` proxy is available (i.e. the function won't always be run in a task), you can check for it in a conditional:
..
.. .. code-block:: python
..
..     def add(x, y):
..       if current_task:
..           current_task.update_state(state='PROGRESS')
..       return x + y


Celery Configuration
--------------------

Starting Celery
+++++++++++++++

As mentioned in the overview of the documentation, this extension can manage the process of starting celery workers the first time a ``celery.submit()`` call is made. It will also pass all celery configuration specified in your application config to Celery. Accordingly, this means you **do not have to manually start workers** if all of your workers are to run locally. An example **development** and **testing** config are shown here:

.. code-block:: python

    # start workers on first submit call
    class DevConfig:
        ENV = 'development'
        CELERY_START_LOCAL_WORKERS = True


    # don't start local workers - run in eager mode
    class TestConfig:
        ENV = 'testing'
        CELERY_ALWAYS_EAGER = True


Alternatively, you can still start celery workers manually for your application and reference them via config (recommended for production). Instead of invoking celery directly and specifying the path to the application, you should either use the built-in CLI ``flask celery cluster`` or ``flask celery worker`` methods:

.. code-block:: bash

    # start all specified workers for config along with Flower celery monitor
    ~$ flask celery cluster

    # start single worker
    ~$ flask celery worker

    # start single named worker
    ~$ flask celery worker -n foo


If you really want to invoke celery directly, you must pass

 .. code-block:: bash

    # start worker with celery
    ~$ celery -A flask_celery.celery worker --loglevel=info

This will automatically detect the flask application celery needs to work with using the auto-detection functionality provided by Flask.

If you're using a factory pattern (i.e. with a ``create_app`` function) to create the app, you can reference the application factory at the command-line via environment variable (similar to Flask CLI methods):

.. code-block:: bash

    # recommended
    ~$ FLASK_APP="app:create_app" flask celery worker

    # using celery directly
    ~$  FLASK_APP="app:create_app" celery -A flask_celery.celery worker --loglevel=info



Workers
+++++++

With this extension, you also have control over worker configuration used to start celery


the names of workers and other celery options that can be passed to workers on setup. For example, to configure your application to use a specific number of workers or specific worker names, use:

.. code-block:: python

    >>> # number of workers, no name preference
    >>> class Config:
    >>>     CELERY_WORKERS = 2

    >>> # named workers
    >>> class Config:
    >>>     CELERY_WORKERS = ['foo', 'bar']

    >>> app.config.from_object(Config)
    >>> celery.init_app(app)
    >>> celery.start()
    >>> celery.status()
    {
      "ping": True,
      "workers": {
        "foo@localhost": "OK",
        "bar@localhost": "OK"
      }
    }


For more advanced worker configuration, you can make the config option a dictionary with worker names and nested specific configuration options to be passed into celery when creating workers:

.. code-block:: python

    class Config:
        CELERY_ROUTES = {
            'core.tasks.too_long_task': {'queue': 'too_long_queue'},
            'core.tasks.quick_task': {'queue': 'quick_queue'},
        }
        CELERY_WORKERS = {
          'foo': {
            'concurrency': 10,
            'log-level': 'error',
            'pidfile': '/var/run/celery/%n.pid',
            'queues': ['low-priority', 'high-priority']
          },
          'bar': {
            'concurrency': 5,
            'log-level': 'info',
            'queues': ['high-priority']
          }
        }

For more information on the parameters available for configuring celery workers, see the Celery `documentation <https://docs.celeryproject.org/en/latest/userguide/workers.html>`_.


Queues
++++++

As alluded to above, you can configure workers to use specific queues.

TODO THIS


To manage multiple queues with this extension ....

.. code-block:: python

    class Config:
      CELERY_QUEUES = ['low-priority', 'high-priority']


To submit a task to a specific queue, use the following syntax with ``submit()``:

.. code-block:: python

    >>> celery.submit(add, 1, 2, queue='high-priority')

If using the queues mechanism provided by this extension, the ``queue`` keyword will be reserved on function calls. Accordingly, developers should be careful not to use that argument for functions that can be submitted to an executor.


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
