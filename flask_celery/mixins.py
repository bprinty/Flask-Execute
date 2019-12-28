# -*- coding: utf-8 -*-
#
# Database mixins
#
# ------------------------------------------------


# imports
# -------
from sqlalchemy import Column
from sqlalchemy.types import String
from sqlalchemy.ext.declarative import declared_attr


# mixins
# ------
class ExampleMixin(object):
    """
    Example database mixin to be used in extension.
    """

    @declared_attr
    def attr(cls):
        return Column(String)
