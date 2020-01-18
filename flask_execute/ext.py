# -*- coding: utf-8 -*-
#
# Module for spinning up application context
# with celery worker, using Flask's auto-detection
# functionality.
#
# ------------------------------------------------

from flask.cli import ScriptInfo
info = ScriptInfo()
app = info.load_app()

if not hasattr(app, 'extensions') or \
   'celery' not in app.extensions:
    raise AssertionError(
        'Celery plugin has not been registered with application. '
        'Please see documentation for how to configure this extension.'
    )

plugin = app.extensions['celery']
celery = plugin.controller
