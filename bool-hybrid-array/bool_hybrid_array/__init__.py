# -*- coding: utf-8 -*-
import sys
from types import FunctionType
from . import core
import builtins,inspect
from .core import ProtectedBuiltinsDict
try:from . import int_array,float_array
except:pass
try:from . import struct_array
except:pass
try:from . import twg_sort
except:pass
try:from . import _cppiostream
except:pass
__version__ = "9.13.3"
public_objects = {
        "BHA_lazy_sieve":core.BHA_lazy_sieve,
        "np": core.np,
        "T": core.BHA_bool(1),
        "F": core.BHA_bool(0),
        "BHA_bool": core.BHA_bool,
        "BHA_Bool": core.BHA_Bool,
        "BHA_List": core.BHA_List,
        "FalsesArray": core.FalsesArray,
        "TruesArray": core.TruesArray,
        "BoolHybridArr": core.BoolHybridArr,
        "BHA_Iterator": core.BHA_Iterator,
        "BoolHybridArray": core.BoolHybridArray,
        "ResurrectMeta": core.ResurrectMeta,
        "namespace": core.namespace,
        "ProtectedBuiltinsDict": core.ProtectedBuiltinsDict,
        "BHA_Function": core.BHA_Function,
        "Ask_BHA": core.Ask_BHA,
        "Create_BHA": core.Create_BHA,
        "BHAX_Descriptor": core.BHAX_Descriptor,
        "numba_opt": core.numba_opt,
        "cin": core.cin,
        "cout": core.cout,
        "endl": core.endl,
        "BHA_Queue": core.BHA_Queue,
        "create_mt_xor25_generator": core.create_mt_xor25_generator,
        "BHA_string": core.BHA_string,
        "mt_xor25": core.mt_xor25,
        "umfs": core.umfs,
        "UltraMersenneFractalSponge": core.UltraMersenneFractalSponge,
}
nobuiltins_objects = {
        "istream": core.istream,
        "ostream": core.ostream,
        "filebuf": core.filebuf,
        "ifstream": core.ifstream,
        "ofstream": core.ofstream,
        "fstream": core.fstream,
        "Manipulator": core.Manipulator,
        "setw": core.setw,
        "setprecision": core.setprecision,
        "setfill": core.setfill,
        "ignore": core.ignore,
        "flush": core.flush,
        "boolalpha": core.boolalpha,
        "noboolalpha": core.noboolalpha,
        "showbase": core.showbase,
        "noshowbase": core.noshowbase,
        "showpoint": core.showpoint,
        "noshowpoint": core.noshowpoint,
        "uppercase": core.uppercase,
        "nouppercase": core.nouppercase,
        "showpos": core.showpos,
        "noshowpos": core.noshowpos,
        "fixed": core.fixed,
        "scientific": core.scientific,
        "left": core.left,
        "right": core.right,
        "internal": core.internal,
        "ios_dec": core.ios_dec,
        "ios_oct": core.ios_oct,
        "ios_hex": core.ios_hex,
        "ios_basefield": core.ios_basefield,
        "ios_left": core.ios_left,
        "ios_right": core.ios_right,
        "ios_internal": core.ios_internal,
        "ios_adjustfield": core.ios_adjustfield,
        "ios_scientific": core.ios_scientific,
        "ios_fixed": core.ios_fixed,
        "ios_floatfield": core.ios_floatfield,
        "ios_boolalpha": core.ios_boolalpha,
        "ios_showbase": core.ios_showbase,
        "ios_showpoint": core.ios_showpoint,
        "ios_uppercase": core.ios_uppercase,
        "ios_showpos": core.ios_showpos,
        "ios_in": core.ios_in,
        "ios_out": core.ios_out,
        "ios_ate": core.ios_ate,
        "ios_app": core.ios_app,
        "ios_trunc": core.ios_trunc,
        "ios_binary": core.ios_binary,
        "ios_base_goodbit": core.ios_base_goodbit,
        "ios_base_badbit": core.ios_base_badbit,
        "ios_base_eofbit": core.ios_base_eofbit,
        "ios_base_failbit": core.ios_base_failbit,
}
__all__ = tuple(public_objects) + tuple(nobuiltins_objects) + ("__version__","__builtins__","builtins","core","builtins","int_array","float_array","struct_array","twg_sort")
globals().update(public_objects)
globals().update(nobuiltins_objects)
if inspect.ismodule(builtins):
    for name, obj in public_objects.items():
        setattr(builtins, name, obj)
    builtins.BHA_Bool.T, builtins.BHA_Bool.F = BHA_bool(1), BHA_bool(0)
    Tid, Fid = id(builtins.T), id(builtins.F)
    original_builtins_dict = builtins.__dict__.copy()
    __builtins__ = ProtectedBuiltinsDict(original_builtins_dict)
    builtins = __builtins__
    sys.modules['builtins'] = builtins
    builtins.name = 'builtins'
    attrs = [
        "__name__",
        "__doc__",
        "__spec__",
        "__loader__",
        "__path__",
        "__annotations__",
    ]
    for attr in attrs:
        if attr in original_builtins_dict:
            try:setattr(builtins, attr, original_builtins_dict[attr])
            except:pass

try:
    sys.modules[__name__] =  ProtectedBuiltinsDict(globals())
    sys.modules[__name__].name = __name__
    sys.modules[__name__].core = ProtectedBuiltinsDict(core.__dict__,name = f'{__name__}.core')
    __dict__ = ProtectedBuiltinsDict(globals())
    sys.modules[__name__].int_array = ProtectedBuiltinsDict(int_array.__dict__,name = __name__+'.int_array')
    sys.modules[__name__].float_array = ProtectedBuiltinsDict(float_array.__dict__,name = __name__+'.float_array')
    try:
        sys.modules[__name__].struct_array = ProtectedBuiltinsDict(struct_array.__dict__,name = __name__+'.struct_array')
    except Exception:
        pass
    core.__dict__ = ProtectedBuiltinsDict(core.__dict__)
except:
    pass
