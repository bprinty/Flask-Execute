# -*- coding: utf-8 -*-

__pkg__ = 'Flask-Celery'
__url__ = 'https://github.com/bprinty/Flask-Celery'
__info__ = 'Simple Celery integration for Flask applications.'
__author__ = 'Blake Printy'
__email__ = 'bprinty@gmail.com'
__version__ = '0.1.0'


from .plugin import Celery            ## noqa
from .plugin import current_task      ## noqa
