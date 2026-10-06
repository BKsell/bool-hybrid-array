# cython: language_level=3,boundscheck=False,wraparound=False,cdivision=True,nonecheck=False,overflowcheck=False,initializedcheck=False,infer_types=True,annotation_typing=True,profile=False,linetrace=False,emit_code_comments=False,c_api_binop_methods=True
from __future__ import annotations
import inspect
try:from mypy_extensions import mypyc_attr
except:
    def mypyc_attr(*a,**k):
        return lambda func:func
from multiprocessing import Queue
import builtins,multiprocessing
from types import MappingProxyType
import array,bisect,numpy as np
from collections.abc import MutableSequence,Iterable,Generator,Iterator,Sequence,Collection
import itertools,copy,sys,math,weakref,random,mmap,os,pathlib,shutil,zipfile,json
from itertools import dropwhile
from functools import reduce
import operator,ctypes,gc,abc,types
_C_UBYTE_PTR = ctypes.POINTER(ctypes.c_ubyte)
from functools import lru_cache
from typing import _GenericAlias
from typing import Callable, Union, Sequence, MutableSequence, Any, overload, Sized
import hashlib
import time
import platform
import threading
hybrid_array_cache:weakref.WeakKeyDictionary[BoolHybridArray,int] = weakref.WeakKeyDictionary()
try:
    msvcrt = ctypes.CDLL("msvcrt.dll")
    memcpy = msvcrt.memcpy
except:
    try:
        libc = ctypes.CDLL('libc.so.6')
    except:
        libc = ctypes.CDLL('libc.so')
    memcpy = libc.memcpy
memcpy.restype = ctypes.c_void_p
memcpy.argtypes = (ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t)
if hasattr(types, 'GenericAlias'):
    _GenericAlias = types.GenericAlias
class ResurrectMeta(abc.ABCMeta,metaclass=abc.ABCMeta):
    __module__ = 'bool_hybrid_array'
    name = 'ResurrectMeta'
    def __new__(cls, name, bases, namespace):
        meta_bases = tuple(type(base) for base in bases)
        if cls not in meta_bases:
            meta_bases = (cls,) + meta_bases
        obj = super().__new__(cls, name, bases, namespace)
        super_cls = super(ResurrectMeta, obj)
        super_cls.__setattr__('x',None)
        super_cls.__setattr__('name', name)
        super_cls.__setattr__('bases', bases)
        super_cls.__setattr__('namespace', namespace)
        super_cls.__setattr__('original_dict', dict(obj.__dict__))
        try:del obj.original_dict["__abstractmethods__"]
        except:pass
        try:del obj.original_dict["_abc_impl"]
        except:pass
        try:del obj.original_dict['_abc_registry']
        except:pass
        try:del obj.original_dict['_abc_cache']
        except:pass
        try:del obj.original_dict['_abc_negative_cache']
        except:pass
        try:del obj.original_dict['_abc_negative_cache_version']
        except:pass
        super_cls.__setattr__('original_dict', MappingProxyType(obj.original_dict))
        return obj
    @lru_cache
    def __str__(cls):
        return f'{cls.__module__}.{cls.name}'
    @lru_cache
    def __repr__(cls,detailed = False):
        if detailed:
            name, bases, namespace = cls.name,cls.bases,cls.namespace
            return f'ResurrectMeta(cls = {cls},{name = },{bases = },{namespace = })'
        return str(cls)
    def __del__(cls):
        try:
            setattr(builtins,cls.name,cls)
            if not sys.is_finalizing():
                print(f'\033[31m警告：禁止删除常变量：{cls}！\033[0m')
                raise TypeError(f'禁止删除常变量：{cls}')
        except NameError:pass
    def __hash__(cls):
        return hash(cls.name+cls.__module__)
    def __setattr__(cls,name,value):
        if not hasattr(cls, 'x') or name.startswith('_'):
            super().__setattr__(name,value)
            return
        if hasattr(cls, 'name') and cls.name == 'BHA_Bool' and repr(value) in {'T','F'} and name in {'T','F'}:
            super().__setattr__(name,value)
            return
        if hasattr(cls, 'original_dict') and name in cls.original_dict:
            raise AttributeError(f'禁止修改属性：{name}')
        else:
            super().__setattr__(name,value)
    def __delattr__(cls,name):
        if name in cls.original_dict:
            raise AttributeError(f'禁止删除属性：{name}')
        else:
            super().__delattr__(name)
    if 'UnionType' not in types.__dict__:
        def __or__(self,other):
            return Union[self,other]
        __ror__ = __or__
    def __getitem__(self,*args):
        return _GenericAlias(self,args)
    x = None
    original_dict = {"__delattr__":__delattr__,"__getitem__":__getitem__,"__setattr__":__setattr__,"__hash__":__hash__,
    "__new__":__new__,"__del__":__del__,"__str__":__str__,"__repr__":__repr__,"__class__":abc.ABCMeta,"original_dict":None}
    try:
        original_dict["original_dict"] = original_dict
        original_dict["__ror__"] = __ror__
        original_dict["__or__"] = __or__
    except:
        pass
    original_dict = MappingProxyType(original_dict)
ResurrectMeta.__class__ = ResurrectMeta
class BHA_Function(metaclass=ResurrectMeta):
    def __init__(self,v):
        self.data,self.module = v,__name__
    def __call__(self,*a,**b):
        return self.data(*a,**b)
    def __getattr__(self,name):
        return getattr(self.data,name)
    @classmethod
    def string_define(cls, name, text, positional, default):
        param_strs = list(positional)
        param_strs.extend([f"{k}={v!r}" for k, v in default.items()])
        params = ", ".join(param_strs)
        func_code = f"""
def {name}({params}):
    {text}
        """
        local_namespace = {}
        exec(func_code, globals(), local_namespace)
        dynamic_func = local_namespace[name]
        return cls(dynamic_func)
class BoolHybridArray(MutableSequence,Exception,metaclass=ResurrectMeta):
    __module__ = 'bool_hybrid_array'
    class _CompactBoolArray(MutableSequence,Exception,metaclass = ResurrectMeta):
        def __init__(self, size: int):
            self.size = size
            self.n_uint8 = (size + 7) >> 3
            self.data = np.zeros(self.n_uint8, dtype=np.uint8)
            self._cptr = None

        def _real_capacity(self) -> int:
            return len(self.data) << 3

        def _resize_capacity(self, want_bit_count:int):
            if want_bit_count <= self._real_capacity():
                return
            old_n_uint8 = len(self.data)
            old_cap_bit = self._real_capacity()
            new_cap_bit = int(old_cap_bit ** 1.01981 * 1.3654 + 94)
            new_n_uint8 = (max(new_cap_bit, want_bit_count) +7) >>3
            self.data.resize(new_n_uint8, refcheck=False)
            if old_n_uint8 < new_n_uint8:
                self.data[old_n_uint8:] = 0
            self._cptr = None

        def _set_single(self, index: int, value: bool, ctypes_arr):
            uint8_pos = index >> 3
            bit_offset = index & 7
            ctypes_arr[uint8_pos] &= ~(1 << bit_offset) & 0xFF
            if value:
                ctypes_arr[uint8_pos] |= (1 << bit_offset)

        def _get_single(self, index:int) -> bool:
            uint8_pos = index >> 3
            bit_offset = index & 7
            return bool((self.data[uint8_pos] >> bit_offset) & 1)

        def _get_cptr(self):
            if self._cptr is None:
                self._cptr = self.data.ctypes.data_as(_C_UBYTE_PTR)
            return self._cptr

        def __getstate__(self):
            return {'size': self.size, 'n_uint8': self.n_uint8, 'data': self.data}

        def __setstate__(self, state):
            self.size = state['size']
            self.n_uint8 = state['n_uint8']
            self.data = state['data']
            self._cptr = None

        def __reduce__(self):
            return (self.__class__, (self.size,), self.__getstate__())

        def __setitem__(self, index: int | slice, value: Any):
            ctypes_arr = self._get_cptr()
            if isinstance(index, slice):
                start, stop, step = index.indices(self.size)
                indices = range(start, stop, step)
                if isinstance(value, Iterable):
                    if hasattr(value, '__len__') and len(value)!= len(indices):
                        raise ValueError("值的数量与切片长度不匹配")
                    for i, val in zip(indices, value):
                        self._set_single(i, bool(val), ctypes_arr)
                elif isinstance(value, (Iterator, Generator, map)):
                    for i, val in zip(indices, value):
                        self._set_single(i, bool(val), ctypes_arr)
                else:
                    val_bool = bool(value)
                    for i in indices:
                        self._set_single(i, val_bool, ctypes_arr)
                return
            if not (0 <= index < self.size):
                raise IndexError(f"密集区索引 {index} 超出范围 [0, {self.size})")
            self._set_single(index, bool(value), ctypes_arr)

        def __getitem__(self, index: int | slice) -> bool | list[bool]:
            if isinstance(index, slice):
                start, stop, step = index.indices(self.size)
                result = []
                for i in range(start, stop, step):
                    result.append(self._get_single(i))
                return result
            if not (0 <= index < self.size):
                raise IndexError(f"密集区索引 {index} 超出范围 [0, {self.size})")
            return self._get_single(index)

        def __len__(self):
            return self.size

        def set_all(self, value: bool):
            ctypes_arr = self.data.ctypes.data_as(ctypes.POINTER(ctypes.c_ubyte))
            length = len(self.data)
            if value:ctypes.memset(ctypes_arr, 0xff, length)
            else:ctypes.memset(ctypes_arr, 0, length)

        def copy(self):
            new_instance = self.__class__(size=self.size)
            new_instance.data = self.data.copy()
            return new_instance

        def insert(self, idx:int, value:bool):
            idx = max(0, min(idx, self.size))
            self._resize_capacity(self.size + 1)
            bp = idx >> 3
            bo = idx & 7
            d = self.data
            tail = d[bp:]
            lo = tail[0] & ((1 << bo) - 1)
            msbs = tail >> 7
            tail <<= 1
            tail[1:] |= msbs[:-1]
            tail[0] = (tail[0] & (0xFF - ((1 << bo) - 1))) | lo
            if value:
                d[bp] |= (1 << bo)
            else:
                d[bp] &= ~(1 << bo) & 0xFF
            self.size += 1

        def pop(self, idx:int = -1) -> bool:
            if self.size <=0:
                raise IndexError("pop from empty _CompactBoolArray")
            idx = idx if idx >=0 else idx + self.size
            if not (0 <= idx < self.size):
                raise IndexError("pop index out of range")
            bp = idx >> 3
            bo = idx & 7
            d = self.data
            val = (d[bp] >> bo) & 1
            tail = d[bp:]
            lo = tail[0] & ((1 << bo) - 1)
            lsbs = tail << 7
            tail >>= 1
            tail[:-1] |= lsbs[1:]
            tail[0] = (tail[0] & (0xFF - ((1 << bo) - 1))) | lo
            self.size -= 1
            return bool(val)
        def _del_range(self, start, n):
            """批量删除 [start, start+n) 的位，后续位左移 n；大整数移位 O(尾部) 无中间数组。"""
            if n <= 0 or start >= self.size:
                return
            end = self.size
            if start + n >= end:
                new_size = start
                new_n = (new_size + 7) >> 3
                if new_n:
                    val = int.from_bytes(self.data.tobytes(), 'little')
                    low = val & ((int(1) << start) - int(1)) if start else 0
                    low &= (int(1) << new_size) - int(1)
                    self.data = np.frombuffer(low.to_bytes(new_n, 'little'), dtype=np.uint8).copy()
                else:
                    self.data = np.zeros(0, dtype=np.uint8)
                self.n_uint8 = len(self.data)
                self.size = new_size
                self._cptr = None
                return
            val = int.from_bytes(self.data.tobytes(), 'little')
            low = val & ((int(1) << start) - int(1)) if start else 0
            high = val >> (start + n)
            new_size = end - n
            new_val = (low | (high << start)) & ((int(1) << new_size) - int(1))
            new_n = (new_size + 7) >> 3
            self.data = np.frombuffer(new_val.to_bytes(new_n, 'little'), dtype=np.uint8).copy()
            self.n_uint8 = new_n
            self.size = new_size
            self._cptr = None
        def _ins_range(self, start, n):
            """批量在 start 处插入 n 个空位（[start, size) 右移 n）；大整数移位 O(尾部) 无中间数组。"""
            if n <= 0:
                return
            old_size = self.size
            self._resize_capacity(old_size + n)
            new_size = old_size + n
            if old_size:
                val = int.from_bytes(self.data.tobytes(), 'little')
                low = val & ((int(1) << start) - int(1)) if start else 0
                high = (val >> start) << (start + n) if start < old_size else 0
                new_val = (low | high) & ((int(1) << new_size) - int(1))
            else:
                new_val = 0
            new_n = (new_size + 7) >> 3
            self.data = np.frombuffer(new_val.to_bytes(new_n, 'little'), dtype=np.uint8).copy()
            self.n_uint8 = new_n
            self.size = new_size
            self._cptr = None
        def __delitem__(self, key:int|slice):
            if isinstance(key, slice):
                start, stop, step = key.indices(self.size)
                if step > 0:
                    for pos in reversed(range(start, stop, step)):
                        self.pop(pos)
                else:
                    for pos in range(start, stop, step):
                        self.pop(pos)
                return
            idx = key if key >=0 else key + self.size
            self.pop(idx)

    def __init__(self, split_index:int=0, size:int=0, is_sparse=False ,Type:callable = None,hash_ = True) -> None:
        self.Type = Type if Type is not None else BHA_Bool
        self.split_index : int = int(split_index)
        self.size : int = size or 0
        self.is_sparse = is_sparse
        self.small = self._CompactBoolArray(self.split_index + 1)
        self.small.set_all(not is_sparse)
        self.large : array.array = array.array('I') if size < 1<<32 else array.array('Q') if size < 1 << 64 else []
        self.hash_ = hash_
        if hash_:
            while True:
                try:
                    for existing_array, existing_hash in hybrid_array_cache.items():
                        try:
                            if self.size != existing_array.size:
                                continue
                            elif self == existing_array:
                                self._cached_hash = existing_hash
                                return
                        except Exception:
                            continue
                    break
                except RuntimeError:
                    continue
        self._cached_hash:int = id(self)
        if hash_:
            hybrid_array_cache[self] = self._cached_hash
    def __call__(self, func:callable):
        func.self = self
        def wrapper(*args, **kwargs):
            return func(self, *args, **kwargs)
        setattr(self, func.__name__, wrapper)
        return func

    def resize(self, size:int):
        size = operator.index(size)
        if size < 0:
            raise ValueError(f"resize 要求 size >= 0，收到 {size}")
        self.size = size

    def __hash__(self):
        return self._cached_hash

    def accessor(self, i: int, value = None):
        def _get_sparse_info(index: int) -> tuple[int, bool]:
            pos = bisect.bisect_left(self.large, index)
            exists = pos < len(self.large) and self.large[pos] == index
            return pos, exists
        if value is None:
            if i <= self.split_index:
                return self.small[i]
            else:
                _, exists = _get_sparse_info(i)
                return exists if self.is_sparse else not exists
        else:
            if i <= self.split_index:
                self.small[i] = value
                return None
            else:
                pos, exists = _get_sparse_info(i)
                condition = not value
                if self.is_sparse != condition:
                    if not exists:
                        self.large.insert(pos, i)
                elif exists:
                    del self.large[pos]
                return

    @overload
    def __getitem__(self, idx: int, /) -> Any: ...
    @overload
    def __getitem__(self, idx: slice, /) -> list: ...
    def __getitem__(self, key:int|slice = -1,/) -> Any:
        if isinstance(key, slice):
            start, stop, step = key.indices(self.size)
            if step == 1:
                return self._slice_bits(start, stop)
            return BoolHybridArr((self[i] for i in range(start, stop, step)), hash_=False)
        key = key if key >=0 else key + self.size
        if 0 <= key < self.size:
            return self.Type(self.accessor(key))
        raise IndexError("索引超出范围")

    def _slice_bits(self, start: int, stop: int):
        """提取 [start, stop) 位段为新 BHA（step=1，保持稀疏结构；small 大整数移位 + large bisect 切片）。"""
        n = stop - start
        if n <= 0:
            return BoolHybridArr((), hash_=False)
        split = self.split_index
        new_arr = BoolHybridArr((), hash_=False)
        new_arr.size = n
        new_arr.Type = self.Type
        new_arr.is_sparse = self.is_sparse
        new_arr.hash_ = False
        small_s = max(start, 0)
        small_e = min(stop, split + 1)
        if small_s < small_e:
            seg_len = small_e - small_s
            val = int.from_bytes(self.small.data.tobytes(), 'little')
            seg_val = (val >> small_s) & ((int(1) << seg_len) - int(1))
            new_split = small_e - start - 1
            new_small = self._CompactBoolArray(new_split + 1)
            new_small.set_all(not self.is_sparse)
            nb = (new_split + 8) >> 3
            new_small.data = np.frombuffer(seg_val.to_bytes(nb, 'little'), dtype=np.uint8).copy()
            new_small.n_uint8 = nb
            new_small._cptr = None
            new_arr.small = new_small
            new_arr.split_index = new_split
        else:
            new_arr.small = self._CompactBoolArray(0)
            new_arr.split_index = -1
        lo = bisect.bisect_left(self.large, max(start, split + 1))
        hi = bisect.bisect_left(self.large, stop)
        if hi > lo:
            if isinstance(self.large, array.array):
                new_arr.large = array.array(self.large.typecode, (x - start for x in self.large[lo:hi]))
            else:
                new_arr.large = [x - start for x in self.large[lo:hi]]
        return new_arr

    def _replace_bits(self, start: int, stop: int, other):
        """等长替换 [start, stop) 位段为 other（other.size == stop-start）；small 逐位写 + large 逐位判定有序插入。"""
        n = stop - start
        if other.size != n:
            raise ValueError("位段长度不匹配")
        split = self.split_index
        old_lo = bisect.bisect_left(self.large, max(start, split + 1))
        old_hi = bisect.bisect_left(self.large, stop)
        del self.large[old_lo:old_hi]
        ss = max(start, 0)
        se = min(stop, split + 1)
        if ss < se:
            off0 = ss - start
            for off in range(off0, off0 + (se - ss)):
                self.small[ss + off - off0] = other.accessor(off)
        ls = max(start, split + 1)
        le = stop
        if ls < le:
            o0 = ls - start
            new_large = []
            for off in range(o0, o0 + (le - ls)):
                if (self.is_sparse and other.accessor(off)) or (not self.is_sparse and not other.accessor(off)):
                    new_large.append(ls + off - o0)
            if new_large:
                if isinstance(self.large, array.array):
                    self.large[old_lo:old_lo] = array.array(self.large.typecode, new_large)
                else:
                    self.large[old_lo:old_lo] = new_large

    def _del_bits(self, start: int, stop: int):
        """删除 [start, stop) 位段（长度变化）。small 大整数重组 + large 索引批量删并左移。"""
        n = stop - start
        if n <= 0:
            return
        split = self.split_index
        # large 区按原始索引批量删
        lo = bisect.bisect_left(self.large, max(start, split + 1))
        hi = bisect.bisect_left(self.large, stop)
        del self.large[lo:hi]
        # large 区绝对位索引：删除区间之前的（< start）不动；之后的（≥ stop）整体左移 n 位
        if lo < len(self.large):
            if isinstance(self.large, array.array):
                rest = array.array(self.large.typecode, (x - n for x in self.large[lo:]))
                self.large = self.large[:lo] + rest
            else:
                self.large[lo:] = [x - n for x in self.large[lo:]]
        # small 区大整数删除
        ss = max(start, 0)
        se = min(stop, split + 1)
        if ss < se:
            seg_len = se - ss
            sm = self.small
            val = int.from_bytes(sm.data.tobytes(), 'little') & ((int(1) << sm.size) - int(1))
            seg1 = val & ((int(1) << ss) - int(1)) if ss else 0
            seg2 = val >> se
            new_val = seg1 | (seg2 << ss)
            new_size = sm.size - seg_len
            nb = (new_size + 7) >> 3
            sm.data = np.frombuffer(new_val.to_bytes(nb, 'little'), dtype=np.uint8).copy()
            sm.size = new_size
            sm.n_uint8 = nb
            sm._cptr = None
            self.split_index -= seg_len
        self.size -= n

    def _insert_bits(self, pos: int, other):
        """在 pos 位处插入 other 全部位（长度变化）。small 大整数插入 + large 索引平移合并。"""
        n = other.size
        if n <= 0:
            return
        split = self.split_index
        o_val = 0
        if other.split_index >= 0:
            o_val = int.from_bytes(other.small.data.tobytes(), 'little') & ((int(1) << other.size) - int(1))
        if other.is_sparse:
            for x in other.large:
                o_val |= int(1) << x
        else:
            # large 存假位：真位 = large 区全真 - 假位索引
            o_val |= (int(1) << other.size) - (int(1) << (other.split_index + 1))
            for x in other.large:
                o_val &= ~(int(1) << x)
        if pos <= split + 1:
            # 全 small 插入：pos..pos+n 均落在新 small 区
            sm = self.small
            val = int.from_bytes(sm.data.tobytes(), 'little') & ((int(1) << sm.size) - int(1))
            seg1 = val & ((int(1) << pos) - int(1)) if pos else 0
            seg2 = val >> pos
            new_val = seg1 | (o_val << pos) | (seg2 << (pos + n))
            new_size = sm.size + n
            nb = (new_size + 7) >> 3
            sm.data = np.frombuffer(new_val.to_bytes(nb, 'little'), dtype=np.uint8).copy()
            sm.size = new_size
            sm.n_uint8 = nb
            sm._cptr = None
            self.split_index += n
            if self.large:
                if isinstance(self.large, array.array):
                    self.large = array.array(self.large.typecode, (x + n for x in self.large))
                else:
                    self.large = [x + n for x in self.large]
        else:
            # large 区插入：≥pos 的索引 +n；other 位填 [pos, pos+n)
            if self.large:
                if isinstance(self.large, array.array):
                    self.large = array.array(self.large.typecode, (x + n if x >= pos else x for x in self.large))
                else:
                    self.large = [x + n if x >= pos else x for x in self.large]
            new_idx = []
            for off in range(n):
                bit = (o_val >> off) & 1
                if (self.is_sparse and bit) or (not self.is_sparse and not bit):
                    new_idx.append(pos + off)
            if new_idx:
                ins_at = bisect.bisect_left(self.large, pos)
                if isinstance(self.large, array.array):
                    self.large[ins_at:ins_at] = array.array(self.large.typecode, new_idx)
                else:
                    self.large[ins_at:ins_at] = new_idx
        self.size += n

    def swap(self, idx1, idx2):
        n = self.size
        idx1 = idx1 if idx1 >= 0 else idx1 + n
        idx2 = idx2 if idx2 >= 0 else idx2 + n
        if not (0 <= idx1 < n and 0 <= idx2 < n):
            raise IndexError("swap index out of range")
        if idx1 == idx2:
            return
        split = self.split_index
        if idx1 <= split and idx2 <= split:
            d = self.small.data
            p1, o1 = idx1 >> 3, idx1 & 7
            p2, o2 = idx2 >> 3, idx2 & 7
            if p1 == p2:
                b1 = (d[p1] >> o1) & 1
                b2 = (d[p1] >> o2) & 1
                if b1 != b2:
                    d[p1] = (d[p1] ^ ((1 << o1) | (1 << o2))) & 0xFF
            else:
                b1 = (d[p1] >> o1) & 1
                b2 = (d[p2] >> o2) & 1
                if b1 != b2:
                    d[p1] = ((d[p1] & ~(1 << o1) & 0xFF) | (b2 << o1)) & 0xFF
                    d[p2] = ((d[p2] & ~(1 << o2) & 0xFF) | (b1 << o2)) & 0xFF
            return
        v1 = self.accessor(idx1)
        v2 = self.accessor(idx2)
        if v1 == v2:
            return
        self.accessor(idx1, v2)
        self.accessor(idx2, v1)

    def move(self, idx1, length, idx2):
        n = self.size
        idx1 = idx1 if idx1 >= 0 else idx1 + n
        idx2 = idx2 if idx2 >= 0 else idx2 + n
        idx1 = max(0, min(idx1, n))
        length = max(0, min(length, n - idx1))
        if length == 0:
            return
        idx2 = max(0, min(idx2, n - length))
        if idx2 == idx1:
            return
        split = self.split_index
        ss = split + 1
        len_s = max(0, min(idx1 + length, ss) - idx1)
        a_bits = 0
        if len_s:
            sm = self.small
            val = int.from_bytes(sm.data.tobytes(), 'little') & ((int(1) << sm.size) - int(1))
            a_bits = (val >> idx1) & ((int(1) << len_s) - int(1))
        self._del_bits(idx1, idx1 + length)
        split2 = split - len_s
        ss2 = split2 + 1
        len_l = length - len_s
        special = 1 if self.is_sparse else 0
        a_full = a_bits | ((((int(1) << len_l) - int(1)) if special else 0) << len_s)
        if idx2 <= ss2:
            sm = self.small
            val = int.from_bytes(sm.data.tobytes(), 'little') & ((int(1) << sm.size) - int(1))
            low = val & ((int(1) << idx2) - int(1)) if idx2 else 0
            high = val >> idx2
            new_val = low | (a_full << idx2) | (high << (idx2 + length))
            new_size = sm.size + length
            nb = (new_size + 7) >> 3
            sm.data = np.frombuffer(new_val.to_bytes(nb, 'little'), dtype=np.uint8).copy()
            sm.size = new_size
            sm.n_uint8 = nb
            sm._cptr = None
            self.split_index = split2 + length
            la = self.large
            if la:
                if isinstance(la, array.array):
                    for i in range(len(la)):
                        la[i] = la[i] + length
                else:
                    for i in range(len(la)):
                        la[i] = la[i] + length
        else:
            la = self.large
            if la:
                if isinstance(la, array.array):
                    for i in range(len(la)):
                        if la[i] >= idx2:
                            la[i] = la[i] + length
                else:
                    for i in range(len(la)):
                        if la[i] >= idx2:
                            la[i] = la[i] + length
            new_idx = []
            for off in range(length):
                bit = (a_full >> off) & 1
                if (self.is_sparse and bit) or (not self.is_sparse and not bit):
                    new_idx.append(idx2 + off)
            if new_idx:
                ins_at = bisect.bisect_left(self.large, idx2)
                if isinstance(self.large, array.array):
                    self.large[ins_at:ins_at] = array.array(self.large.typecode, new_idx)
                else:
                    self.large[ins_at:ins_at] = new_idx
        self.size += length

    def __setitem__(self, key: int | slice, value:Any) -> None:
        if isinstance(key, int):
            adjusted_key = key if key >= 0 else key + self.size
            if not (0 <= adjusted_key < self.size):
                raise IndexError("索引超出范围")
            self.accessor(adjusted_key, bool(value))
            return
        if isinstance(key, slice):
            if not hasattr(value, '__iter__'):
                start, stop, step = key.indices(self.size)
                if step != 1:
                    for i in range(start, stop, step):
                        self[i] = bool(value)
                    return
                for i in range(start, stop):
                    self[i] = bool(value)
                return
            original_size = self.size
            start, stop, step = key.indices(original_size)
            value_list = list(value)
            new_len = len(value_list)
            slice_span = max(0, stop - start)
            if step != 1:
                slice_indices = range(start, stop, step)
                if new_len != len(slice_indices):
                    raise ValueError(f"值长度与切片长度不匹配：{new_len} vs {len(slice_indices)}")
                for i, val in zip(slice_indices, value_list):
                    self[i] = val
                return
            if new_len == slice_span:
                for offset, val in enumerate(value_list):
                    self[start + offset] = val
                return
            delta = new_len - slice_span
            common = min(new_len, slice_span)
            for offset in range(common):
                self[start + offset] = value_list[offset]
            if delta < 0:
                del_start = start + common
                del_end = del_start + (-delta)
                for i in range(del_end -1, del_start -1, -1):
                    del self[i]
            else:
                for offset in range(common, new_len):
                    self.insert(start + offset, value_list[offset])
            return
        raise TypeError("索引必须是整数或切片")

    def __repr__(self) -> str:
        return(f"BoolHybridArray(split_index={self.split_index}, size={self.size}, "
        +f"is_sparse={self.is_sparse}, small_len={len(self.small)}, large_len={len(self.large)})")

    @overload
    def __delitem__(self, key: int, /) -> None: ...
    @overload
    def __delitem__(self, key: slice, /) -> None: ...
    def __delitem__(self, key: int|slice = -1,/) -> None:
        if isinstance(key, slice):
            start, stop, step = key.indices(self.size)
            if step > 0:
                for i in reversed(range(start,stop,step)):
                    del self[i]
            else:
                for i in range(start,stop,step):
                    del self[i]
            return
        key = key if key >= 0 else key + self.size
        if not (0 <= key < self.size):
            raise IndexError(f"索引 {key} 超出范围 [0, {self.size})")

        if key <= self.split_index:
            self.small.pop(key)
            self.split_index = max(-1, self.split_index - 1)
            for i in range(len(self.large)):
                self.large[i] -= 1
        else:
            pos = bisect.bisect_left(self.large, key)
            if pos < len(self.large) and self.large[pos] == key:
                del self.large[pos]
            adjust_pos = bisect.bisect_right(self.large, key)
            for i in range(adjust_pos, len(self.large)):
                self.large[i] -= 1
        self.size -= 1
        if self.size == 0:
            self.split_index = 0
            del self.large[:]
            self.small = self._CompactBoolArray(1)
            self.small.set_all(not self.is_sparse)
        elif self.split_index < 0:
            self.split_index = 0
            self.small = self._CompactBoolArray(1)
            self.small.set_all(not self.is_sparse)
            if self.large and self.large[0] == 0:
                self.small[0] = self.is_sparse
                self.large.pop(0)
    def compare(self, other:Iterable):
        if not isinstance(other, Iterable):
            return NotImplemented
        it_self = map(operator.itemgetter(0), zip(self))
        it_other = map(operator.itemgetter(0), zip(other))
        a,b = any(it_self),any(it_other)
        if not(a and b):
            if a: return 1
            if b: return -1
            return 0
        it_self,it_other = BHA_Iterator(it_self),BHA_Iterator(it_other)
        l1 = sum(1 for _ in it_self)
        l2 = sum(1 for _ in it_other)
        if (l2 < l1) - (l2 > l1):
            return (l2 < l1) - (l2 > l1)
        diff_pairs = dropwhile(lambda pair: pair[0] == pair[1], zip(it_self, it_other))
        first_diff = next(diff_pairs, None)
        if first_diff is None:
            return 0
        s_bit, o_bit = first_diff
        return -1 if s_bit < o_bit else 1
    def __lt__(self, other):
        res = self.compare(other)
        return NotImplemented if res is NotImplemented else res < 0
    def __le__(self, other):
        res = self.compare(other)
        return NotImplemented if res is NotImplemented else res <= 0
    def __ge__(self, other):
        res = self.compare(other)
        return NotImplemented if res is NotImplemented else res >= 0
    def __gt__(self, other):
        res = self.compare(other)
        return NotImplemented if res is NotImplemented else res > 0
    def __str__(self) -> str:
        return f"BoolHybridArr([{','.join(map(str,self))}])"

    def __reversed__(self):
        if not self:return BHA_Iterator([])
        return BHA_Iterator(map(self.__getitem__,range(self.size-1,-1,-1)))

    def __deepcopy__(self, memo):
        return BoolHybridArr(self, hash_ = False)

    def insert(self, key: int, value) -> None:
        value = bool(value)
        key = key if key >= 0 else key + self.size
        key = max(0, min(key, self.size))
        if key <= self.split_index:
            self.small.insert(key, value)
            old_split = self.split_index
            self.split_index = min(self.split_index + 1, len(self.small) - 1, max(0, self.size))
            for i in range(len(self.large)):
                self.large[i] += 1
        else:
            pos = bisect.bisect_left(self.large, key)
            for i in range(pos, len(self.large)):
                self.large[i] += 1
            if (self.is_sparse and value) or (not self.is_sparse and not value):
                self.large.insert(pos, key)
        self.size += 1

    def __len__(self) -> int:
        return int(self.size)

    def __iter__(self):
        if not self:return BHA_Iterator([])
        return BHA_Iterator(map(self.__getitem__,itertools.takewhile(lambda x: x < self.size, itertools.count(0))))

    def __contains__(self, value:Any) -> bool:
        if not (value == True or value == False): return False
        if not self.size:return False
        for i in range(30):
            if self.small[random.randrange(0,self.small.size)] == value:
                return True
        b = (1 for i in range(self.small.size+1>>1) if value==self.small[i] or value==self.small[self.small.size+~i])
        if value == self.is_sparse:
            return self.large or any(b)
        else:
            return (len(self.large) == self.size+~self.split_index and self.large) or any(b)
    def __bool__(self) -> bool:
        return bool(self.size)

    def __any__(self):
        return True in self

    def __all__(self):
        return False not in self

    def __eq__(self, other) -> bool:
        if not isinstance(other, Iterable):
            return NotImplemented
        if hasattr(other, '__len__'):
            if len(self) != len(other):
                return False
            return all(map(operator.eq, self, other))
        it0 = iter(other)
        if isinstance(it0, BHA_Iterator):
            it0 = it0.data
        a, b = itertools.tee(it0, 2)
        if len(self) != sum(1 for _ in a):
            return False
        return all(map(operator.eq, self, b))

    def __ne__(self, other) -> bool:
        return not self == other

    def __and__(self, other) -> BoolHybridArray:
        if type(other) == int:
            other = abs(other)
            other = map(int,f"{other:0{self.size}b}")
        if isinstance(other, (Iterator, Generator, map)) and not isinstance(other, (BHA_Iterator, BoolHybridArray)):
            other = BHA_Iterator(other)
        if len(self) != len(other):
            raise ValueError(f"与运算要求数组长度相同（{len(self)} vs {len(other)}）")
        return BoolHybridArr(map(operator.and_, self, other),hash_ = self.hash_)

    def __int__(self):
        if not self.size:
            return 0
        return reduce(lambda acc, val: operator.or_(operator.lshift(acc, 1), int(val)),self,0)

    def __index__(self):
        return int(self)

    def __or__(self, other:Iterable) -> BoolHybridArray:
        if type(other) == int:
            other = abs(other)
            other = map(int,f"{other:0{self.size}b}")
        if isinstance(other, (Iterator, Generator, map)) and not isinstance(other, (BHA_Iterator, BoolHybridArray)):
            other = BHA_Iterator(other)
        if len(self) != len(other):
            raise ValueError(f"或运算要求数组长度相同（{len(self)} vs {len(other)}）")
        return BoolHybridArr(map(operator.or_, self, other),hash_ = self.hash_)
    def __ror__(self, other:Iterable) -> BoolHybridArray:
        return self | other

    def __rshift__(self, other:int) -> BoolHybridArray:
        arr = BoolHybridArr(self)
        arr >>= other
        return arr

    def __irshift__(self, other:int) -> BoolHybridArray:
        if int(other) < 0:
            self <<= -other
            return self
        for i in range(int(other)):
            if self.size < 1:
                return self
            self.pop(-1)
        return self

    def __ilshift__(self ,other:int) -> BoolHybridArray:
        if int(other) < 0:
            self >>= -other
            return self
        if not self.is_sparse:
            self += FalsesArray(int(other), hash_=False)
        else:
            self.size += int(other)
        return self

    def __lshift__(self ,other:int) -> BoolHybridArray:
        if int(other) < 0:
            return self >> -other
        return self+FalsesArray(int(other))

    def __add__(self, other:Iterable) -> BoolHybridArray:
        arr = self.copy()
        arr += other
        return arr

    def __rand__(self, other:Iterable) -> BoolHybridArray:
        return self & other

    def __xor__(self, other:Iterable) -> BoolHybridArray:
        if type(other) == int:
            other = abs(other)
            other = map(int,f"{other:0{self.size}b}")
        if isinstance(other, (Iterator, Generator, map)) and not isinstance(other, (BHA_Iterator, BoolHybridArray)):
            other = BHA_Iterator(other)
        if len(self) != len(other):
            raise ValueError(f"异或运算要求数组长度相同（{len(self)} vs {len(other)}）")
        return BoolHybridArr(map(operator.xor, self, other),hash_ = self.hash_)

    def __rxor__(self, other:Iterable) -> BoolHybridArray:
        return self^other

    def __invert__(self:Iterable) -> BoolHybridArray:
        return BoolHybridArr(not a for a in self)

    def copy(self) -> BoolHybridArray:
        arr = BoolHybridArray(hash_ = False)
        arr.large,arr.small,arr.split_index,arr.is_sparse,arr.Type,arr.size = (array.array(self.large.typecode, self.large),self.small.copy(),
        self.split_index,BHA_Bool(self.is_sparse),self.Type,self.size)
        arr.hash_ = self.hash_
        if self.hash_:
            arr._cached_hash = self._cached_hash
            hybrid_array_cache[arr] = self._cached_hash
        return arr

    def view(self):
        tmp = TruesArray(0)
        tmp.__dict__ = self.__dict__
        return tmp

    def __copy__(self) -> BoolHybridArray:
        return self.copy()

    @staticmethod
    def _add(a, b):
        bits, carry = [], 0
        for x, y in itertools.zip_longest(reversed(a), reversed(b), fillvalue=0):
            s = int(x) + int(y) + carry
            bits.append(s & 1)
            carry = s >> 1
        if carry:
            bits.append(1)
        bits.reverse()
        return BoolHybridArr(bits)

    @staticmethod
    def _sub(a, b):
        bits, borrow = [], 0
        for x, y in itertools.zip_longest(reversed(a), reversed(b), fillvalue=0):
            d = int(x) - int(y) - borrow
            borrow = d < 0
            bits.append(d + 2 if borrow else d)
        bits.reverse()
        i = 0
        while i < len(bits) and bits[i] == 0:
            i += 1
        return BoolHybridArr(bits[i:])

    @staticmethod
    def _strip_leading_zeros(x):
        """去掉前导零；全零返回空数组（0 的规范表示）。"""
        bs = BoolHybridArr(x)
        i = 0
        while i < len(bs) and bs[i] == 0:
            i += 1
        return BoolHybridArr(bs[i:])

    @staticmethod
    def _div(a, b):
        """二进制长除法：返回 a // b（商），要求 b != 0 且隐式 a >= 0。"""
        if int(b) == 0:
            raise ZeroDivisionError("真整除：除数为 0")
        quotient = BoolHybridArr([])
        rem = BoolHybridArr([])
        for bit in a:
            # rem = rem * 2 + bit（末尾接一个 bit）；每步都规范化，去掉前导零，
            # 否则 rem 会从空值 0 开始越拼越长（[0]、[0,1]、[0,1,0]...），
            # 带前导零的中间余数会让 >= 比较判错。
            rem = BoolHybridArray._strip_leading_zeros(rem + BoolHybridArr([bool(bit)]))
            if rem >= b:
                rem = BoolHybridArray._strip_leading_zeros(BoolHybridArray._sub(rem, b))
                quotient.append(1)
            else:
                quotient.append(0)
        i = 0
        while i < len(quotient) and quotient[i] == 0:
            i += 1
        return BoolHybridArr(quotient[i:])

    @staticmethod
    def _as_bits(x):
        if isinstance(x, BoolHybridArray):
            return x
        if isinstance(x, int):
            if x < 0:
                raise ValueError("真运算暂不支持负数")
            return BoolHybridArr([int(c) for c in bin(x)[2:]]) if x > 0 else BoolHybridArr([])
        return BoolHybridArr(x)

    def add(self, other):
        return self._add(self, self._as_bits(other))

    def sub(self, other):
        return self._sub(self, self._as_bits(other))

    def div(self, other):
        return self._div(self, self._as_bits(other))

    def __mul__(self, arr2):
        if isinstance(arr2, int):
            n = arr2
            if n <= 0:
                return BoolHybridArr([])
            res = BoolHybridArr([])
            base = self.copy()
            while n:
                if n & 1:
                    res += base
                base = base + base
                n >>= 1
            return res
        len1, len2 = len(self), len(arr2)

        if len1 < 64 or len2 < 64:
            result = FalsesArray(len1 + len2, hash_=False)
            for i in range(len1 - 1, -1, -1):
                if not self[i]:
                    continue
                carry = 0
                for j in range(len2 - 1, -1, -1):
                    k = i + j + 1
                    s = int(result[k]) + int(arr2[j]) + carry
                    result[k] = s & 1
                    carry = s >> 1
                k = i
                while carry:
                    s = int(result[k]) + carry
                    result[k] = s & 1
                    carry = s >> 1
                    k -= 1
            i = 0
            while i < len(result) - 1 and not result[i]:
                i += 1
            return result[i:]

        m = max(len1, len2) >> 1
        low1 = self[len1 - m:] if len1 > m else self
        high1 = self[:len1 - m] if len1 > m else FalsesArray(1)
        low2 = arr2[len2 - m:] if len2 > m else arr2
        high2 = arr2[:len2 - m] if len2 > m else FalsesArray(1)

        z0 = low1 * low2
        z2 = high1 * high2
        z1 = self._sub(self._sub(self._add(low1, high1) * self._add(low2, high2), z0), z2)

        return self._add(self._add(z2 << (m << 1), z1 << m), z0)

    def __rmul__(self, other):
        if isinstance(other, int):
            return self * other
        return NotImplemented

    def find(self,value):
        from .int_array import IntHybridArray
        return IntHybridArray(i for i in range(len(self)) if self[i]==value)
    def extend(self, iterable:Iterable) -> None:
        if isinstance(iterable, (Iterator, Generator, map)):
            iterable,copy = itertools.tee(iterable, 2)
            len_ = sum(1 for _ in copy)
        else:
            len_ = len(iterable)
        old_size = self.size
        self.size += len_
        for i,j in zip(range(len_),iterable):
            self[old_size + i] = j

    def append(self,v):
        self.size += 1
        self[-1] = v

    def swap(self, idx1, idx2):
        """交换两个元素（bool 单值，无编解码成本）。"""
        n = self.size
        if idx1 < 0:
            idx1 += n
        if idx2 < 0:
            idx2 += n
        if not (0 <= idx1 < n and 0 <= idx2 < n):
            raise IndexError("swap index out of range")
        if idx1 == idx2:
            return
        self[idx1], self[idx2] = self[idx2], self[idx1]

    def move(self, idx1, length, idx2):
        """memmove 式：把 [idx1, idx1+length) 移到 [idx2, idx2+length)，长度不变，重叠安全。"""
        n = self.size
        if idx1 < 0:
            idx1 += n
        if idx2 < 0:
            idx2 += n
        idx1 = max(0, min(idx1, n))
        length = max(0, min(length, n - idx1))
        if length == 0:
            return
        idx2 = max(0, min(idx2, n - length))
        if idx2 == idx1:
            return
        # small 区内：批量位搬移（一次向量化），避免逐元素 pop/insert
        if idx1 + length <= self.split_index + 1 and idx2 + length <= self.split_index + 1:
            sm = self.small
            chunk = np.unpackbits(sm.data, bitorder='little')[:sm.size][idx1:idx1 + length].copy()
            sm._del_range(idx1, length)
            sm._ins_range(idx2, length)
            cptr = sm._get_cptr()
            for i, v in enumerate(chunk):
                sm._set_single(idx2 + i, bool(v), cptr)
            return
        chunk = self[idx1:idx1 + length]
        del self[idx1:idx1 + length]
        self[idx2:idx2] = chunk

    push = append
    peek = __getitem__
    top = property(peek)
    front = property(lambda self:self[0])
    rear = top
    enqueue = push

    def index(self, value, start=0, stop=None) -> int:
        if self.size == 0:
            raise ValueError('无法在空的 BoolHybridArray 中查找元素！')
        value = bool(value)
        n = self.size
        if stop is None:
            stop = n
        start = max(0, start if start >= 0 else start + n)
        stop = min(n, stop if stop >= 0 else stop + n)
        for i in range(start, stop):
            if self[i] == value:
                return i
        raise ValueError(f"{value} not in BoolHybridArray")
    def rindex(self, value) -> int:
        if self.size == 0:
            raise ValueError('无法在空的 BoolHybridArray 中查找元素！')
        value = bool(value)
        x = 'not find'
        for i in range(self.size):
            if self[~i] == value:
                return self.size + ~i
            if self[i] == value:
                x = i
            if len(self)-i <= i:
                break
        if x != 'not find':
            return x
        raise ValueError(f"{value} not in BoolHybridArray")

    def count(self, value) -> int:
        value = bool(value)
        if not self.size: return 0
        scan_n = min(self.split_index + 1, self.size)
        c = 0
        if scan_n > 0:
            for i in range(scan_n):
                if self.small[i] == value:
                    c += 1
        if value == (not self.is_sparse):
            c += max(0, self.size - self.split_index - 1 - len(self.large))
        else:
            c += len(self.large)
        return c

    def optimize(self,*a,**k) -> BoolHybridArray:
        arr = BoolHybridArr(self,*a,**k)
        self.large,self.small,self.split_index,self.is_sparse = (arr.large,arr.small,
        arr.split_index,arr.is_sparse)
        gc.collect()
        return self

    def memory_usage(self, detail=False) -> dict | int:
        small_mem = (self.small.size >> 3) + 96
        large_mem = (len(self.large) << 2) + 40
        equivalent_list_mem = 40 + (self.size << 3)
        equivalent_numpy_mem = 96 + self.size
        total = small_mem + large_mem
        if not detail:
            return total
        need_optimize = False
        optimize_reason = ""
        n = self.size
        if n <= 0:
            return {
                "总占用(字节)": total,
                "密集区占用": small_mem,
                "稀疏区占用": large_mem,
                "对比原生list节省": "N/A",
                "对比numpy节省": "N/A",
                "是否需要优化": "否",
                "优化理由/说明": "数组为空"
            }
        sparse_size = n - self.split_index - 1
        dense_size = self.split_index + 1
        entry_bytes = 4 if n < (1 << 32) else 8
        if sparse_size > 0 and large_mem >= (sparse_size >> 3) + 96:
            need_optimize = True
            optimize_reason = "稀疏区索引密度过高，优化后可转为密集存储提升速度"
        sampled_total = 0
        dense_density = 0.5
        if not need_optimize and dense_size >= 16:
            win_sz = min(256, dense_size)
            max_points = 1024
            n_win = max(1, max_points // win_sz)
            step = max(1, dense_size // n_win)
            sampled_true = 0
            sampled_total = 0
            for start in range(0, dense_size - win_sz + 1, step):
                for i in range(start, start + win_sz):
                    if self.small[i]:
                        sampled_true += 1
                sampled_total += win_sz
                if sampled_total >= max_points:
                    break
            dense_density = sampled_true / sampled_total if sampled_total > 0 else 0.5
            minority_ratio = min(dense_density, 1.0 - dense_density)
            minority_count = int(minority_ratio * dense_size)
            minority_cost = minority_count * entry_bytes + 40
            if minority_cost <= small_mem:
                need_optimize = True
                optimize_reason = "密集区有效值占比过低，优化后可转为稀疏存储节省内存"
        if not need_optimize and n < 32 and total > n:
            need_optimize = True
            optimize_reason = "小尺寸数组存储冗余，优化后将用int位存储进一步省内存"
        if not need_optimize and sparse_size >= 16 and dense_size > 0:
            if self.is_sparse:
                intruder_ratio = 1.0 - (len(self.large) / sparse_size if sparse_size > 0 else 0)
            else:
                intruder_ratio = len(self.large) / sparse_size if sparse_size > 0 else 0
            if sampled_total > 0:
                dense_minority_ratio = min(dense_density, 1.0 - dense_density)
            else:
                dense_minority_ratio = 0.5
            if intruder_ratio > 0.3 and dense_minority_ratio > 0.3:
                need_optimize = True
                optimize_reason = "密集区有效值占比过低，优化后可转为稀疏存储节省内存"

        if not need_optimize:
            optimize_reason = "当前存储模式已适配数据特征，无需优化"

        return {
            "总占用(字节)": total,
            "密集区占用": small_mem,
            "稀疏区占用": large_mem,
            "对比原生list节省": f"{min((1 - total / equivalent_list_mem) * 100, 99.999999):.6f}%",
            "对比numpy节省": f"{min((1 - total / equivalent_numpy_mem) * 100, 99.999999):.6f}%" if equivalent_numpy_mem > 0 else "N/A",
            "是否需要优化": "是" if need_optimize else "否",
            "优化理由/说明": optimize_reason
        }
    def __reduce__(self):
        return BoolHybridArr,((self.large, self.small, self.split_index, self.is_sparse, self.Type, self.hash_, self.size),)
class BoolHybridArr(BoolHybridArray,metaclass=ResurrectMeta):
    __module__ = 'bool_hybrid_array'
    def __new__(cls, lst: Iterable = (), is_sparse=None, Type = None, hash_ = True, split_index = None) -> BoolHybridArray:
        if isinstance(lst,tuple) and len(lst)==7 and isinstance(lst[0],array.array) and isinstance(lst[1],(BoolHybridArray._CompactBoolArray,np.ndarray)):
            arr = TruesArray(0)
            arr.large,arr.small,arr.split_index,arr.is_sparse,arr.Type,arr.hash_,arr.size = lst
            return arr
        a = isinstance(lst, (Iterator, Generator, map)) and not isinstance(lst, BoolHybridArray)
        if a:
            values = array.array('b')
            true_pos = array.array('I')
            false_pos = array.array('I')
            size = 0
            true_count = 0
            for i, val in enumerate(lst):
                b = 1 if val else 0
                values.append(b)
                size += 1
                if b:
                    true_count += 1
                    true_pos.append(i)
                else:
                    false_pos.append(i)
        else:
            size = len(lst)
            true_count = sum(bool(val) for val in lst)
        if not size:
            return BoolHybridArray(0, 0, is_sparse=False if is_sparse is None else is_sparse, hash_=hash_)
        if split_index is None:
            C = 4 if size < (1 << 32) else 8
            running_true = 0
            min_cost = float('inf')
            best_split = 0
            best_is_sparse = is_sparse
            val_iter = iter(values) if a else iter(lst)
            for s, val in enumerate(val_iter):
                small_cost = s + 7 >> 3
                seg_true = true_count - running_true - bool(val)
                seg_len = size - 1 - s
                seg_false = seg_len - seg_true
                if is_sparse is None:
                    cost_sparse_true = small_cost + seg_true * C
                    cost_sparse_false = small_cost + seg_false * C
                    if cost_sparse_true <= cost_sparse_false:
                        cur_cost = cost_sparse_true
                        cur_is_sparse = True
                    else:
                        cur_cost = cost_sparse_false
                        cur_is_sparse = False
                else:
                    cur_cost = small_cost + (seg_true * C if is_sparse else seg_false * C)
                    cur_is_sparse = is_sparse
                if cur_cost < min_cost:
                    min_cost = cur_cost
                    best_split = s
                    best_is_sparse = cur_is_sparse
                running_true += bool(val)
            split_index = best_split
            if is_sparse is None:
                is_sparse = best_is_sparse
        elif is_sparse is None:
            is_sparse = true_count <= (size - true_count)
        arr = BoolHybridArray(split_index = split_index, size = size, is_sparse = is_sparse, Type = Type, hash_ = F)
        small_max_idx = min(split_index, size - 1)
        if a:
            if small_max_idx >= 0:
                arr.small[:small_max_idx + 1] = values[:small_max_idx + 1]
            if size >= 1 << 32:
                true_pos = array.array('Q', true_pos)
                false_pos = array.array('Q', false_pos)
            if is_sparse:
                arr.large.extend(true_pos[bisect.bisect_right(true_pos, split_index):])
            else:
                arr.large.extend(false_pos[bisect.bisect_right(false_pos, split_index):])
        else:
            if small_max_idx >= 0:
                arr.small[:small_max_idx + 1] = map(bool, itertools.islice(lst, small_max_idx + 1))
            large_indices = (
                i for i in range(split_index + 1, size)
                if (is_sparse and bool(lst[i])) or (not is_sparse and not bool(lst[i]))
            )
            arr.large.extend(large_indices)
        arr.large = sorted(arr.large)
        type_ = 'I' if size < 1 << 32 else 'Q'
        arr.large = array.array(type_, arr.large) if size < 1 << 64 else list(arr.large)
        if hash_:
            while True:
                try:
                    for existing_array, existing_hash in hybrid_array_cache.items():
                        try:
                            if arr.size != existing_array.size:
                                continue
                            elif arr == existing_array:
                                arr._cached_hash = existing_hash
                                return arr
                        except Exception:
                            continue
                    break
                except RuntimeError:
                    continue
        arr._cached_hash = id(arr)
        if hash_:
            hybrid_array_cache[arr] = arr._cached_hash
        return arr

def TruesArray(size, Type = None, hash_ = True):
    size = operator.index(size)
    if size < 0:
        raise ValueError(f"size 必须大于等于 0，收到 {size}")
    split_index = min(size >> 4, math.isqrt(size))
    split_index = max(split_index, 1)
    split_index = int(split_index) if split_index < 150e+7*2 else int(145e+7*2)
    return BoolHybridArray(split_index,size,Type = Type,hash_ = hash_)
def FalsesArray(size, Type = None,hash_ = True):
    size = operator.index(size)
    if size < 0:
        raise ValueError(f"size 必须大于等于 0，收到 {size}")
    split_index = min(size >> 4, math.isqrt(size))
    split_index = max(split_index, 1)
    split_index = int(split_index) if split_index < 150e+7*2 else int(145e+7*2)
    return BoolHybridArray(split_index,size,True,Type = Type,hash_ = hash_)
Bool_Array = np.arange(2,dtype = np.uint8)
class BHA_bool(int,metaclass=ResurrectMeta):
    __module__ = 'bool_hybrid_array'
    @lru_cache
    def __new__(cls, value):
        core_value = bool(value)
        instance = super().__new__(cls, core_value)
        instance.data = Bool_Array[1] if core_value else Bool_Array[0]
        instance.value = core_value
        return instance
    @lru_cache
    def __str__(self):
        return 'True' if self else 'False'
    @lru_cache
    def __repr__(self):
        return 'T' if self else 'F'
    @lru_cache
    def __bool__(self):
        return self.value
    @lru_cache
    def __int__(self):
        return int(self.data)
    @lru_cache
    def __or__(self,other):
        return BHA_Bool(self.value|other)
    @lru_cache
    def __and__(self,other):
        return BHA_Bool(self.value&other)
    @lru_cache
    def __xor__(self,other):
        return BHA_Bool(self.value^other)
    def __hash__(self):
        return hash(self.data)
    def __len__(self):
        raise TypeError("'BHA_bool' object has no attribute '__len__'")
    __rand__,__ror__,__rxor__ = __and__,__or__,__xor__
T,F = BHA_bool(1),BHA_bool(0)
class BHA_Bool(BHA_bool,metaclass=ResurrectMeta):
    __module__ = 'bool_hybrid_array'
    @lru_cache
    def __new__(cls,v):
        return T if v else F
class BHA_List(list,metaclass=ResurrectMeta):
    __module__ = 'bool_hybrid_array'
    def __init__(self, arr=()):
        from .float_array import FloatHybridArray
        def Temp(v):
            if isinstance(v,(list,tuple)):
                v = (BoolHybridArr(v) if all(isinstance(i,
                    (bool,BHA_bool,np.bool_)) for i in v)
                     else BHA_List(v))
            if isinstance(v,(BoolHybridArray,FloatHybridArray)):
                return v
            elif isinstance(v,(bool,np.bool_)):
                return BHA_Bool(v)
            else:
                return v
        super().__init__(map(Temp,arr))
        try:self.hash_value = sum(map(hash,self))
        except Exception:self.hash_value = 0
    def __hash__(self):
        return self.hash_value
    def __call__(self, func):
        func.self = self
        def wrapper(*args, **kwargs):
            return func(self, *args, **kwargs)
        setattr(self, func.__name__, wrapper)
        return func
    def __str__(self):
        def Temp(v):
            if isinstance(v,(BoolHybridArray,np.ndarray,BHA_List,array.array)):
                return str(v)+',\n'
            else:
                return repr(v)+','
        return f"BHA_List([\n{''.join(map(Temp,self))}])"
    def __repr__(self):
        return str(self)
    def __or__(self,other):
        return BHA_List(map(operator.or_, self, other))
    def __reduce__(self):
        return (BHA_List, (list(self),))
    def __and__(self,other):
        return BHA_List(map(operator.and_, self, other))
    def __xor__(self,other):
        return BHA_List(map(operator.xor, self, other))
    def __rxor__(self,other):
        return self^other
    def __ror__(self,other):
        return self|other
    def __rand__(self,other):
        return self&other
    def optimize(self):
        for val in self:
            val.optimize()
    def memory_usage(self,detail=False):
        total = sum(val.memory_usage() for val in self) + 32
        if not detail:
            return total
        else:
            temp = sum(val.size for val in self)
            return {
            "占用(字节)": total,
            "对比原生list节省": f"{(1 - total / (temp * 8 + 40))*100:.6f}%",
            "对比numpy节省": f"{(1 - total / (temp + 96)) * 100:.6f}%"}
    def __iter__(self):
        return BHA_Iterator(super().__iter__())
    def to_ascii_art(self, width=20):
        art = '\n'.join([' '.join(['■' if j else ' '  for j in i]) for i in self])
        return art
    def save(self,path,*a,**k):return Create_BHA(path,self,*a,**k)
    @classmethod
    def load(path,*a,**k):return Ask_BHA(path,*a,**k)
class BHA_Iterator(Iterator,metaclass=ResurrectMeta):
    __module__ = 'bool_hybrid_array'
    def __init__(self,data):
        if isinstance(data, BHA_Iterator):
            self.data, data.data, self.copy_data = itertools.tee(data.data, 3)
        else:
            itd = iter(data)
            if isinstance(itd, BHA_Iterator):
                self.data, self.copy_data = itertools.tee(itd.data, 2)
            else:
                self.data, self.copy_data = itertools.tee(itd, 2)
    def __len__(self):
        self.copy_data, it = itertools.tee(self.copy_data, 2)
        return sum(1 for _ in it)
    def __next__(self):
        try:
            return next(self.data)
        except StopIteration:
            self.data, self.copy_data = itertools.tee(self.copy_data, 2)
            raise
    def __iter__(self):
        return self
    def __or__(self,other):
        return BHA_Iterator(map(operator.or_, self, other))
    def __and__(self,other):
        return BHA_Iterator(map(operator.and_, self, other))
    def __xor__(self,other):
        return BHA_Iterator(map(operator.xor, self, other))
    def __array__(self,dtype = None,copy = None):
        arr = np.fromiter(self, dtype=dtype)
        return arr.copy() if copy else arr.view()
    __rand__,__ror__,__rxor__ = __and__,__or__,__xor__
class BHA_string(metaclass = ResurrectMeta):
    def __init__(self, data: str | bytes | bytearray = ""):
        if isinstance(data, str):
            self._buf = bytearray(data.encode("utf-8"))
        elif isinstance(data, (bytes, bytearray)):
            self._buf = bytearray(data)
        else:
            raise TypeError("BHA_string only accept str / bytes / bytearray")

    def __str__(self) -> str:
        return self._buf.decode("utf-8", errors="replace")

    def __repr__(self) -> str:
        return f'BHA_string({str(self)!r})'

    def __eq__(self, other) -> bool:
        if isinstance(other, BHA_string):
            return self._buf == other._buf
        if isinstance(other, str):
            return self._buf == bytearray(other.encode("utf-8"))
        if isinstance(other, (bytes, bytearray)):
            return self._buf == bytearray(other)
        return NotImplemented

    def __ne__(self, other) -> bool:
        r = self.__eq__(other)
        if r is NotImplemented:
            return r
        return not r

    def _coerce(self, other):
        if isinstance(other, BHA_string):
            return bytes(other._buf)
        if isinstance(other, str):
            return other.encode("utf-8")
        if isinstance(other, (bytes, bytearray)):
            return bytes(other)
        return NotImplemented

    def __lt__(self, other) -> bool:
        o = self._coerce(other)
        if o is NotImplemented:
            return NotImplemented
        return bytes(self._buf) < o

    def __le__(self, other) -> bool:
        o = self._coerce(other)
        if o is NotImplemented:
            return NotImplemented
        return bytes(self._buf) <= o

    def __gt__(self, other) -> bool:
        o = self._coerce(other)
        if o is NotImplemented:
            return NotImplemented
        return bytes(self._buf) > o

    def __ge__(self, other) -> bool:
        o = self._coerce(other)
        if o is NotImplemented:
            return NotImplemented
        return bytes(self._buf) >= o

    def __hash__(self) -> int:
        return hash(bytes(self._buf))

    def __len__(self) -> int:
        return len(self._buf)

    def __getitem__(self, idx: int | slice) -> int | bytearray:
        return self._buf[idx]

    def __setitem__(self, idx: int, val: int):
        self._buf[idx] = val

    def __contains__(self, sub: str | bytes | bytearray | "BHA_string") -> bool:
        if isinstance(sub, BHA_string):
            target = sub._buf
        elif isinstance(sub, str):
            target = sub.encode("utf-8")
        elif isinstance(sub, (bytes, bytearray)):
            target = sub
        else:
            raise TypeError("in support str/bytes/bytearray/BHA_string")
        return target in self._buf

    def __cin__(self, stream) -> None:
        self._buf = bytearray(stream.getline().encode("utf-8"))

    def write(self, s: str | bytes | bytearray | "BHA_string") -> int:
        if isinstance(s, BHA_string):
            raw = s._buf
        elif isinstance(s, str):
            raw = s.encode("utf-8")
        elif isinstance(s, (bytes, bytearray)):
            raw = s
        else:
            raise TypeError("write supports str/bytes/bytearray/BHA_string")
        self._buf.extend(raw)
        return len(raw)
    def __add__(self, other: str | bytes | bytearray | "BHA_string") -> "BHA_string":
        temp = bytearray(self._buf)
        if isinstance(other, BHA_string):
            temp.extend(other._buf)
        elif isinstance(other, str):
            temp.extend(other.encode("utf-8"))
        elif isinstance(other, (bytes, bytearray)):
            temp.extend(other)
        else:
            raise TypeError
        return BHA_string(temp)
    def __iadd__(self, other: str | bytes | bytearray | "BHA_string") -> "BHA_string":
        if isinstance(other, BHA_string):
            self._buf.extend(other._buf)
        elif isinstance(other, str):
            self._buf.extend(other.encode("utf-8"))
        elif isinstance(other, (bytes, bytearray)):
            self._buf.extend(other)
        else:
            raise TypeError
        return self
    def __cin__(self,stream = None) -> None:
        if stream == None:line = sys.stdin.readline()
        else:line = stream.getline()
        self._buf.clear()
        self.write(line.rstrip("\r\n").rstrip("\n"))
    def __iter__(self):
        return BHA_Iterator(iter(self._buf))
M = (1 << 2281) - 1

E1, E2, E3, E4, E5 = 11, 13, 17, 19, 23
E6, E7, E8, E9, E10 = 29, 31, 37, 41, 43

IV_R = 0x2957A2F168CC3509
IV_C = 0x71D39E40BB72A61F
C1 = 0x19260817
C2 = 0x114514
C3 = 0xABCDEF
C4 = 0x233333
C5 = 0x666666
C6 = 0x123456789

def fast_pow(x : int, e : int):
    return pow(x, e, M)

def tenth_order_mapping(x : int):
    x %= M
    x = (fast_pow(x, 210) + fast_pow(210, x) + fast_pow(x, x) - 1) & M
    x = fast_pow(x, E1) ^ C1
    x = (fast_pow(x, E2) + C2) & M
    x_shr = (x >> 18) & M
    x_shl = (x << 9) & M
    x = fast_pow(x, E3) ^ x_shr ^ x_shl
    x = (fast_pow(x, E4) * C3) & M
    x = fast_pow(x, E5) ^ ((x << 21) & M)
    x = fast_pow(x, E6) ^ C4
    x = (fast_pow(x, E7) - C6) & M
    x_s12 = (x >> 12) & M
    x_s15 = (x << 15) & M
    x = fast_pow(x, E8) ^ (x_s12 & x_s15)
    x = (fast_pow(x, E9) * C6) & M
    x = fast_pow(x, E10) ^ ((x << 33) & M)
    return x % M

class UltraMersenneFractalSponge(metaclass =  ResurrectMeta):
    __slots__ = ('r','c','total_len','data_pool','_bts')
    def __init__(self,data = None):
        self.r = IV_R
        self.c = IV_C
        self.total_len = 0
        self.data_pool = []
        self._bts = data
    def absorb(self, data: bytes):
        if not data:
            return self
        self.total_len += len(data)
        step = len(data) // len(data).bit_length()
        for i in range(0, len(data), step):
            chunk = data[i:i+step]
            num = int.from_bytes(chunk, "big")
            self.data_pool.append(num)
            self.r = tenth_order_mapping(self.r^num)
            term = (pow(num, 7, M) * self.r) % M
            self.c = (self.c ^ self.r + term) % M
        return self
    def update(self,bts):
        self._bts += bts
    def digest(self,*a,**k):
        return bytes.fromhex(self.hexdigest(*a,**k))
    def _fold_recursive(self, arr):
        if len(arr) <= 2:
            res = 0
            for v in arr:
                res = (res + tenth_order_mapping(v ^ res)) % M
            return res
        mid = len(arr) >> 1
        left = self._fold_recursive(arr[:mid])
        right = self._fold_recursive(arr[mid:])
        l3 = pow(left, 3, M)
        r3 = pow(right, 3, M)
        cross = (left * right ^ l3 + r3) % M
        return tenth_order_mapping(cross)
    def hexdigest(self,bitn = 256):
        if self._bts:
            self.absorb(self._bts)
            self._bts = None
        if bitn > 4562:
            s = ""
            while bitn >= 4096:
                s += self.hexdigest(bitn = 4096)
                bitn -= 4096
            s = self.hexdigest(bitn = bitn) + s
            return s
        len3 = pow(self.total_len, 3, M)
        self.r ^= len3
        self.c = (self.c + len3 * self.r) % M

        fold_val = self._fold_recursive(self.data_pool)
        self.r = (self.r ^ fold_val) % M
        for _ in range(10):
            self.r = tenth_order_mapping(self.r)
            self.c = tenth_order_mapping(self.c)
            r3 = pow(self.r, 3, M)
            c3 = pow(self.c, 3, M)
            cross = (r3 ^ c3 + self.r * self.c) % M
            self.r, self.c = cross % M, (cross ^ self.r) % M
        res = (self.r << max(0,bitn - 2281)) ^ self.c
        mask = (1 << bitn) - 1
        return f"{res & mask:0{bitn + 3 >> 2}x}"
    squeeze = hexdigest
umfs = UltraMersenneFractalSponge
def _real_generator(in_q,out_q):
    pid = os.getpid()
    tid = threading.get_ident()
    mem_addr = id(object())
    dynamic_data = f"{pid}_{tid}_{mem_addr}"
    raw_seed = time.perf_counter()
    sys_info = (sys.version + platform.machine()
    + platform.processor() + str(os.cpu_count()))
    mix_seed = (
    str(raw_seed) + sys_info + dynamic_data + os.urandom(8).hex())
    h1 = umfs(mix_seed.encode()).digest()
    h2 = hashlib.md5(h1.hex().encode()).digest()
    mt_seed = int.from_bytes(h2, byteorder='big')
    __mt_state = array.array('I',[0] * 624)
    __mt_state[0] = mt_seed & 0xFFFFFFFF
    for i in range(1, 624):
        __mt_state[i] = (1812433253 * (__mt_state[i-1] ^
        (__mt_state[i-1] >> 30)) + i) & 0xFFFFFFFF
    __mt_index = 0
    while in_q.get() == "next":
        if __mt_index >= 624:
            for i in range(624):
                y = ((__mt_state[i] & 0x80000000) +
                (__mt_state[(i+1)%624] & 0x7FFFFFFF))
                __mt_state[i] = __mt_state[(i+397)%624] ^ (y >> 1)
                if y & 1:
                    __mt_state[i] ^= 0x9908B0DF
                    __mt_state[i] += (
                        int.from_bytes(os.urandom(1),'big')&0xFFFFFFFF)
            __mt_index = 0
        y = __mt_state[__mt_index]
        __mt_index += 1
        y ^= (y >> 11)
        y ^= (y << 7) & 0x9D2C5680
        y ^= (y << 15) & 0xEFC60000
        y ^= (y >> 18)
        xor_result = y
        for i in range(1, 25):
            idx = (__mt_index + i) % 624
            xor_result ^= __mt_state[idx]
        h3 = hashlib.sha3_512(str(xor_result).encode('utf-8')).digest()
        final = hashlib.md5(h3).hexdigest()
        out_q.put(final)
@lru_cache(None,False)
def create_mt_xor25_generator():
    """
    MT-XOR25 永久密钥使用规范

    1. 私钥生成：
    在用户本地设备初始化`mt_xor25`实例，使用
    umfs(bytes(f"{rng.getrandbits(256):032x}")).digest(bitn = 2048)
    作为Ed25519私钥种子；由该种子派生Ed25519私钥。私钥生成全程在本地完成，私钥本身永不外发。

    2. 公钥推导：
    由上一步生成的Ed25519私钥，直接推导对应的Ed25519公钥；公钥可上传至服务端用于验签，公钥仅用于身份校验，不能用于加密私钥。（官方推荐不加域分离前缀，也可以加）

    3. 身份验证：
    - 用户端：原始消息M，计算`umfs(M).digest(bitn = 1024)`，使用本地Ed25519私钥对该payload生成签名，POST提交服务端。bitn可以根据场景决定（bitn可以是128（简短）/256（默认）/1024（权衡）/2048/4096，也可以不是2的幂）
    - 服务端用：收到M、签名、公钥标识；取出数据库中该用户对应的公钥，对消息执行完全一致的umfs摘要，调用Ed25519验签函数。
    - 服务端用保存的公钥验证签名（对比哈希结果），匹配则身份验证通过。
    
    
    公钥加密规范（非强制但建议，泄漏了也没事）
    - 不要用 HTTP 协议传输公钥；
    - 不要在日志、明文存储（如 txt 文件）中记录公钥（如需存储，需加密后再存）；
    - 不要在非加密的通信渠道（如邮件、聊天软件）发送公钥。
    所有涉及公钥、私钥签名、验证信息的传输，必须用 POST 请求，不要用 GET
    
    
    私钥强制保密规则：
    1. 生成：仅在用户本地设备生成，绝不传输到任何服务器/第三方；
    2. 存储：仅加密存储在用户本地（如设备安全区、加密文件），禁止明文存储；
    3. 传输：绝对禁止通过任何渠道（HTTPS/邮件/聊天软件）传输私钥；
    4. 泄露后果：私钥一旦泄露，攻击者可完全冒充用户身份，且无法补救（只能重置私钥和公钥）。
    
    
    示例代码：
    
    from bool_hybrid_array import mt_xor25, umfs
    from cryptography.hazmat.primitives.asymmetric import ed25519
    rng = mt_xor25()
    sk_seed = umfs(bytes(f"{rng.getrandbits(256):032x}")).digest(bitn = 2048)
    private_key = ed25519.Ed25519PrivateKey.from_private_bytes(sk_seed)
    pub = private_key.public_key()
    msg = b"your data"
    msg_digest = umfs(msg).digest(bitn = 1024)
    sig = private_key.sign(msg_digest)
    pub.verify(sig, umfs(msg).digest(bitn = 1024)) #这里的bitn必须和msg_digest的完全一致
    """
 
    number = multiprocessing.cpu_count() << 1
    in_q = [Queue() for _ in range(number)]
    out_q = Queue()
    processes = []
    for i in range(number):
        p = multiprocessing.Process(target=_real_generator,
                                  args=(in_q[i], out_q), daemon=True)
        p.start()
        processes.append(p)
    class XOR25_Generator(metaclass = ResurrectMeta):
        def __call__(self) -> str:
            return next(it)
        def __iter__(self):
            while 1:
                yield from self.batch_generate(number)
        def __next__(self):
            return self()
        def batch_generate(self,n = 1):
            for i in range(n):
                in_q[i%len(in_q)].put("next")
            return BHA_Iterator(out_q.get() for i in range(n))
        def getrandbits(self, k: int) -> int:
            if k <= 0:
                raise ValueError("bits must be positive")
            res = 0
            rem = k
            need = (rem + 0x7F) >> 7
            for hx in self.batch_generate(need):
                chunk = int(hx, 16)
                take = rem if rem < 128 else 128
                shift = 128 - take
                res = (res << take) | (chunk >> shift)
                rem -= take
                if not rem:
                    break
            return res
        def uniform(self, low: float = 0.0, high: float = 1.0) -> float:
            from .float_array import BHA_Float
            r = self.getrandbits(1024)
            return low + (BHA_Float(high) - low) * r / (1 << 1024)
        def randrange(self, start, stop=None, step=1):
            if stop is None:
                stop, start = start, 0
            span = stop - start
            if span <= 0:
                raise ValueError("stop must be greater than start")
            cnt = ((span - 1) // step) + 1
            if cnt <= 0:
                raise ValueError("empty range")
            MAX_U128 = (1 << 128) - 1
            bias = MAX_U128 % cnt
            BATCH = 32
            while True:
                for hx in self.batch_generate(BATCH):
                    num = int(hx, 16)
                    if num + bias <= MAX_U128:
                        offset = num % cnt
                        return start + offset * step
        def randint(self, a, b):
            return self.randrange(a, b + 1)
    gen = XOR25_Generator()
    it = BHA_Iterator(iter(gen))
    return gen
mt_xor25 = create_mt_xor25_generator
try:from ._cppiostream import *
except:pass
def _bhax_is_bit_set(val) -> bool:
    s = str(val)
    return s == '1' or s == 'True' or val is True


def _bhax_decode_int_bits(bit_arr, bit_length: int, count: int) -> list:
    result = []
    for i in range(count):
        base = i * bit_length
        sign = 1 if _bhax_is_bit_set(bit_arr[base]) else 0
        val = 0
        for b in range(1, bit_length):
            if _bhax_is_bit_set(bit_arr[base + b]):
                val |= (1 << (b - 1))
        if sign:
            val = val - (1 << (bit_length - 1))
        result.append(val)
    return result


class BHAX_Descriptor(metaclass=ResurrectMeta):
    PIPE_SEP = "|"
    INNER_SDA = "data0.sda"
    FLOAT_END_SENTINEL = "@@END_FLOAT@@"

    def __new__(cls, path, *args, **kwargs):
        root = pathlib.Path(path)
        inst = super().__new__(cls)
        inst._root = root
        return inst

    def __init__(self, path):
        pass

    def _encode_1d(self, arr) -> list:
        from .int_array import IntHybridArray
        from .float_array import FloatHybridArray

        if isinstance(arr, IntHybridArray):
            total = len(arr)
            hex_total = f"{total:X}"
            hex_bitlen = f"{arr.bit_length:X}"
            b_view = arr.view()
            hex_data = Ask_arr(b_view).strip()
            line = self.PIPE_SEP.join(["int", hex_total, hex_bitlen, hex_data])
            return [line]
        elif isinstance(arr, BoolHybridArray):
            total = len(arr)
            hex_total = f"{total:X}"
            hex_data = Ask_arr(arr).strip()
            line = self.PIPE_SEP.join(["bool", hex_total, hex_data])
            return [line]
        elif isinstance(arr, FloatHybridArray):
            total = len(arr)
            hex_total = f"{total:X}"
            header_line = self.PIPE_SEP.join(["float", hex_total])
            lines = [header_line]
            lines.extend(self._encode_1d(arr.a))
            lines.extend(self._encode_1d(arr.b))
            lines.extend(self._encode_1d(arr.lengths))
            if hasattr(arr, 'signs'):
                lines.extend(self._encode_1d(arr.signs))
            lines.append(self.FLOAT_END_SENTINEL)
            return lines
        else:
            raise TypeError(f"不支持序列化类型: {type(arr)}")

    def _decode_1d(self, lines_iter, first_line=None):
        from .int_array import IntHybridArray
        from .float_array import FloatHybridArray
        from . import BoolHybridArr

        if first_line is None:
            line = next(lines_iter).strip()
        else:
            line = first_line.strip()
        parts = line.strip().split(self.PIPE_SEP)
        typ = parts[0]

        if typ == "bool":
            _, hex_total, hex_data = parts
            if not hex_data:
                return BoolHybridArr(split_index=0)
            return temp2(hex_data)
        elif typ == "int":
            _, hex_total, hex_bitlen, hex_data = parts
            elem_cnt = int(hex_total, 16)
            bit_len = int(hex_bitlen, 16)
            if not hex_data or elem_cnt == 0:
                return IntHybridArray([])
            ba = temp2(hex_data)
            int_list = _bhax_decode_int_bits(ba, bit_len, elem_cnt)
            return IntHybridArray(int_list, bit_length=bit_len)
        elif typ == "float":
            _hex_total = parts[1]
            a = self._decode_1d(lines_iter)
            b = self._decode_1d(lines_iter)
            lengths = self._decode_1d(lines_iter)
            next_line = next(lines_iter).strip()
            if next_line == self.FLOAT_END_SENTINEL:
                signs = BoolHybridArr([bool(a[i] < 0) for i in range(len(a))])
            else:
                signs = self._decode_1d(lines_iter, first_line=next_line)
                sentinel = next(lines_iter).strip()
                assert sentinel == self.FLOAT_END_SENTINEL
            fh = FloatHybridArray([])
            fh.a = a
            fh.b = b
            fh.lengths = lengths
            fh.signs = signs
            return fh
        raise ValueError(f"未知类型标记 {typ}")

    def _struct_field_kind(self, ft):
        from .struct_array.core import BHA_Struct, BHA_Char
        if ft is BHA_Char:
            return "int_char"
        if ft is int:
            return "int"
        if ft is float:
            return "float"
        if ft is bool:
            return "bool"
        if isinstance(ft, type) and issubclass(ft, BHA_Struct):
            return "struct"
        return "list"

    def _write_struct(self, zf, sarr, prefix: str):
        from .struct_array.core import StructHybridArray, BHA_Char
        sc = sarr.struct_class
        fields_meta = {}
        for fn, ft in sc.__BHAStructAttrs__.items():
            kind = self._struct_field_kind(ft)
            if kind == "struct":
                sub = getattr(ft, "__module__", None)
                qual = getattr(ft, "__qualname__", None)
                fields_meta[fn] = {"kind": "struct", "module": sub, "qualname": qual}
            else:
                fields_meta[fn] = {"kind": kind}
        meta = {
            "module": getattr(sc, "__module__", None),
            "qualname": getattr(sc, "__qualname__", None),
            "fields": fields_meta,
        }
        zf.writestr(f"{prefix}meta.json", json.dumps(meta))
        for fn, storage in sarr.attrs.items():
            kind = fields_meta[fn]["kind"]
            child_prefix = f"{prefix}{fn}/"
            if kind == "struct":
                self._write_struct(zf, storage, child_prefix)
            elif kind == "list":
                zf.writestr(f"{child_prefix}data.json", json.dumps(list(storage)))
            else:
                lines = self._encode_1d(storage)
                zf.writestr(f"{child_prefix}{self.INNER_SDA}", "\n".join(lines))

    def _read_struct(self, zf, prefix: str):
        import importlib
        from .struct_array.core import StructHybridArray, BHA_Char
        from .int_array import IntHybridArray
        text = zf.read(f"{prefix}meta.json").decode("utf-8")
        meta = json.loads(text)
        mod = importlib.import_module(meta["module"])
        sc = eval(meta["qualname"], vars(mod))
        fields_meta = meta["fields"]
        storages = {}
        size = 0
        for fn, fm in fields_meta.items():
            kind = fm["kind"]
            child_prefix = f"{prefix}{fn}/"
            if kind == "struct":
                storages[fn] = self._read_struct(zf, child_prefix)
                size = max(size, len(storages[fn]))
            elif kind == "list":
                data = json.loads(zf.read(f"{child_prefix}data.json").decode("utf-8"))
                storages[fn] = data
                size = max(size, len(data))
            else:
                sda = child_prefix + self.INNER_SDA
                lines_iter = iter([ln for ln in zf.read(sda).decode("utf-8").splitlines() if ln.strip()])
                arr = self._decode_1d(lines_iter)
                if kind == "int_char":
                    arr = IntHybridArray(list(arr), Type=BHA_Char)
                storages[fn] = arr
                size = max(size, len(arr))
        out = StructHybridArray(sc, 0)
        for fn, fm in fields_meta.items():
            kind = fm["kind"]
            if kind == "struct":
                out.attrs[fn] = storages[fn]
            elif kind == "list":
                out.attrs[fn] = storages[fn]
            else:
                out.attrs[fn] = storages[fn]
        return out

    def _write_bha_list(self, zf, data, prefix: str):
        for idx, item in enumerate(data):
            path = f"{prefix}{idx}/"
            if isinstance(item, BHA_List):
                self._write_bha_list(zf, item, path)
            else:
                lines = self._encode_1d(item)
                zf.writestr(f"{path}{self.INNER_SDA}", "\n".join(lines))

    def write_data(self, arr):
        from .struct_array.core import StructHybridArray
        if self._root.exists():
            self._root.unlink()
        with zipfile.ZipFile(self._root, 'w', zipfile.ZIP_DEFLATED) as zf:
            if isinstance(arr, StructHybridArray):
                self._write_struct(zf, arr, "")
            elif isinstance(arr, BHA_List):
                self._write_bha_list(zf, arr, "")
            else:
                wrapper = BHA_List([arr])
                self._write_bha_list(zf, wrapper, "")

    def _read_bha_list(self, zf, prefix: str):
        names = zf.namelist()
        sub_indices = set()
        for name in names:
            if name.startswith(prefix):
                rest = name[len(prefix):]
                if '/' in rest:
                    idx = rest.split('/')[0]
                    if idx.isdigit():
                        sub_indices.add(int(idx))
        children = []
        for idx in sorted(sub_indices):
            child_prefix = f"{prefix}{idx}/"
            sda_path = f"{child_prefix}{self.INNER_SDA}"
            if sda_path in names:
                text = zf.read(sda_path).decode('utf-8')
                lines_iter = iter([ln for ln in text.splitlines() if ln.strip()])
                obj = self._decode_1d(lines_iter)
                children.append(obj)
            else:
                sub_list = self._read_bha_list(zf, child_prefix)
                children.append(sub_list)
        return BHA_List(children)

    def read_data(self):
        if not self._root.exists():
            raise FileNotFoundError(f"BHAX路径不存在: {self._root}")
        fd = os.open(self._root, os.O_RDONLY)
        try:
            size = os.fstat(fd).st_size
            if size == 0:
                return BHA_List([])
            mm = mmap.mmap(fd, size, access=mmap.ACCESS_READ)
            try:
                if not hasattr(mm, 'seekable'):
                    class _SeekableMM:
                        def __init__(self, m): self._m = m
                        def read(self, n=-1): return self._m.read(n)
                        def seek(self, pos, whence=0): return self._m.seek(pos, whence)
                        def tell(self): return self._m.tell()
                        def seekable(self): return True
                        def close(self): self._m.close()
                    mm = _SeekableMM(mm)
                with zipfile.ZipFile(mm) as zf:
                    names = zf.namelist()
                    if "meta.json" in names:
                        result = self._read_struct(zf, "")
                    else:
                        result = self._read_bha_list(zf, "")
            finally:
                mm.close()
        finally:
            os.close(fd)
        from .struct_array.core import StructHybridArray
        if isinstance(result, StructHybridArray):
            return result
        if len(result) == 1 and not isinstance(result[0], BHA_List):
            return result[0]
        return result

    @property
    def root_path(self) -> pathlib.Path:
        return self._root

    def __repr__(self):
        return f"<BHAX_Descriptor dataset_root='{self._root}'>"

class ProtectedBuiltinsDict(dict,metaclass=ResurrectMeta):
    def __new__(cls, *args, protected_names = (("T", "F","Ask_arr","Ask_BHA","Create_BHA","temp2","BHA_Queue","numba_opt","namespace")+tuple(globals())),
                name = 'builtins', **kwargs):
        self = super().__new__(cls)
        dict.__init__(self, *args, **kwargs)
        if name == 'builtins':
            object.__setattr__(self,'builtins',self)
            object.__setattr__(self,'__builtins__',self)
        self.name = name
        object.__setattr__(self,"protected_names",protected_names)
        return self
    def __init__(self, *args, **kwargs):
        pass
    def __reduce__(self):
        return (ProtectedBuiltinsDict, (dict(self),), {"protected_names": self.protected_names, "name": self.name})
    def __setitem__(self, name, value):
        if not hasattr(self,"protected_names"):
            super().__setitem__(name, value)
            return
        try:
            if name in self.protected_names:
                print(f"\033[31m警告：禁止修改内置常量 __{self.name}__['{name}']！\033[0m")
                raise AttributeError(f"禁止修改内置常量 __{self.name}__['{name}']")
        except:
            if sys.implementation.name == 'cpython':
                raise
        else:super().__setitem__(name, value)
    def __delitem__(self, name):
        if name in self.protected_names:
            print(f"\033[31m警告：禁止删除内置常量 __{self.name}__['{name}']！\033[0m")
            raise AttributeError(f"禁止删除内置常量 __{self.name}__['{name}']")
        if name in self:
            super().__delitem__(name)
    def __delattr__(self, name):
        if name in self.protected_names:
            raise AttributeError(f'禁止删除内置常量：{self.name}.{name}')
        try:
            object.__delattr__(self, name)
        except AttributeError:
            if name in self:
                del self[name]
    def __getattr__(self, name):
        try:
            return super().__getattribute__(name)
        except Exception:
            if name in self:
                return self[name]
            else:raise AttributeError(f"module 'builtins' has no attribute '{name}'") from None
    def __setattr__(self,name,value):
        try:protected = self.protected_names
        except Exception:protected = self
        if name == 'protected_names':
            raise AttributeError(f'禁止修改内置常量：{self.name}.{name}')
        if(name in protected)and(not sys.is_finalizing())and(name != '_'):
            raise AttributeError(f'禁止修改内置常量：{self.name}.{name}')
        else:
            super().__setattr__(name,value)
    def __import__(self, name, globals=None, locals=None, fromlist=(), level=0):
        if fromlist:
            result = []
            for key in fromlist:
                if key not in self:
                    raise AttributeError(f"'ImportableDict' object has no attribute '{key}'")
                result.append(self[key])
            return result[0] if len(result) == 1 else tuple(result)
        return self
    def clear(self):
        if any(k in self.protected_names for k in self):
            raise AttributeError(f"禁止删除内置常量 __{self.name}__")
        super().clear()
    def pop(self, name, *args):
        if name in self.protected_names:
            raise AttributeError(f"禁止删除内置常量 __{self.name}__['{name}']")
        return super().pop(name, *args)
    def popitem(self):
        if any(k in self.protected_names for k in self):
            raise AttributeError(f"禁止删除内置常量 __{self.name}__")
        return super().popitem()
    def update(self, *args, **kwargs):
        items = {}
        if args:
            src = args[0]
            if hasattr(src, 'keys'):
                items.update(src)
            else:
                items.update(dict(src))
        items.update(kwargs)
        for name, value in items.items():
            if name in self.protected_names:
                raise AttributeError(f"禁止修改内置常量 __{self.name}__['{name}']")
            self[name] = value
    def setdefault(self, name, *args):
        if name in self.protected_names:
            raise AttributeError(f"禁止修改内置常量 __{self.name}__['{name}']")
        return super().setdefault(name, *args)
    def __ior__(self, other):
        self.update(other)
        return self
def Ask_arr(arr):
    if isinstance(arr,BHA_List):
        return '\n'.join(map(Ask_arr,arr))
    elif isinstance(arr,BoolHybridArray):
        if arr.size == 0:
            return ''
        h = hex(int(arr))[2:]
        h = '0'*(arr.size - len(bin(int(arr)))+2)+h
        return h
    else:
        return str(arr)
def temp2():
    @lru_cache
    def __temp1(x):
        n = int(x, base=16)
        lead_zero = len(x) - len(x.lstrip('0'))
        total_len = lead_zero + n.bit_length()
        bit_stream = bytes(0 if k < lead_zero else (n >> ((total_len - 1) - k)) & 1 for k in range(total_len))
        return bit_stream
    return lambda x: BoolHybridArr(__temp1(x))
temp2 = temp2()
@BHA_Function
def Ask_BHA(path,mode = "BHA"):
    if mode.lower() == "bhax":
        return BHAX_Descriptor(path).read_data()
    if not path.lower().endswith('.bha'):
        path += '.bha'
    with open(path, 'a+b') as f:
        f.seek(0)
        file_size = os.fstat(f.fileno()).st_size
        if not file_size:
            return TruesArray(0)
        if os.name == 'nt':
            mm = mmap.mmap(f.fileno(), file_size, access=mmap.ACCESS_READ)
        else:
            mm = mmap.mmap(f.fileno(), file_size, flags=mmap.MAP_PRIVATE, prot=mmap.PROT_READ)
        with mm:
            temp = mm.read().decode('utf-8').strip()
        temp = temp.split()
        temp = BHA_List(map(temp2,temp))
        if len(temp) == 1:
            return temp[0]
        return temp

class BHA_Queue(Collection, metaclass=ResurrectMeta):
    def __init__(self, data=(), collection = BoolHybridArr, *a, **k):
        self.a = collection(data, *a, **k)
        self.b = collection([], *a,**k)
        self.collection = collection
    def __str__(self):
        return f"BHA_Queue([{','.join(itertools.chain(map(str,reversed(self.b)),map(str,self.a)))}])"
    __repr__ = __str__
    def __contains__(self,v):
        return v in self.a or v in self.b
    def enqueue(self, v):
        self.a.append(v)
    def dequeue(self):
        if self.b:
            return self.b.pop()
        elif self.a:
            Type = self.b.Type
            self.b = self.collection(reversed(self.a))
            self.b.Type = Type
            self.a.clear()
            return self.dequeue()
        else:
            raise IndexError("无法从空的 BHA_Queue 队列执行出队操作")
    def __iter__(self):
        yield from reversed(self.b)
        yield from self.a
    def __len__(self):
        return len(self.a) + len(self.b)
    def is_empty(self):
        return not self
    put = append = enqueue
    get = popleft = dequeue
    def appendleft(self, v):
        self.b.append(v)
    def pop(self):
        if self.a:
            return self.a.pop()
        if self.b:
            Type = self.a.Type
            self.a = self.collection(reversed(self.b))
            self.a.Type = Type
            self.b.clear()
            return self.a.pop()
        raise IndexError("无法从空的 BHA_Queue 队列执行出队操作")
@BHA_Function
def Create_BHA(path,arr,mode = "BHA"):
    if mode.lower() == "bhax":
        BHAX_Descriptor(path).write_data(arr)
        return
    if not path.lower().endswith('.bha'):
        path += '.bha'
    temp = Ask_arr(arr).strip().encode('utf-8')
    with open(path, "w+b") as f:
        f.truncate(len(temp))
        if not len(temp):
            return
        with mmap.mmap(
            f.fileno(),
            length=len(temp),
            access=mmap.ACCESS_WRITE
        ) as mm:
            mm[:] = temp
            mm.flush()
def numba_opt():
    import numba
    g = globals()
    updated = []
    for name, obj in list(g.items()):
        if name.startswith("__"):
            continue
        if isinstance(obj, (numba.core.registry.CPUDispatcher, numba.core.types.npytypes.NumbaType)):
            continue
        if inspect.isfunction(obj):
            try:
                wrapped = numba.jit(nopython=False)(obj)
                g[name] = wrapped
                updated.append(f"func: {name}")
            except BaseException as e:traceback.print_exception(type(e), e, e.__traceback__)
        elif inspect.isclass(obj):
            if obj.__module__ == __name__:
                for attr_name, attr_val in list(obj.__dict__.items()):
                    if inspect.isfunction(attr_val):
                        try:
                            wrapped_method = numba.jit(nopython=False)(attr_val)
                            setattr(obj, attr_name, wrapped_method)
                            updated.append(f"class {obj.__name__}.{attr_name}")
                        except BaseException as e:traceback.print_exception(type(e), e, e.__traceback__)
    print(f"numba jit完成，共处理 {len(updated)} 个对象：")
    for s in updated:
        print(" -", s)
class namespace(ProtectedBuiltinsDict):
    def __new__(cls,name,bases,namespace_):
        tmp = {}
        for base in bases:tmp.update(base.__namespace__)
        self = ProtectedBuiltinsDict({**tmp,**namespace_},name = name,protected_names = namespace_.get("protected_names",()))
        self["__namespace__"] = self
        return self
class BHA_lazy_sieve(metaclass=ResurrectMeta):
    __module__ = 'bool_hybrid_array'
    def __init__(self):
        from .int_array import IntHybridArray
        self.primes = IntHybridArray([2])
        self._limit = 3
        self._n = 3
        self._last = 2
        self._started = False
        self._pos = -1
    def _grow(self):
        old_len = self._limit
        new_len = old_len + max(256, old_len >> 2)
        blen = new_len - old_len
        block = TruesArray(blen)
        lim = math.isqrt(new_len - 1)
        plen = len(self.primes)
        for j in range(plen):
            p = self.primes[j]
            if p > lim:
                break
            start = ((old_len + p - 1) // p) * p
            for m in range(start, new_len, p):
                block[m - old_len] = False
        for i in range(blen):
            if block[i]:
                q = old_len + i
                qq = q * q
                if qq >= new_len:
                    break
                for m in range(qq, new_len, q):
                    block[m - old_len] = False
        self._limit = new_len
        for i in range(blen):
            if block[i]:
                self.primes.append(old_len + i)
    def __iter__(self):
        return self
    def __next__(self):
        if not self._started:
            self._started = True
            self._pos = 0
            return self._last
        while self._pos + 1 >= len(self.primes):
            self._grow()
        self._pos += 1
        n = self.primes[self._pos]
        self._last = n
        self._n = n + 1
        return n
    def upto(self, N):
        for p in self:
            if p > N:
                self.primes.pop()
                self._n = p
                break
        while self.primes and self.primes[-1] > N:
            self.primes.pop()
        self._pos = len(self.primes) - 1
        self._limit = self.primes[-1] + 1 if self.primes else 2
        return self.primes
    def take(self, k):
        start = self._pos + 1
        for _ in range(k):
            next(self)
        return self.primes[start:self._pos + 1]
    def count_le(self, N):
        while self._limit <= N:
            self._grow()
        return bisect.bisect_right(self.primes, N)
    def reset(self):
        self.__init__()
        return self
    @property
    def current(self):
        return self._last
    @property
    def discovered(self):
        return len(self.primes)
    def __len__(self):
        return len(self.primes)
    def __repr__(self):
        return f'BHA_lazy_sieve(current={self._last}, discovered={len(self.primes)})'
    def __getstate__(self):
        return (self.primes, self._limit, self._n, self._last, self._started, self._pos)
    def __setstate__(self, state):
        self.primes, self._limit, self._n, self._last, self._started, self._pos = state
