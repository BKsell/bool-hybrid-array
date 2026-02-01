# -*- coding: utf-8 -*-
import sys
from types import ModuleType,FunctionType
try:from . import compile_core as core
except:from . import core
from .core import __builtins__,builtins
try:from . import int_array
except:pass
__version__ = "9.11.13"
public_objects = []
for name in dir(core):
    if not name.startswith("_"):
        obj = getattr(core, name)
        if isinstance(obj, (type, ModuleType)) or callable(obj):
            public_objects.append(name)
__all__ = public_objects + ["__version__","__builtins__","core","builtins","__dict__","int_array"]
globals().update({
    name: getattr(core, name)
    for name in public_objects
})
try:
    sys.modules[__name__] =  ProtectedBuiltinsDict(globals())
    sys.modules[__name__].name = __name__
    sys.modules[__name__+'.core'] = ProtectedBuiltinsDict(core.__dict__,name = f'{__name__}.core')
    __dict__ = ProtectedBuiltinsDict(globals())
    sys.modules[__name__+'.int_array'] = ProtectedBuiltinsDict(int_array.__dict__,name = __name__+'.int_array')
    core.__dict__ = ProtectedBuiltinsDict(core.__dict__)
except:
    pass

