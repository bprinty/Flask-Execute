
Usage
=====

The sections below detail how to fully use this module, along with context for design decisions made during development of the plugin.


Section
-------

Info for section


Configuration
-------------

The following configuration values exist for Flask-Authorize.
Flask-Authorize loads these values from your main Flask config which can
be populated in various ways. Note that some of those cannot be modified
after the database engine was created so make sure to configure as early as
possible and to not modify them at runtime.

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
