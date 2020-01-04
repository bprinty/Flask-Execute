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
executor = app.celery
