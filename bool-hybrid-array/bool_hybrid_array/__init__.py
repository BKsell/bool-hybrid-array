import sys
from types import ModuleType,FunctionType
from . import core
from .core import __builtins__,builtins
from . import int_array
__version__ = "9.10.19"
public_objects = []
def jit_class_methods(cls):
    for attr_name in dir(cls):
        if not attr_name.startswith("_"):
            attr = getattr(cls, attr_name)
            if isinstance(attr, FunctionType):
                try:
                    setattr(cls, attr_name, jit(attr))
                except:
                    pass
            elif isinstance(attr, classmethod):
                original_func = attr.__func__
                try:
                    setattr(cls, attr_name, classmethod(jit(original_func)))
                except:
                    pass
    return cls
for name in dir(core):
    if not name.startswith("_"):
        obj = getattr(core, name)
        if isinstance(obj, (type, ModuleType)) or callable(obj):
            public_objects.append(name)
            if isinstance(obj,FunctionType):
                try:setattr(core,name,jit(obj))
                except:pass
            elif isinstance(obj,type):
                jit_class_methods(obj)
__all__ = public_objects + ["__version__","__builtins__","core","builtins","__dict__","int_array"]
globals().update({
    name: getattr(core, name)
    for name in public_objects
})
try:
    __dict__ = ProtectedBuiltinsDict(globals())
    sys.modules[__name__+'.int_array'] = ProtectedBuiltinsDict(int_array.__dict__)
    sys.modules[__name__] = ProtectedBuiltinsDict(globals().copy())
    sys.modules[__name__].name = 'bool_hybrid_array'
    core.__dict__ = ProtectedBuiltinsDict(core.__dict__)
except:
    pass

