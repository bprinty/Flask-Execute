# -*- coding: utf-8 -*-
#
# Plugin Setup
#
# ------------------------------------------------


# imports
# -------
# ...


# plugin
# ------
class Plugin(object):
    """
    Plugin for updating flask functions to handle class-based URL
    routing.
    """

    def __init__(self, app=None, option=False):
        self.option = option
        if app is not None:
            self.init_app(app)
        return

    def init_app(self, app):
        self.app = app
        self.app.config.setdefault('PLUGIN_DEFAULT_VARIABLE', False)
        return
