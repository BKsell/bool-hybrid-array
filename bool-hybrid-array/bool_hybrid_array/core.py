# cython: language_level=3, boundscheck=False, wraparound=False, initializedcheck=False
from __future__ import annotations
try:from mypy_extensions import mypyc_attr
except:
    def mypyc_attr(*a,**k):
        return lambda func:func
import builtins
from types import MappingProxyType
import array,bisect,numpy as np
from collections.abc import MutableSequence,Iterable,Generator,Iterator,Sequence,Collection
import itertools,copy,sys,math,weakref,random,mmap,os
from functools import reduce
import operator,ctypes,gc,abc,types
from functools import lru_cache
from typing import _GenericAlias
from typing import Callable, Union, Sequence, MutableSequence, Any, overload, Sized
hybrid_array_cache:list[tuple[Any]] = []
try:
    msvcrt = ctypes.CDLL('msvcrt.dll')
    memcpy = msvcrt.memcpy
except:
    try:
        libc = ctypes.CDLL('libc.so.6')
        memcpy = libc.memcpy
    except:
        libc = ctypes.CDLL('libc.so')
        memcpy = libc.memcpy
memcpy.argtypes = (ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t)
memcpy.restype = ctypes.c_void_p
if 'GenericAlias' in types.__dict__:
    _GenericAlias = types.GenericAlias
class ResurrectMeta(abc.ABCMeta,metaclass=abc.ABCMeta):# type: ignore
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
        super_cls.__setattr__('original_dict', dict(obj.__dict__))# type: ignore[assignment]
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
        super_cls.__setattr__('original_dict', MappingProxyType(obj.original_dict))# type: ignore[assignment]
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
class BHA_Function(metaclass=ResurrectMeta):# type: ignore
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
@mypyc_attr(native_class=False)
class BoolHybridArray(MutableSequence,Exception,metaclass=ResurrectMeta):# type: ignore
    __module__ = 'bool_hybrid_array'
    @mypyc_attr(native_class=False)
    class _CompactBoolArray(Sequence,Exception):
        def __init__(self, size: int):
            self.size = size
            self.n_uint8 = (size + 7) >> 3
            self.data = np.zeros(self.n_uint8, dtype=np.uint8)# type: ignore[assignment]
        def __setitem__(self, index: int | slice, value: Any):
            ctypes_arr = self.data.ctypes.data_as(ctypes.POINTER(ctypes.c_ubyte))
            if isinstance(index, slice):
                start, stop, step = index.indices(self.size)
                indices = list(range(start, stop, step))
                if isinstance(value, (list, tuple)):
                    if len(value)!= len(indices):
                        raise ValueError("值的数量与切片长度不匹配")
                    for i, val in zip(indices, value):
                        self._set_single(i, bool(val), ctypes_arr)
                else:
                    val_bool = bool(value)
                    for i in indices:
                        self._set_single(i, val_bool, ctypes_arr)
                self.data = np.ctypeslib.as_array(ctypes_arr, shape=(self.n_uint8,))
                return
            if not (0 <= index < self.size):
                raise IndexError(f"密集区索引 {index} 超出范围 [0, {self.size})")
            self._set_single(index, bool(value), ctypes_arr)
            self.data = np.ctypeslib.as_array(ctypes_arr, shape=(self.n_uint8,))
            self.data = self.data.view()
        def _set_single(self, index: int, value: bool, ctypes_arr):
            uint8_pos = index >> 3
            bit_offset = index & 7
            ctypes_arr[uint8_pos] &= ~(1 << bit_offset) & 0xFF
            if value:
                ctypes_arr[uint8_pos] |= (1 << bit_offset)

        def __getitem__(self, index: int | slice) -> bool | list[bool]:
            if isinstance(index, slice):
                start, stop, step = index.indices(self.size)
                result = []
                for i in range(start, stop, step):
                    uint8_pos = i >> 3
                    bit_offset = i & 7
                    result.append(bool((self.data[uint8_pos] >> bit_offset) & 1))
                return result
            if not (0 <= index < self.size):
                raise IndexError(f"密集区索引 {index} 超出范围 [0, {self.size})")
            uint8_pos = index >> 3
            bit_offset = index & 7
            return bool((self.data[uint8_pos] >> bit_offset) & 1)
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
    def __init__(self, split_index: int, size=None, is_sparse=False ,Type:Callable = None,hash_:Any = True) -> None:
        self.Type = Type if Type is not None else builtins.BHA_Bool
        self.split_index = int(split_index)
        self.size = size or 0
        self.is_sparse = is_sparse
        self.small = self._CompactBoolArray(self.split_index + 1)
        self.small.set_all(not is_sparse)
        self.large = array.array('I') if size < 1<<32 else array.array('Q')
        self.generator = iter(self)
        self.hash_ = hash_
        if hash_:
            global hybrid_array_cache
            hybrid_array_cache = [
                (ref, h) for ref, h in hybrid_array_cache 
                if ref() is not None
            ]
            for ref, existing_hash in hybrid_array_cache:
                existing_array = ref()
                try:
                    if self.size != existing_array.size:
                        continue
                    elif self == existing_array:
                        self._cached_hash = existing_hash
                        return
                except Exception:
                    continue
        new_hash = id(self)
        self._cached_hash = new_hash
        hybrid_array_cache.append((weakref.ref(self), new_hash))
    def __call__(self, func):
        func.self = self
        def wrapper(*args, **kwargs):
            return func(self, *args, **kwargs)
        setattr(self, func.__name__, wrapper)
        return func
    def __hash__(self):
        return self._cached_hash
    def accessor(self, i: int, value: Any = None) -> Any:
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
                condition = not value or exists
                if self.is_sparse != condition:
                    self.large.insert(pos, i)
                else:
                    if pos < len(self.large):
                        del self.large[pos]
                return None
    @overload
    def __getitem__(self, idx: int, /) -> Any: ...
    @overload
    def __getitem__(self, idx: slice, /) -> list: ...

    def __getitem__(self, key:int|slice = -1,/) -> Any:
        if isinstance(key, slice):
            start, stop, step = key.indices(self.size)
            return BoolHybridArr((self[i] for i in range(start, stop, step)),hash_ = self.hash_)
        key = key if key >=0 else key + self.size
        if 0 <= key < self.size:
            return self.Type(self.accessor(key))
        raise IndexError("索引超出范围")
    def __setitem__(self, key: int | slice, value:Any) -> None:
        if isinstance(key, int):
            adjusted_key = key if key >= 0 else key + self.size
            if not (0 <= adjusted_key < self.size):
                raise IndexError("索引超出范围")
            self.accessor(adjusted_key, bool(value))
            return
        if isinstance(key, slice):
            original_size = self.size
            start, stop, step = key.indices(original_size)
            value_list = list(value)
            new_len = len(value_list)
            if step != 1:
                slice_indices = list(range(start, stop, step))
                if new_len != len(slice_indices):
                    raise ValueError(f"值长度与切片长度不匹配：{new_len} vs {len(slice_indices)}")
                for i, val in zip(slice_indices, value_list):
                    self[i] = val
                return
            if new_len == max(0, stop - start):
                for v,i in zip(new_len,range(start,stop)):
                    self[i] = v
                return
            for i in range(stop - 1, start - 1, -1):
                if i <= self.split_index:
                    if i >= len(self.small):
                        self.small = np.pad(
                            self.small, 
                            (0, i - len(self.small) + 1),
                            constant_values=not self.is_sparse
                        )
                del self[i]
            for idx, val in enumerate(value_list):
                self.insert(start + idx, bool(val))
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
        key = key if key >= 0 else key + self.size
        if isinstance(key, slice):
            start, stop, step = key.indices(self.size)
            for i in range(start,stop,step):del self[i]
        if not (0 <= key < self.size):
            raise IndexError(f"索引 {key} 超出范围 [0, {self.size})")
        if key <= self.split_index:
            if key >= len(self.small):
                raise IndexError(f"小索引 {key} 超出small数组范围（长度{len(self.small)}）")
            self.small = np.delete(self.small, key)# type: ignore[assignment]
            self.small = np.append(self.small, not self.is_sparse)# type: ignore[assignment]
            self.split_index -= min(self.split_index, len(self.small) - 1)
        else:
            pos = bisect.bisect_left(self.large, key)
            if pos < len(self.large) and self.large[pos] == key:
                del self.large[pos]
            adjust_pos = bisect.bisect_right(self.large, key)
            for i in range(adjust_pos, len(self.large)):
                self.large[i] -= 1
        self.size -= 1
    def __str__(self) -> str:
        return f"BoolHybridArr([{','.join(map(str,self))}])"
    def __reversed__(self):
        if not self:return BHA_Iterator([])
        return BHA_Iterator(map(self.__getitem__,range(self.size-1,-1,-1)))
    def insert(self, key: int, value: Any) -> None:
        value = bool(value)
        key = key if key >= 0 else key + self.size
        key = max(0, min(key, self.size))
        if key <= self.split_index:
            if key > len(self.small):
                self.small = np.pad(
                    self.small, 
                    (0, key - len(self.small) + 1),
                    constant_values=not self.is_sparse
                )
            self.small = np.insert(self.small, key, value)# type: ignore[assignment]
            self.split_index = min(self.split_index + 1, len(self.small) - 1)
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
        return BHA_Iterator(map(self.__getitem__,range(self.size)))
    def __next__(self):
        return next(self.generator)
    def __contains__(self, value:Any) -> bool:
        if not isinstance(value, (bool,np.bool_,self.Type,BHA_bool)):return False
        if not self.size:return False
        for i in range(10):
            if self[random.randint(0,self.size-1)] == value:
                return True
        b = any(1 for i in range(self.small.size+1>>1) if value==self.small[i] or value==self.small[self.small.size-i-1])
        if value == self.is_sparse:
            return self.large or b
        else:
            return len(self.large) == self.size-self.split_index-1 or b
    def __bool__(self) -> bool:
        return bool(self.size)
    def __any__(self):
        return builtins.T in self
    def __all__(self):
        return builtins.F not in self
    def __eq__(self, other) -> bool:
        if not isinstance(other, (BoolHybridArray, list, tuple, np.ndarray, array.array)):
            return False
        if len(self) != len(other):
            return False
        return all(a == b for a, b in zip(self, other))
    def __ne__(self, other) -> bool:
        return not self == other
    def __and__(self, other) -> BoolHybridArray:
        if type(other) == int:
            other = abs(other)
            other = bin(other)[2:]
        if len(self) != len(other):
            raise ValueError(f"与运算要求数组长度相同（{len(self)} vs {len(other)}）")
        return BoolHybridArr(map(operator.and_, self, other),hash_ = self.hash_)
    def __int__(self):
        if not self.size:
            return 0
        return reduce(lambda acc, val: operator.or_(operator.lshift(acc, 1), int(val)),self,0)
    def __or__(self, other) -> BoolHybridArray:
        if type(other) == int:
            other = bin(other)[2:]
        if self.size != len(other):
            raise ValueError(f"或运算要求数组长度相同（{len(self)} vs {len(other)}）")
        return BoolHybridArr(map(operator.or_, self, other),hash_ = self.hash_)
    def __ror__(self, other) -> BoolHybridArray:
        if type(other) == int:
            other = abs(other)
            other = bin(other)[2:]
        return self | other
    def __rshift__(self, other) -> BoolHybridArray:
        arr = BoolHybridArr(self)
        arr >>= other
        return arr
    def __irshift__(self, other) -> BoolHybridArray:
        if int(other) < 0:
            self <<= -other
            return self
        for i in range(int(other)):
            if self.size < 1:
                return self
            self.pop(-1)
        return self
    def __ilshift__(self ,other) -> BoolHybridArray:
        if int(other) < 0:
            self >>= -other
            return self
        if not self.is_sparse:
            self += FalsesArray(int(other))
            self.optimize()
        else:
            self.size += int(other)
        return self
    def __lshift__(self ,other) -> BoolHybridArray:
        if int(other) < 0:
            return self >> -other
        return self+FalsesArray(int(other))
    def __add__(self, other) -> BoolHybridArray:
        arr = self.copy()
        arr += other
        arr.optimize()
        return arr
    def __rand__(self, other) -> BoolHybridArray:
        if type(other) == int:
            other = bin(other)[2:]
        return self & other
    def __xor__(self, other) -> BoolHybridArray:
        if len(self) != len(other):
            raise ValueError(f"异或运算要求数组长度相同（{len(self)} vs {len(other)}）")
        return BoolHybridArr(map(operator.xor, self, other),hash_ = self.hash_)
    def __rxor__(self, other) -> BoolHybridArray:
        return self^other
    def __invert__(self) -> BoolHybridArray:
        return BoolHybridArr(not a for a in self)
    def copy(self) -> BoolHybridArray:
        arr = BoolHybridArray(split_index = self.split_index,size = self.size)
        arr.large,arr.small,arr.split_index,arr.is_sparse,arr.Type,arr.size = (array.array(self.large.typecode, self.large),self.small.copy(),
        self.split_index,BHA_Bool(self.is_sparse),self.Type,self.size)
        return arr
    def __copy__(self) -> BoolHybridArray:
        return self.copy()
    def find(self,value):
        from .int_array import IntHybridArray
        return IntHybridArray([i for i in range(len(self)) if self[i]==value])
    def extend(self, iterable:Iterable) -> None:
        if isinstance(iterable, (Iterator, Generator, map)):
            iterable,copy = itertools.tee(iterable, 2)
            len_ = sum(1 for _ in copy)
        else:
            len_ = len(iterable)
        self.size += len_
        for i,j in zip(range(len_),iterable):
            self[-i-1] = j
    def append(self,v):
        self.size += 1
        self[-1] = v
    push = append
    peek = __getitem__
    top = property(peek)
    front = property(lambda self:self[0])
    rear = top
    enqueue = push
    def index(self, value) -> int:
        if self.size == 0:
            raise ValueError('无法在空的 BoolHybridArray 中查找元素！')
        value = bool(value)
        x = 'not find'
        for i in range(self.size):
            if self[i] == value:
                return i
            if self[-i] == value:
                x = self.size-i
            if len(self)-i == i:
                break
        if x != 'not find':
            return x
        raise ValueError(f"{value} not in BoolHybridArray")
    def rindex(self, value) -> int:
        if self.size == 0:
            raise ValueError('无法在空的 BoolHybridArray 中查找元素！')
        value = bool(value)
        x = 'not find'
        for i in range(self.size):
            if self[-i] == value:
                return -i
            if self[i] == value:
                x = -(self.size-i)
            if len(self)-i == i:
                break
        if x != 'not find':
            return x
        raise ValueError(f"{value} not in BoolHybridArray")
    def count(self, value) -> int:
        value = bool(value)
        return sum(v == value for v in self)
    def optimize(self,*a,**k) -> BoolHybridArray:
        arr = BoolHybridArr(self,*a,**k)
        self.large,self.small,self.split_index,self.is_sparse = (arr.large,arr.small,
        arr.split_index,arr.is_sparse)
        gc.collect()
        return self
    def memory_usage(self, detail=False) -> dict | int:
        small_mem = self.small.size // 8 + 32
        large_mem = len(self.large) * 4 + 32
        equivalent_list_mem = 40 + 8 * self.size
        equivalent_numpy_mem = 96 + self.size
        total = small_mem+large_mem
        if not detail:
            return total
        need_optimize = False
        optimize_reason = ""
        sparse_ratio = len(self.large) / max(len(self), 1)
        if sparse_ratio > 0.4 and len(self) > 500:  # 阈值可根据测试调整
            need_optimize = True
            optimize_reason = "稀疏区索引密度过高，优化后可转为密集存储提升速度"
        elif len(self) < 32 and total > len(self):
            need_optimize = True
            optimize_reason = "小尺寸数组存储冗余，优化后将用int位存储进一步省内存"
        elif np.count_nonzero(np.array(self.small)) / max(len(self.small), 1) < 0.05 and len(self) > 1000:
            need_optimize = True
            optimize_reason = "密集区有效值占比过低，优化后可转为稀疏存储节省内存"
        return {
            "总占用(字节)": total,
            "密集区占用": small_mem,
            "稀疏区占用": large_mem,
            "对比原生list节省": f"{(1 - total/equivalent_list_mem)*100:.6f}%",
            "对比numpy节省": f"{(1 - total/equivalent_numpy_mem)*100:.6f}%" if equivalent_numpy_mem > 0 else "N/A",
            "是否需要优化": "是" if need_optimize else "否",
            "优化理由/说明": optimize_reason if need_optimize else "当前存储模式已适配数据特征，无需优化"
        }
    def get_shape(self):
        return (self.size,)
    def __array__(self,dtype = np.bool_,copy = None):
        arr = np.fromiter(map(np.bool_,self), dtype=dtype)
        return arr.copy() if copy else arr.view()
    def view(self):
        arr = TruesArray(0)
        arr.__dict__ = self.__dict__
        return arr
    def __reduce__(self):
        return BoolHybridArr,(np.asarray(self),self.is_sparse,self.Type,self.hash_,),
    dequeue = lambda self:self.pop(0)
@mypyc_attr(native_class=False)
class BoolHybridArr(BoolHybridArray,metaclass=ResurrectMeta):# type: ignore
    __module__ = 'bool_hybrid_array'
    def __new__(cls, lst: Iterable = (), is_sparse=None, Type = None, hash_ = True, split_index = None) -> BoolHybridArray:
        a = isinstance(lst, (Iterator, Generator, map))
        if a:
            lst, copy1, copy2 = itertools.tee(lst, 3)
            size = sum(1 for _ in copy1)
            true_count = sum(bool(val) for val in copy2)
        else:
            size = len(lst)
            true_count = sum(bool(val) for val in lst)
        if size == 0:
            return BoolHybridArray(0, 0, is_sparse=False if is_sparse is None else is_sparse)
        if is_sparse is None:
            is_sparse = true_count <= (size - true_count)
        if split_index == None:
            split_index = int(min(size * 0.8, math.sqrt(size) * 100))
            split_index = math.isqrt(size) if true_count>size/3*2 or true_count<size/3 else max(split_index, 1)
            split_index = int(split_index) if split_index < 150e+7*2 else int(145e+7*2)
        arr = BoolHybridArray(split_index = split_index, size = size, is_sparse = is_sparse, Type = Type, hash_ = F)
        small_max_idx = min(split_index, size - 1)
        if a:
            small_data = []
            large_indices = []
            for i, val in enumerate(lst):
                val_bool = bool(val)
                if i <= small_max_idx:
                    small_data.append(val_bool)
                else:
                    if (is_sparse and val_bool) or (not is_sparse and not val_bool):
                        large_indices.append(i)
            if small_data:
                arr.small[:len(small_data)] = small_data
            if large_indices:
                arr.large.extend(large_indices)
        else:
            if small_max_idx >= 0:
                arr.small[:small_max_idx + 1] = [bool(val) for val in lst[:small_max_idx + 1]]
            large_indices = [
                i for i in range(split_index + 1, size)
                if (is_sparse and bool(lst[i])) or (not is_sparse and not bool(lst[i]))
            ]
            arr.large.extend(large_indices)
        arr.large = sorted(arr.large)
        type_ = 'I' if size < 1 << 32 else 'Q'
        arr.large = array.array(type_, arr.large)
        if hash_:
            global hybrid_array_cache
            del hybrid_array_cache[-1]
            hybrid_array_cache = [
                (ref, h) for ref, h in hybrid_array_cache 
                if ref() is not None
            ]
            for ref, existing_hash in hybrid_array_cache:
                existing_array = ref()
                try:
                    if arr.size != existing_array.size:
                        continue
                    elif arr == existing_array:
                        arr._cached_hash = existing_hash
                        return arr
                except:
                    continue
        return arr
def TruesArray(size, Type = None, hash_ = True):
    split_index = min(size//10, math.isqrt(size))
    split_index = max(split_index, 1)
    split_index = int(split_index) if split_index < 150e+7*2 else int(145e+7*2)
    return BoolHybridArray(split_index,size,Type = Type,hash_ = hash_)
def FalsesArray(size, Type = None,hash_ = True):
    split_index = min(size//10, math.isqrt(size))
    split_index = max(split_index, 1)
    split_index = int(split_index) if split_index < 150e+7*2 else int(145e+7*2)
    return BoolHybridArray(split_index,size,True,Type = Type,hash_ = hash_)
Bool_Array = np.arange(2,dtype = np.uint8)
@mypyc_attr(native_class=False)
class BHA_bool(int,metaclass=ResurrectMeta):# type: ignore
    __module__ = 'bool_hybrid_array'
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
@mypyc_attr(native_class=False)
class BHA_Bool(BHA_bool,metaclass=ResurrectMeta):# type: ignore
    __module__ = 'bool_hybrid_array'
    @lru_cache
    def __new__(cls,v):
        return builtins.T if v else builtins.F
@mypyc_attr(native_class=False)
class BHA_List(list,metaclass=ResurrectMeta):# type: ignore
    __module__ = 'bool_hybrid_array'
    def __init__(self,arr):
        def Temp(v):
            if isinstance(v,(list,tuple)):
                v = (BoolHybridArr(v) if all(isinstance(i,
                    (bool,BHA_bool,np.bool_)) for i in v)
                     else BHA_List(v))
            if isinstance(v,BoolHybridArray):
                return v
            elif isinstance(v,(bool,np.bool_)):
                return BHA_Bool(v)
            else:
                return v
        super().__init__(map(Temp,arr))
        try:self.hash_value = sum(map(hash,self))
        except Exception as e:return hash(e)
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
@mypyc_attr(native_class=False)
class BHA_Iterator(Iterator,metaclass=ResurrectMeta):# type: ignore
    __module__ = 'bool_hybrid_array'
    def __init__(self,data):
        self.data,self.copy_data = itertools.tee(iter(data),2)
    def __next__(self):
        try:return next(self.data)
        except StopIteration as e:
            self.__init__(self.copy_data)
            raise e
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
@mypyc_attr(native_class=False)
class ProtectedBuiltinsDict(dict,metaclass=ResurrectMeta):# type: ignore
    def __init__(self, *args, protected_names = ("T", "F", "BHA_Bool", "BHA_List", "BoolHybridArray", "BoolHybridArr",
                                "TruesArray", "FalsesArray", "ProtectedBuiltinsDict", "builtins",
                                "__builtins__", "__dict__","ResurrectMeta","math",
                                "np","protected_names","BHA_Function",
                                "__class__","Ask_BHA","Create_BHA","Ask_arr","numba_opt","bool_hybrid_array","BHA_Queue","cin","cout","endl"),
                 name = 'builtins', **kwargs):
        super().__init__(*args, **kwargs)
        if name == 'builtins':
            super().__setattr__('__dict__',self)
            super().__setattr__('builtins',self)
            super().__setattr__('__builtins__',self)
        self.name = name
        super().__setattr__("protected_names",protected_names)
    def __setitem__(self, name, value):
        if not hasattr(self,"protected_names"):
            super().__setitem__(name, value)
            return
        try:
            if name in ["T", "F"]:
                current_T = self.get("T")
                current_F = self.get("F")
                if isinstance(current_T, BHA_bool) and isinstance(current_F, BHA_bool):
                    is_swap = (name == "T" and isinstance(value, BHA_bool) and value.value == current_F.value)or(name == "F" and isinstance(value, BHA_bool) and value.value == current_T.value)
                    if is_swap:
                        print(f"""\033[31m警告：禁止交换内置常量 __{self.name}__["{name}"] 和 __builtins__["{'F' if name == 'T' else 'T'}"]！\033[0m""")
                        raise AttributeError(f"""禁止交换内置常量 __{self.name}__["{name}"] 和 __{self.name}__["{'F' if name == 'T' else 'T'}"]""")
            if name in self.protected_names and name not in ["T", "F"]:
                print(f"\033[31m警告：禁止修改内置常量 __{self.name}__['{name}']！\033[0m")
                raise AttributeError(f"禁止修改内置常量 __{self.name}__['{name}']")
        except:
            if sys.implementation.name == 'cpython':
                raise
        finally:super().__setitem__(name, value)
    def __delitem__(self, name):
        if name in self.protected_names:
            print(f"\033[31m警告：禁止删除内置常量 __builtins__['{name}']！\033[0m")
            raise AttributeError(f"禁止删除内置常量 __builtins__['{name}']")
        if name in self:
            super().__delitem__(name)
    def __delattr__(self, name):
        if name in self.protected_names:
            raise AttributeError(f'禁止删除内置常量：{self.name}.{name}')
        else:
            del self[name]
    def __getattr__(self, name):
        try:
            return super().__getattribute__(name)
        except AttributeError:
            if name in self:
                return self[name]
            raise AttributeError(f"module 'builtins' has no attribute '{name}'") from None
    def __setattr__(self,name,value):
        try:protected = self.protected_names
        except Exception:protected = self
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
def Ask_arr(arr):
    if isinstance(arr,BHA_List):
        return '\n'.join(map(Ask_arr,arr))
    elif isinstance(arr,BoolHybridArray):
        h = hex(int(arr))[2:]
        h = '0'*(arr.size - len(bin(int(arr)))+2)+h
        return h
    else:
        return str(arr)
@BHA_Function
def Ask_BHA(path):
    if '.bha' not in path.lower():
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
        temp2 = lambda x: BoolHybridArr(
        (
        bit_stream := bytes(0 if k < lead_zero else (n >> ((total_len - 1) - k)) & 1 for k in range(total_len)),
        arr := array.array('B', FalsesArray(total_len)),
        memcpy(arr.buffer_info()[0], bit_stream, total_len),arr)[-1]
        if(n := int(x, base=16),
        lead_zero := len(x) - len(x.lstrip('0')),
        total_len := lead_zero + n.bit_length())
        else array.array('B'))
        temp = BHA_List(map(temp2,temp))
        if len(temp) == 1:
            return temp[0]
        return temp
class BHA_Queue(Collection,metaclass = ResurrectMeta):
    def __init__(self,data = (),*a,**k):
        self.a = BoolHybridArr(data,*a,**k)
        self.b = BoolHybridArr([],*a,**k)
    def __str__(self):
        return f"BHA_Queue([{','.join(itertools.chain(map(str,reversed(self.b)),map(str,self.a)))}])"
    __repr__ = __str__
    def enqueue(self,v):
        self.a.push(v)
    def dequeue(self):
        if self.b:
            return self.b.pop()
        elif self.a:
            Type = self.b.Type
            self.b = BoolHybridArr(reversed(self.a))
            self.b.Type = Type
            self.a.clear()
            return self.dequeue()
        else:
            raise IndexError("无法从空的 BHA_Queue 队列执行出队操作")
    def __iter__(self):
        yield from reversed(self.b)
        yield from self.a
    def __len__(self):
        return len(self.a)+len(self.b)
    def is_empty(self):
        return not self
@BHA_Function
def Create_BHA(path,arr):
    if '.bha' not in path.lower():
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
    import numba # type: ignore
    sig = numba.types.Union([
        numba.types.intp(
            numba.types.Array(numba.types.uint32, 1, 'C'),
            numba.types.uint32,
            numba.types.uint32,
            numba.types.Optional(numba.types.uint32)
        ),
        numba.types.intp(
            numba.types.Array(numba.types.uint64, 1, 'C'),
            numba.types.uint64,
            numba.types.uint64,
            numba.types.Optional(numba.types.uint64)
        ),
        numba.types.intp(
            numba.types.Any,
            numba.types.Any,
            numba.types.Any,
            numba.types.Optional(numba.types.Any)
        )
    ])
    bisect.bisect_left = numba.njit(sig, cache=True)(bisect.bisect_left)
    bisect.bisect_right = numba.njit(sig, cache=True)(bisect.bisect_right)
from ._cppiostream import cin,cout,endl
builtins.np = np
builtins.T = BHA_bool(1)
builtins.F = BHA_bool(0)
builtins.BHA_Bool = BHA_Bool
builtins.BHA_List = BHA_List
builtins.FalsesArray =  FalsesArray
builtins.TruesArray = TruesArray
builtins.BoolHybridArr = BoolHybridArr
builtins.BHA_Iterator = BHA_Iterator
builtins.BoolHybridArray = BoolHybridArray
builtins.BHA_Bool.T,builtins.BHA_Bool.F = BHA_bool(1),BHA_bool(0)
builtins.ResurrectMeta = ResurrectMeta
builtins.ProtectedBuiltinsDict = ProtectedBuiltinsDict
builtins.BHA_Function = BHA_Function
builtins.Ask_BHA = Ask_BHA
builtins.Create_BHA = Create_BHA
builtins.numba_opt = numba_opt
builtins.cin = cin
builtins.cout = cout
builtins.endl = endl
builtins.BHA_Queue = BHA_Queue
Tid,Fid = id(builtins.T),id(builtins.F)
original_id = builtins.id
def fake_id(obj):
    if isinstance(obj, BHA_bool):return Tid if obj else Fid
    else:return original_id(obj)
builtins.id = fake_id
original_builtins_dict = builtins.__dict__.copy()
__builtins__ = ProtectedBuiltinsDict(original_builtins_dict)
builtins = __builtins__
sys.modules['builtins'] = builtins
builtins.name = 'builtins'