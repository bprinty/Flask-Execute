
.. _Celery documentation: https://docs.celeryproject.org/en/latest/userguide/
.. _Celery Setup documentation: https://docs.celeryproject.org/en/latest/getting-started/first-steps-with-celery.html
.. _Celery Result documentation: https://docs.celeryproject.org/en/latest/reference/celery.result.html
.. _Celery Task documentation: https://docs.celeryproject.org/en/latest/userguide/tasks.html
.. _Celery Worker documentation: https://docs.celeryproject.org/en/latest/userguide/workers.html
.. _Celery Periodic Tasks documentation: https://docs.celeryproject.org/en/latest/userguide/periodic-tasks.html
.. _Celery Config documentation: https://docs.celeryproject.org/en/latest/userguide/configuration.html


Usage
=====

The sections below detail how to fully use this module, along with context for design decisions made during development of the plugin.


Why is this Necessary?
----------------------

If you've configured Flask to use Celery before, you may have run into the motivating factor behind the creation of this package - it's not particularly straightforward to either 1) connect celery workers to a flask instance, 2) wrap celery workers in a flask application context, 3) use the application factory pattern alongside a celery configuration, or 4) manage starting workers in development mode. Like other Flask extensions, configuration for an external tool should be as simple as instantiating the extension and registering the Flask application:

.. code-block:: python

    app = Flask()
    celery = Celery(app)


This package is functionally a wrapper around the process of configuring celery that resolves the annoyances listed above and adds the following additional functionality:

1. Removes the need to manually start local celery workers and configure celery ``Tasks`` with separate application contexts.
2. Provides simpler worker and queue configuration (related to 1).
3. Provides ``flask`` command-line extensions for configuring celery with the application context.
4. Homogenizes the API for interacting with tasks with other execution tools like ``concurrent.futures`` and ``Dask``.
5. Allows developers to dynamically submit tasks to Celery, instead of developers needing to pre-register tasks to run on workers.

The features listed above simplify the process of configuring Celery to work with Flask and make working with Celery a more enjoyable experience. If you don't agree with those sentiments or like the way Celery historically has been configured with Flask applications, feel free to ignore the rest of this documentation. This extension isn't necessary for configuring your application to use celery, just like ``Flask-SQLAlchemy`` isn't necessary for configuring your application to use ``SQLAlchemy``.


Prerequisites
-------------

Just like celery, this package requires a message broker as a prerequisite. For information on how to install and set up the various celery message brokers, see the `Celery Setup documentation`_.

For those who just want to get moving quickly, here's how to install ``Redis`` on OSX:

.. code-block:: bash

    ~$ brew install redis


And on ``*nix`` systems:

.. code-block:: bash

    ~$ wget http://download.redis.io/redis-stable.tar.gz
    ~$ tar xvzf redis-stable.tar.gz
    ~$ cd redis-stable
    ~$ make

To start redis manually (most installers will configure it to start on boot), run:

.. code-block:: bash

    ~$ redis-server


Setup
-----

As mentioned in the overview section of the documentation, to configure your application to use Celery via this extension you can register it directly:

.. code-block:: python

    from flask import Flask
    from flask_execute import Celery

    app = Flask(__name__)
    plugin = Celery(app)


Or, via the application factory pattern:

.. code-block:: python

    celery = Celery()
    app = Flask(__name__)
    celery.init_app(app)


That's it! all of the other tedium around wrapping tasks in an application context, creating a ``make_celery`` function, or pre-registering tasks is no longer necessary. Additionally, you don't need to manually use the ``celery`` CLI tool to start workers if your workers are meant to run on the server the application is running. This package will automatically spin them up the first time an executable is sent to the workers. More fine-grained control over worker configuration and command-line extensions this tool provides is detailed later in the documentation.

Once this extension has been registered with the application, you can submit tasks to workers via ``celery.submit()``:

.. code-block:: python

    def add(x, y):
      return x + y

    celery.submit(add, 1, 2)

More information on task execution and other tools the ``Celery`` object provides is detailed below.


Tasks
-----

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


Just like with other executor tools, this extension also provides a built-in ``map`` operator for submitting an iterable object to remote workers:

.. code-block:: python

    # arguments
    >>> future_pool = celery.map(add, [1, 2], [3, 4], [5, 6])
    >>> for future in future_pool:
    >>>     print(future.result(timeout=1))
    3
    7
    11

    # with constant keyword arguments
    >>> future_pool = celery.map(add, [1], [3], [5], y=2)
    >>> for future in future_pool:
    >>>     print(future.result(timeout=1))
    3
    5
    7


The return value for the ``celery.map()`` function is a ``FuturePool`` object that can serve as a proxy for querying the overall status of the submitted tasks. All API methods on the ``Future`` object are also available on the ``FuturePool`` object:

.. code-block:: python

    >>> pool = celery.map(add, [1, 2], [3, 4], [5, 6])

    # check if any tasks in the pool are still running
    >>> pool.running()
    True

    # check if all tasks in the pool are done
    >>> future.done()
    False

    # return a list with the map results
    >>> future.result(timeout=1)
    [3, 7 , 11]


For more information about the methods available on ``Future`` and ``FuturePool`` objects, see the `Working with Futures`_ section of the documentation.


Working with Futures
++++++++++++++++++++

As alluded to previously in the documentation, the return value for submitting a task is a ``Future`` object, which wraps the ``celery.AsyncResult`` object with an API similar to the ``concurrent.futures`` `Future <https://docs.python.org/3/library/concurrent.futures.html#concurrent.futures.Future>`_ API. With this object you can do the following:

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

    # raise exception returned by future
    future.exception()


You can also query properties of the ``celery.AsyncResult`` object from ``Future`` objects:

.. code-block:: python

    # query status/state
    future.state
    future.status

    # query task id
    future.id

    # query task name
    future.name


For more information on available properties, see the `Celery Result documentation`_.

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

If you have the task ID (obtained via ``Future.id``), you can query a task Future via:

.. code-block:: python

    >>> future = celery.submit(add, 1, 2)
    >>> task_id = future.id

    # later in code ...

    >>> future = celery.get(task_id)
    >>> future.done()
    False


Similarly to ``Future`` objects, ``FuturePool`` objects are a wrapper around the ``GroupResult`` object available from celery. Accordingly, the ``FuturePool`` object has a very similar API:

.. code-block:: python

    # submitting future
    pool = celery.map(add, [1, 2], [3, 4], [5, 6])

    # cancel *all* tasks in the pool
    pool.cancel()

    # check if *any* task in the pool has been cancelled
    pool.cancelled() # True

    # check if *any task in the pool is currently running
    pool.running() # True

    # check if *all* tasks in the pool are finished running
    pool.done()

    # wait for *all* task results (with optional timeout)
    pool.result(timeout=1)

    # raise *any* exception returned by the pool
    pool.exception()


Task Registration
+++++++++++++++++

If you like the declarative syntax celery uses to register tasks, you can still do so via:

.. code-block:: python

    app = Flask(__name__)
    celery = Celery(app)

    @celery.task
    def add(x, y):
      return x + y

    add.delay(1, 2)

However, using the ``delay`` method on the registered task will only work if the application was not configured using the Factory pattern with a ``create_app`` function. If you want to use the celery task API within an app configured using the factory pattern, call the task from the ``celery`` plugin object:

.. code-block:: python

    celery = Celery()

    @celery.task
    def add(x, y):
      return x + y

    app = Flask(__name__)
    celery.init_app(app)

    celery.task.add.delay(1, 2)


Alternatively, if you don't need the celery workers to have tasks registered and are happy with just submitting them dynamically, use the ``celery.submit()`` method detailed above.

For more information on registering tasks and configuration options available, see the `Celery Task documentation`_.


Task Scheduling
+++++++++++++++

Another useful feature provided by this function is declarative mechanism for scheduling tasks. With this extension, developers no longer need to manually add entries to the celery ``beat`` configuration (or even worry about starting a celery ``beat`` service).

To schedule a periodic task to run alongside the application, use the ``celery.schedule()`` decorator. For instance, to schedule a task to run every night at midnight:

.. code-block:: python

    @celery.schedule(hour=0, minute=0, name='scheduled-task-to-run-at-midnight')
    def scheduled_task():
      # do something ...
      return

The arguments to the schedule decorator can either be numeric:

.. code-block:: python

    @celery.schedule(30, args=(1, 2), kwargs=dict(arg3='foo'))
    def task_to_run_every_30_seconds(arg1, arg2, arg3='test'):
      # do something ...
      return

Keyword arguments to the ``celery.crontab`` function:

.. code-block:: python

    @celery.schedule(hour=7, minute=30, day_of_week=1)
    def task_to_run_every_monday_morning():
      # do something ...
      return

Or, a solar schedule:

.. code-block:: python

    from celery.schedules import solar

    @celery.schedule(solar('sunset', -37.81753, 144.96715), name='solar-task')
    def task_to_run_every_sunset():
      # do something ...
      return


In addition, if you don't want to use this decorator, you can still schedule tasks via the ``CELERYBEAT_SCHEDULE`` configuration option. For more information on task scheduling, including ``crontab`` and ``solar`` schedule configuration, see the `Celery Periodic Tasks documentation`_.


Status Updates
++++++++++++++

Another divergence from the original Celery API is how ``Task`` objects are referenced in code. This extension takes a more Flask-y approach to accessing said information, where a proxied object called ``current_task`` is available for developers to reference throughout their application. This paradigm is similar to the ``current_app`` or ``current_user`` object commonly referenced in flask applications. For example, to reference the current task and update the state metadata:

.. code-block:: python

  from flask_execute import current_task

  def add(a, b):
    current_task.update_state(state='PROGRESS')
    return a + b

More information about the ``update_state`` method or ``Task`` objects can be found in the `Celery Task documentation`_.

If the function is not currently running in a task, this will return an error because the proxy object will be ``None``. If the method you're using will run both within and outside celery tasks, you'll want to check if the ``current_task`` proxy is available:

.. code-block:: python

    def add(x, y):
      if current_task:
          current_task.update_state(state='PROGRESS')
      return x + y


Writing Safe Code
+++++++++++++++++

As with any program that executes code across multiple threads or processes, developers must be cognizant of how IO is managed at the boundaries across separate application contexts (i.e. how data are passed to and returned from functions). In general, try to write thread-safe code when working on functions that might be sent to celery workers. Some recommendations are as follows:

* Don't pass instantiated SQLAlchemy objects or file streams as arguments to functions. Instead, pass in references (primary keys or other identifiers) to the objects you want to use and query them from within the function before executing other logic.

* Don't pass lambda functions or other non-pickle-able objects as arguments to functions. For information on which objects can and cannot pickle, see the `pickle documentation <https://docs.python.org/2.4/lib/node66.html>`_.

* Don't reference global variables that might change values when the application is created on an external executor. LocalProxy objects in Flask are safe to reference.

* Ensure that functions either return or fail with appropriate and manageable exceptions. This allows developers to more easily diagnose failures that occur on external executors.

* If external libraries are used, import the external libraries within functions using them.


If you run into an issue sending data back and forth to executors, feel free to file a question in the GitHub Issue Tracker for this project.


Management
----------

Starting Celery
+++++++++++++++

As mentioned in the overview of the documentation, this extension can manage the process of starting celery workers the first time a ``celery.submit()`` call is made. It will also pass all celery configuration (i.e. any option starting with ``CELERY``) specified in your application config to Celery. Accordingly, this means you **do not have to manually start workers, beat schedulers, or flower** if all of your workers are to run locally. With this extension, the first time you run a ``celery.submit()`` call:

.. code-block:: python

    def add(x, y):
      return x + y

    celery.submit(add, 1, 2)

The following services will be started in the backround:

1. All workers referenced by the ``CELERY_WORKERS`` config variable. This configuration value can take a numeric number of workers or explicit worker names. This can be disabled using ``CELERY_START_LOCAL_WORKERS=False`` in your application config (recommended for production).

2. The `Celery Flower <https://flower.readthedocs.io/en/latest/>`_ monitoring tool for monitoring celery workers and statuses. This can be disabled using ``CELERY_FLOWER=False`` in your application config (recommended for production).

3. If any tasks are registered via ``celery.schedule``, the `Celery Beat <https://docs.celeryproject.org/en/latest/userguide/periodic-tasks.html>`_ scheduler tool for managing scheduled tasks. This can be disabled using ``CELERY_SCHEDULER=False`` in your application config (recommended for production).

An example **production**, **development**, and **testing** config are shown here:

.. code-block:: python

    # set worker names, don't start services (started externally)
    class ProdConfig:
        ENV = 'development'
        CELERY_WORKERS = ['foo', 'bar']
        CELERY_START_LOCAL_WORKERS = False
        CELERY_FLOWER = False
        CELERY_SCHEDULER = False

    # start workers, flower, and scheduler on first submit call
    class DevConfig:
        ENV = 'development'
        CELERY_WORKERS = 2


    # don't start local workers - run in eager mode
    class TestConfig:
        ENV = 'testing'
        CELERY_ALWAYS_EAGER = True


Above, the ``ProdConfig`` will tell the plugin to not start local workers, because they should be configured externally via the ``flask celery cluster`` or ``flask celery worker`` command-line tools (more info below).

The ``DevConfig`` will start local workers, flower, and the scheduler lazily (i.e. whenever the first ``celery.submit()`` call is made). Whenever the application is torn down, all forked services will be terminated.

The ``TestConfig`` will use the same dispatch tools, but will execute the functions in the main application thread instead of on remote workers (accordingly, workers will not be started on ``celery.submit()``). This is particularly useful during unit testing when running separate workers requires unnecessary overhead.


Command-Line Extensions
+++++++++++++++++++++++

Alternatively, you can still start celery workers manually for your application and reference them via config (recommended for production). Instead of invoking celery directly and specifying the path to the application, you should either use the built-in CLI ``flask celery cluster`` or ``flask celery worker`` methods:

.. code-block:: bash

    # start all specified workers, flower, and scheduler
    ~$ flask celery cluster

    # start single worker
    ~$ flask celery worker

    # start single named worker
    ~$ flask celery worker -n foo@%h

    # start flower
    ~$ flask celery worker

    # start beat scheduler
    ~$ flask celery worker


Each of these cli extensions wrap ``celery`` calls with the application context (even an application factory function). Other cli extensions provided by celery are also available:

.. code-block:: bash

    # ping workers
    ~$ flask celery inspect ping

    # inspect worker stats
    ~$ flask celery inspect stats

    # shut down all workers
    ~$ flask celery control shutdown

    # get status of all workers
    ~$ flask celery status


Accordingly, when using the ``flask`` cli entypoint, you'll need to make sure the application is available as an ``app.py`` file in your local directory, or referenced via the ``FLASK_APP`` environment variable:

.. code-block:: bash

    # without create app function
    ~$ FLASK_APP=my_app flask celery cluster

    # using factory method
    ~$ FLASK_APP=my_app:create_app flask celery cluster


If you really want to invoke celery directly, you must reference ``flask_execute.celery`` as the celery application. This will automatically detect the flask application celery needs to work with using the auto-detection functionality provided by Flask:

 .. code-block:: bash

    # start worker with celery
    ~$ celery -A flask_execute.celery worker --loglevel=info

As alluded to above, if you're using a factory pattern (i.e. with a ``create_app`` function) to create the app, you can reference the application factory at the command-line via environment variable (similar to Flask CLI methods):

.. code-block:: bash

    # recommended
    ~$ FLASK_APP="app:create_app" flask celery worker

    # using celery directly
    ~$  FLASK_APP="app:create_app" celery -A flask_execute.celery worker --loglevel=info


Configuring Workers
+++++++++++++++++++

As alluded to above, with this extension, you have control (via configuration) over how workers are initialized. For example, to configure your application to use a specific number of workers or specific worker names, use:

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
      "foo@localhost": "OK",
      "bar@localhost": "OK"
    }


For more advanced worker configuration, you can make the config option a dictionary with worker names and nested specific configuration options to be passed into celery when creating workers:

.. code-block:: python

    class Config:
        CELERY_WORKERS = {
          'foo': {
            'concurrency': 10,
            'loglevel': 'error',
            'pidfile': '/var/run/celery/%n.pid',
            'queues': ['low-priority', 'high-priority']
          },
          'bar': {
            'concurrency': 5,
            'loglevel': 'info',
            'queues': ['high-priority']
          }
        }


This is equivalent to the following command-line specification:

.. code-block:: bash

    # foo worker
    ~$ flask celery worker -n foo@%h --concurrency=10 --loglevel=error --pidfile=/var/run/celery/%n.pid --queues=low-priority,high-priority

    # bar worker
    ~$ flask celery worker -n bar@%h --concurrency=5 --loglevel=info --queues=high-priority

For more information on the parameters available for configuring celery workers, see the `Celery Worker documentation`_.


Queues
++++++

As alluded to above, you can configure workers to subscribe to specific queues. This extension will automatically detect queues references in worker configuration, and will set them up for you. With this, there's no need to manually specify ``task_routes``, because tasks within this module can be dynamically sent to specific queues, instead of pre-registered as always needing to execute on a specific queue.

For example, to configure your application with two workers that execute from two different queues, use the following configuration:

.. code-block:: python

    class Config:
      CELERY_WORKERS = {
        # worker for priority items
        'foo': {
          'queues': ['low-priority', 'high-priority']
        },

        # worker for high-priority tasks only
        'bar': {
          'queues': ['high-priority']
        }

        # worker for any task
        'baz': {}
      }

Once the queues have been defined for workers, you can submit a task to a specific queue use the following syntax with ``submit()``:

.. code-block:: python

    # submit to default queue
    >>> celery.submit(add, 1, 2)

    # submit to high priority queue
    >>> celery.submit(add, 1, 2, queue='high-priority')

With this syntax, the ``queue`` keyword will be reserved on function calls. Accordingly, developers should be careful not to use that argument for functions that can be submitted to an executor.


Inspection
----------

This extension also provides various utilities for `inspecting <https://docs.celeryproject.org/en/latest/userguide/monitoring.html#management-command-line-utilities-inspect-control>`_ the state of submitted tasks and general stats about workers. These utilities are all available on the extension object once the application has been registered and workers started.

.. code-block:: python

    # ping workers
    >>> celery.inspect.ping()

    # inspect active tasks
    >>> celery.inspect.active()

    # inspect scheduled tasks
    >>> celery.inspect.scheduled()

    # inspect reserved tasks
    >>> celery.inspect.reserved()

    # inspect revoked tasks
    >>> celery.inspect.revoked()

    # inspect registered tasks
    >>> celery.inspect.registered()

    # inspect worker stats
    >>> celery.inspect.stats()


Note that all of this inspection information is also available via the ``Flower`` monitoring tool.


Control
-------

Similarly to the `Inspection`_ tool, the extension provides a proxy for `controlling <https://docs.celeryproject.org/en/latest/userguide/workers.html>`_ celery directly.

.. code-block:: python

    # shutdown all workers
    >>> celery.control.shutdown()

    # restart worker pool
    >>> celery.control.pool_restart()

    # shrink worker pool by 1
    >>> celery.control.pool_shrink(1)

    # expand worker pool by 1
    >>> celery.control.pool_grow(1)

    # manage autoscale settings
    >>> celery.control.autoscale(1, 5)


Configuration
-------------

The majority of customizations for this plugin happen via configuration, and this section covers the various types of customizations available. Alongside new configuration options for this plugin, any celery configuration options (prefixed with ``CELERY*``) specified in your application config to the celery application. For a list of available configuration options, see the `Celery Config documentation`_.


Plugin Configuration
++++++++++++++++++++

New celery configuration keys that specifically change the features of this plugin (not celery) include:

.. tabularcolumns:: |p{6.5cm}|p{10cm}|

================================== =========================================
``PLUGIN_DEFAULT_VARIABLE``        A variable used in the plugin for
                                   something important.

``CELERY_BROKER_URL``              The URL to use for the celery broker backend.
                                   Defaults to redis://localhost:6379.

``CELERY_WORKERS``                 A number of workers, list of worker names, or
                                   dicationary options with worker names and
                                   configuration options. Defaults to ``1``

``CELERY_START_LOCAL_WORKERS``     Whether or not to automatically start workers
                                   locally whenever a ``celery.submit()`` call is
                                   made. Defaults to ``True``, and should be set
                                   to ``False`` in production.

``CELERY_START_TIMEOUT``           How long to wait for starting local workers
                                   before timing out and throwing an error. Defaults
                                   to ``10`` seconds and can be increased if many
                                   local workers will be started by this plugin.

``CELERY_LOG_LEVEL``               The default log level to use across celery services
                                   started by this application.

``CELERY_LOG_DIR``                 A directory where all celery logs will be stored.
                                   The default for this option is the current directory
                                   where the application is run.

``CELERY_FLOWER``                  Whether or not to start the flower monitoring tool
                                   alongside local workers. Default is ``True``, and
                                   the plugin assumes ``flower`` has been installed.
                                   Should be set to ``False`` in production.

``CELERY_FLOWER_PORT``             If flower is configured to run locally, the port
                                   it will run on. Default is ``5555``

``CELERY_FLOWER_ADDRESS``          If flower is configured to run locally the address
                                   flower will run on. Default is ``'127.0.0.1'``.

``CELERY_SCHEDULER``               Whether or not to start the celerybeat scheduler tool
                                   alongside local workers. Default is ``True``, and
                                   should be set to ``False`` in production.

================================== =========================================


Default Overrides
+++++++++++++++++

Existing celery configuration options that have been overridden by this plugin to accommodate various plugin features include:

================================== =========================================
``CELERY_RESULT_SERIALIZER``       The celery result serialization format. To enable
                                   dynamic submission of celery tasks, this plugin
                                   has set the option to ``'pickle'``.

``CELERY_ACCEPT_CONTENT``          A white-list of content-types/serializers to allow.
                                   To enable dynamic submission of celery tasks, this plugin
                                   has set the option to ``['json', 'pickle']``.

``CELERY_TASK_SERIALIZER``         A string identifying the default serialization method to use.
                                   To enable dynamic submission of celery tasks, this plugin
                                   has set the option to ``'pickle'``.

================================== =========================================


Other Customizations
++++++++++++++++++++

In addition to configuration options, this plugin can be customized with specific triggers. The following detail what can be customized:

* ``base_task`` - Base task object to use when creating celery tasks.

The code below details how you can override all of these configuration options:

.. code-block:: python

    from flask import Flask
    from flask_execute import Celery
    from celery import Task

    class MyBaseTask(Task):
        queue = 'hipri'

    app = Flask(__name__)
    celery = Celery(base_task=MyBaseTask)
    celery.init_app(app)


For even more in-depth information on the module and the tools it provides, see the `API <./api.html>`_ section of the documentation.


Troubleshooting
---------------

Below is an evolving list of issues that developers may encounter when trying to set up the plugin. This list will grow and shrink throughout the lifecycle of this plugin. If you run into a new issue that you think should be added to this list, please file a ticket on the GitHub page for the project.

1. ``future.result()`` with timeout never returns and worker logs aren't available or showing changes:

    Celery workers likely can't connect to redis. Run ```flask celery worker``` to debug the connection. See the `Prerequisites`_ section for information on installing and running redis locally.
