
Overview
========

Provide overview snippet of what the plugin does.


A Minimal Application
---------------------


Setting up the flask application with extensions:


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

Here is how you use the plugin:

.. code-block:: python

    # insert code here ...


For more in-depth discussion on design considerations and how to fully utilize the plugin, see the `User Guide <./usage.html>`_.
