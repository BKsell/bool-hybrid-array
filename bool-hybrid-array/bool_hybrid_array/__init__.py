import sys
from types import ModuleType
from . import core
from .core import __builtins__,builtins
__version__ = "9.10.3"
public_objects = []
for name in dir(core):
    if not name.startswith("_"):
        obj = getattr(core, name)
        if isinstance(obj, (type, ModuleType)) or callable(obj):
            public_objects.append(name)
__all__ = public_objects + ["__version__","__builtins__","core","builtins","__dict__"]
globals().update({
    name: getattr(core, name)
    for name in public_objects
})
try:
    __dict__ = ProtectedBuiltinsDict(globals())
    sys.modules[__name__] = ProtectedBuiltinsDict(globals().copy())
    sys.modules[__name__].name = 'bool_hybrid_array'
    core.__dict__ = ProtectedBuiltinsDict(core.__dict__)
except:
    pass

