# -*- coding: utf-8 -*-
try:from .compile_core import *
except:from .core import *
__all__ = tuple(globals())