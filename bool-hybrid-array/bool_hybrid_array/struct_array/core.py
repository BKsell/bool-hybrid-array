# cython: language_level=3,boundscheck=False,wraparound=False,cdivision=True,nonecheck=False,overflowcheck=False,initializedcheck=False,infer_types=True,annotation_typing=True,profile=False,linetrace=False,emit_code_comments=False,c_api_binop_methods=True
from __future__ import annotations
from collections.abc import MutableSequence, MutableMapping, MutableSet
from itertools import repeat
from weakref import WeakValueDictionary, proxy as _wproxy
from ..core import *
from ..int_array import IntHybridArray
from ..float_array import FloatHybridArray, BHA_Float
from ..twg_sort import twg_sort
import math as _math
import colorsys as _colorsys
import datetime as _datetime
import operator


def _item_to_row(item, struct_class):
    if isinstance(item, dict):
        return item
    if isinstance(item, BHA_Struct):
        arr = item.__dict__.get("_arr")
        if arr is not None:
            i = item.__dict__.get("index")
            return {k: arr.attrs[k][i] for k in struct_class.__BHAStructAttrs__}
        return {k: getattr(item, k) for k in struct_class.__BHAStructAttrs__}
    row = {}
    for k in struct_class.__BHAStructAttrs__:
        try:
            row[k] = getattr(item, k)
        except AttributeError:
            raise TypeError(f"cannot treat {type(item).__name__} as {struct_class.__name__}")
    return row


class BHAStructMeta(type, metaclass=ResurrectMeta):
    def __mul__(cls, n):
        if not isinstance(n, int):
            return NotImplemented
        return StructHybridArray(cls, n)
    __rmul__ = __mul__

    def __call__(cls, *args, **kwargs):
        tmp = StructHybridArray(cls, 1)
        proxy = tmp[0]
        proxy._arr = tmp
        cls.__init__(proxy, *args, **kwargs)
        return proxy


class BHA_Char(int, metaclass=ResurrectMeta):
    __module__ = 'bool_hybrid_array.struct_array'
    def __new__(cls, value=0, *args, **kwargs):
        if isinstance(value, str):
            if len(value) != 1:
                raise ValueError("BHA_Char 只接受单个字符")
            value = ord(value)
        return int.__new__(cls, value)
    def __str__(self):
        try:
            return chr(int(self))
        except (ValueError, OverflowError):
            return int.__str__(self)
    def __repr__(self):
        return repr(chr(int(self))) if 0 <= int(self) < 0x110000 else int.__repr__(self)


class BHA_Struct(metaclass=BHAStructMeta):
    __BHAStructAttrs__: dict = {}

    def __getattr__(self, name):
        arr = self.__dict__.get("_arr")
        i = self.__dict__.get("index")
        if arr is None or i is None:
            raise AttributeError(f"{type(self).__name__!r} unbound")
        if name in arr.attrs:
            return arr.attrs[name][i]
        raise AttributeError(f"{type(self).__name__!r} has no field {name!r}")

    def __setattr__(self, name, value):
        arr = self.__dict__.get("_arr")
        i = self.__dict__.get("index")
        if (arr is not None and i is not None
                and name in arr.struct_class.__BHAStructAttrs__):
            ftype = arr.struct_class.__BHAStructAttrs__[name]
            if not isinstance(value, ftype):
                value = ftype(value)
            arr.attrs[name][i] = value
            return
        object.__setattr__(self, name, value)

    def __init__(self, *args, **kwargs):
        cls = self.__class__
        if len(args) == 1 and not kwargs and isinstance(args[0], (dict, BHA_Struct)):
            src = args[0]
            if isinstance(src, dict):
                for k, v in src.items():
                    setattr(self, k, v)
            else:
                for k in cls.__BHAStructAttrs__:
                    setattr(self, k, getattr(src, k))
            return
        fields = cls.__BHAStructAttrs__
        if len(args) > len(fields):
            raise TypeError(f"{cls.__name__}() takes at most {len(fields)} positional args, got {len(args)}")
        for k, v in zip(fields, args):
            setattr(self, k, v)
        for k, v in kwargs.items():
            setattr(self, k, v)

    def __reduce__(self):
        return (dict, ({k: getattr(self, k) for k in self.__class__.__BHAStructAttrs__},))

    def __repr__(self):
        arr = self.__dict__.get("_arr")
        i = self.__dict__.get("index")
        if arr is None:
            return f"<{type(self).__name__} unbound>"
        fields = ", ".join(f"{k}={arr.attrs[k][i]!r}"
                           for k in arr.struct_class.__BHAStructAttrs__)
        return f"{type(self).__name__}({fields})"

    def __iter__(self):
        arr = self.__dict__.get("_arr")
        i = self.__dict__.get("index")
        if arr is None or i is None:
            raise TypeError(f"{type(self).__name__!r} unbound")
        for k in self.__class__.__BHAStructAttrs__:
            yield arr.attrs[k][i]

    def __eq__(self, other):
        if isinstance(other, BHA_Struct):
            a = self.__dict__.get("_arr"); i = self.__dict__.get("index")
            b = other.__dict__.get("_arr"); j = other.__dict__.get("index")
            if a is None or b is None:
                return NotImplemented
            if type(self) is not type(other):
                return False
            for k in a.struct_class.__BHAStructAttrs__:
                if a.attrs[k][i] != b.attrs[k][j]:
                    return False
            return True
        return NotImplemented

    def __ne__(self, other):
        r = self.__eq__(other)
        return NotImplemented if r is NotImplemented else not r

    def as_dict(self):
        arr = self.__dict__["_arr"]; i = self.__dict__["index"]
        return {k: arr.attrs[k][i] for k in arr.struct_class.__BHAStructAttrs__}


class RowArrayView(MutableSequence, metaclass=ResurrectMeta):
    __slots__ = ("_col", "_row")
    def __init__(self, col, row):
        self._col = col
        self._row = row
    def __len__(self):
        offs = self._col._offsets
        return offs[self._row + 1] - offs[self._row]
    def __getitem__(self, j):
        offs = self._col._offsets
        start = offs[self._row]
        n = offs[self._row + 1] - start
        if isinstance(j, slice):
            idxs = range(*j.indices(n))
            if j.step in (None, 1):
                return self._col._flat[start + idxs.start:start + idxs.stop]
            return self._col._flat_cls(self._col._flat[start + i] for i in idxs)
        if j < 0:
            j += n
        if not (0 <= j < n):
            raise IndexError(j)
        return self._col._flat[start + j]
    def __setitem__(self, j, v):
        offs = self._col._offsets
        start = offs[self._row]
        n = offs[self._row + 1] - start
        if isinstance(j, slice):
            idxs = range(*j.indices(n))
            vals = iter(v)
            for i, val in zip(idxs, vals):
                self._col._flat[start + i] = val
            return
        if j < 0:
            j += n
        if not (0 <= j < n):
            raise IndexError(j)
        self._col._flat[start + j] = v
    def __delitem__(self, j):
        offs = self._col._offsets
        start = offs[self._row]
        n = offs[self._row + 1] - start
        if isinstance(j, slice):
            for i in reversed(range(*j.indices(n))):
                self._col.row_delete(self._row, i)
            return
        if j < 0:
            j += n
        if not (0 <= j < n):
            raise IndexError(j)
        self._col.row_delete(self._row, j)
    def insert(self, j, v):
        n = len(self)
        if j < 0:
            j += n
        j = max(0, min(j, n))
        self._col.row_insert(self._row, j, v)
    def append(self, v):
        self._col.row_insert(self._row, len(self), v)
    def extend(self, iterable):
        for v in iterable:
            self.append(v)
    def pop(self, index=-1):
        n = len(self)
        if not n:
            raise IndexError("pop from empty row")
        if index < 0:
            index += n
        v = self[index]
        self._col.row_delete(self._row, index)
        return v
    def remove(self, v):
        for i, x in enumerate(self):
            if x == v:
                self._col.row_delete(self._row, i)
                return
        raise ValueError(f"{v!r} not in row")
    def reverse(self):
        offs = self._col._offsets
        start = offs[self._row]
        n = offs[self._row + 1] - start
        flat = self._col._flat
        for i in range(n // 2):
            flat[start + i], flat[start + n - 1 - i] = flat[start + n - 1 - i], flat[start + i]
    def clear(self):
        offs = self._col._offsets
        start = offs[self._row]
        n = offs[self._row + 1] - start
        del self._col._flat[start:start + n]
        self._col._lengths[self._row] = 0
        self._col._recompute_offsets()
    def __iadd__(self, other):
        self.extend(other)
        return self
    def __iter__(self):
        offs = self._col._offsets
        start = offs[self._row]
        n = offs[self._row + 1] - start
        return BHA_Iterator(map(self._col._flat.__getitem__, range(start, start + n)))
    def __contains__(self, v):
        offs = self._col._offsets
        start = offs[self._row]
        n = offs[self._row + 1] - start
        for i in range(n):
            if self._col._flat[start + i] == v:
                return True
        return False
    def __eq__(self, other):
        if isinstance(other, RowArrayView):
            return all(map(operator.eq, self, other))
        if isinstance(other, (list, tuple)):
            return all(map(operator.eq, self, other))
        return NotImplemented
    def __repr__(self):
        return f"RowArrayView([{', '.join(map(str, self))}])"


class RowArrayColumn(metaclass=ResurrectMeta):
    def __init__(self, flat_cls, size):
        self._flat = flat_cls([])
        self._lengths = IntHybridArray(repeat(0, size), hash_=False)
        self._offsets = IntHybridArray(repeat(0, size + 1), hash_=False)
        self._flat_cls = flat_cls
    def __len__(self):
        return len(self._lengths)
    def __getitem__(self, row):
        return RowArrayView(self, row)
    def __setitem__(self, row, values):
        old_len = self._lengths[row]
        start = self._offsets[row]
        del self._flat[start:start + old_len]
        cnt = 0
        for v in values:
            self._flat.insert(start, v)
            start += 1
            cnt += 1
        self._lengths[row] = cnt
        off = 0
        for i in range(len(self._lengths)):
            self._offsets[i] = off
            off += self._lengths[i]
        self._offsets[len(self._lengths)] = off
    def insert_row(self, row, values=()):
        nrows = len(self._lengths)
        row = row if row >= 0 else row + nrows
        row = max(0, min(row, nrows))
        cnt = 0
        off = self._offsets[row]
        for v in values:
            self._flat.insert(off, v)
            off += 1
            cnt += 1
        self._lengths.insert(row, cnt)
        self._offsets.insert(row + 1, self._offsets[row] + cnt)
        for i in range(row + 1, len(self._offsets)):
            self._offsets[i] = self._offsets[i - 1] + self._lengths[i - 1]
    def delete_row(self, row):
        nrows = len(self._lengths)
        row = row if row >= 0 else row + nrows
        if not (0 <= row < nrows):
            raise IndexError(row)
        start = self._offsets[row]
        n = self._lengths[row]
        del self._flat[start:start + n]
        del self._lengths[row]
        del self._offsets[row + 1]
        for i in range(row, len(self._offsets)):
            self._offsets[i] = self._offsets[i - 1] + self._lengths[i - 1] if i > 0 else 0
    def _recompute_offsets(self):
        off = 0
        nrows = len(self._lengths)
        for i in range(nrows):
            self._offsets[i] = off
            off += self._lengths[i]
        self._offsets[nrows] = off
    def row_insert(self, row, j, v):
        start = self._offsets[row]
        n = self._lengths[row]
        if j < 0:
            j += n
        j = max(0, min(j, n))
        pos = start + j
        if pos == len(self._flat):
            self._flat.append(v)
        else:
            self._flat.insert(pos, v)
        self._lengths[row] = n + 1
        for i in range(row + 1, len(self._offsets)):
            self._offsets[i] += 1
    def row_delete(self, row, j):
        start = self._offsets[row]
        n = self._lengths[row]
        if j < 0:
            j += n
        del self._flat[start + j]
        self._lengths[row] = n - 1
        for i in range(row + 1, len(self._offsets)):
            self._offsets[i] -= 1
    def __delitem__(self, row):
        self.delete_row(row)
    def insert(self, position, values=()):
        self.insert_row(position, values if values is not None else ())
    def optimize(self):
        if hasattr(self._flat, "optimize"):
            self._flat.optimize()
        self._lengths.optimize()

    def clear(self):
        self._flat = self._flat_cls([])
        self._lengths = IntHybridArray([])
        self._offsets = IntHybridArray([0])

    def swap(self, i, j):
        """交换两行的内容（引用/重建，避免逐位解码）。"""
        n = len(self._lengths)
        if i < 0:
            i += n
        if j < 0:
            j += n
        if not (0 <= i < n and 0 <= j < n):
            raise IndexError("swap row out of range")
        if i == j:
            return
        vi = self._flat[self._offsets[i]:self._offsets[i] + self._lengths[i]]
        vj = self._flat[self._offsets[j]:self._offsets[j] + self._lengths[j]]
        self[i] = vj
        self[j] = vi

    def move(self, idx1, length, idx2):
        """memmove 式：把连续 length 行移到 [idx2, idx2+length)，长度不变。"""
        n = len(self._lengths)
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
        block = [self._flat[self._offsets[r]:self._offsets[r] + self._lengths[r]] for r in range(idx1, idx1 + length)]
        for r in reversed(range(idx1, idx1 + length)):
            del self[r]
        for off, rowvals in enumerate(block):
            self.insert_row(idx2 + off, rowvals)

    def __imul__(self, n):
        n = operator.index(n)
        if n <= 0:
            self.clear()
            return self
        if n == 1:
            return self
        nrows = len(self._lengths)
        flat = self._flat
        offs = self._offsets
        lens = self._lengths
        def _gen():
            for _ in range(n):
                for r in range(nrows):
                    s = offs[r]
                    e = s + lens[r]
                    for i in range(s, e):
                        yield flat[i]
        self._flat = self._flat_cls(_gen())
        self._lengths = IntHybridArray((lens[r] for _ in range(n) for r in range(nrows)), hash_=False)
        off = 0
        new_n = n * nrows
        self._offsets = IntHybridArray(repeat(0, new_n + 1), hash_=False)
        for i in range(new_n):
            self._offsets[i] = off
            off += self._lengths[i % nrows]
        self._offsets[new_n] = off
        return self

    def __mul__(self, n):
        n = operator.index(n)
        if n <= 0:
            return RowArrayColumn(self._flat_cls, 0)
        r = RowArrayColumn(self._flat_cls, 0)
        for _ in range(n):
            for i in range(len(self)):
                r.insert_row(len(r), self._flat[self._offsets[i]:self._offsets[i] + self._lengths[i]])
        return r

    __rmul__ = __mul__


class StructHybridArray(MutableSequence, metaclass=ResurrectMeta):
    sort = twg_sort
    def __init__(self, struct_class, size=0, items=None, hash_=True):
        self.struct_class = struct_class
        self._is_raw = not (isinstance(struct_class, type) and issubclass(struct_class, BHA_Struct))
        if self._is_raw:
            self._raw = [None] * size
        else:
            self.attrs: dict = {}
            for fn, ft in struct_class.__BHAStructAttrs__.items():
                self.attrs[fn] = self._build_storage(ft, size, hash_=hash_)
            self._proxies: WeakValueDictionary = WeakValueDictionary()
            self._nproxies = 0
        if items:
            self.extend(items)

    @staticmethod
    def _build_storage(ft, size, hash_=True):
        if ft is bool or ft is BHA_bool or ft is BHA_Bool:
            return FalsesArray(size, hash_=hash_)
        if ft is int or ft is BHA_Char:
            return IntHybridArray([0], Type=BHA_Char if ft is BHA_Char else int, hash_=hash_) * size
        if ft is float or ft is BHA_Float:
            return FloatHybridArray([0.0], hash_=hash_) * size
        if ft is IntHybridArray:
            return RowArrayColumn(IntHybridArray, size)
        if ft is FloatHybridArray:
            return RowArrayColumn(FloatHybridArray, size)
        if ft is BoolHybridArr or ft is BoolHybridArray:
            return RowArrayColumn(BoolHybridArr, size)
        if isinstance(ft, type) and issubclass(ft, BHA_Struct):
            return StructHybridArray(ft, size)
        if ft is StructHybridArray or getattr(ft, "__origin__", None) is StructHybridArray:
            args = getattr(ft, "__args__", None)
            if not args or not isinstance(args[0], type) or not issubclass(args[0], BHA_Struct):
                raise TypeError("StructHybridArray field needs parameterization")
            return StructHybridArray(args[0], size)
        origin = getattr(ft, "__origin__", None)
        if ft is list or origin is list:
            return [None] * size
        return StructHybridArray(ft, size)

    def _evict(self, key):
        old = self._proxies.pop(key, None)
        if old is None:
            return
        self._nproxies -= 1
        tmp = StructHybridArray(self.struct_class, 1)
        for k in self.struct_class.__BHAStructAttrs__:
            tmp.attrs[k][0] = self.attrs[k][key]
        object.__setattr__(old, "_arr", tmp)
        object.__setattr__(old, "index", 0)

    def __del__(self):
        try:
            if self._nproxies == 0:
                return
        except AttributeError:
            return
        try:
            proxies = dict(self._proxies)
        except Exception:
            return
        for key, p in proxies.items():
            try:
                tmp = StructHybridArray(self.struct_class, 1)
                for k in self.struct_class.__BHAStructAttrs__:
                    tmp.attrs[k][0] = self.attrs[k][key]
                object.__setattr__(p, "_arr", tmp)
                object.__setattr__(p, "index", 0)
            except Exception:
                pass
        try:
            self._proxies.clear()
        except Exception:
            pass

    def __len__(self):
        if self._is_raw:
            return len(self._raw)
        return len(next(iter(self.attrs.values())))

    def __hash__(self):
        if self._is_raw:
            h = 0
            for v in self._raw:
                h += hash(v)
            return h
        h = 0
        for col in self.attrs.values():
            h += hash(col)
        return h

    def __eq__(self, o):
        if isinstance(o, StructHybridArray):
            if len(self) != len(o):
                return False
            if self._is_raw and o._is_raw:
                return self._raw == o._raw
            if self._is_raw or o._is_raw:
                for i in range(len(self)):
                    if self[i] != o[i]:
                        return False
                return True
            return all(self.attrs[k] == o.attrs[k] for k in self.attrs)
        if isinstance(o, Iterable) and not isinstance(o, (str, bytes)):
            if len(self) != len(o):
                return False
            for i, v in enumerate(o):
                if isinstance(v, dict) and not self._is_raw:
                    v = self.struct_class(v)
                if self[i] != v:
                    return False
            return True
        return NotImplemented

    def getdict(self, i):
        if self._is_raw:
            v = self._raw[i]
            return v if isinstance(v, dict) else {'value': v}
        return {k: self.attrs[k][i] for k in self.attrs}

    def setdict(self, i, d):
        i = i if i >= 0 else i + len(self)
        if not (0 <= i < len(self)):
            raise IndexError(f"index {i} out of range")
        if self._is_raw:
            cur = self._raw[i]
            if isinstance(cur, dict) and isinstance(d, dict):
                cur.update(d)
                return
            self._raw[i] = d.get('value', d)
            return
        for k, v in d.items():
            col = self.attrs.get(k)
            if col is None:
                raise KeyError(f"未知属性: {k}")
            if isinstance(col, IntHybridArray):
                col[i] = int(v)
            elif isinstance(col, BoolHybridArr):
                col[i] = bool(v)
            else:
                col[i] = v

    def __getitem__(self, key):
        if isinstance(key, slice):
            if self._is_raw:
                return self._raw[key]
            tmp = StructHybridArray(self.struct_class, 0)
            tmp.attrs = {k: col[key] for k, col in self.attrs.items()}
            tmp._proxies = WeakValueDictionary()
            tmp._nproxies = 0
            return tmp
        key = key if key >= 0 else key + len(self)
        if not (0 <= key < len(self)):
            raise IndexError(f"index {key} out of range")
        if self._is_raw:
            return self._raw[key]
        p = self._proxies.get(key)
        if p is None:
            p = self.struct_class.__new__(self.struct_class)
            object.__setattr__(p, "_arr", _wproxy(self))
            object.__setattr__(p, "index", key)
            self._proxies[key] = p
        self._nproxies += 1
        return p

    def __setitem__(self, key, value):
        if isinstance(key, slice):
            if self._is_raw:
                # raw 模式：列表切片语义（右侧迭代器/数组直接赋给 _raw 列表）
                self._raw[key] = value
                return
            start, stop, step = key.indices(len(self))
            idxs = range(start, stop, step)
            if isinstance(value, StructHybridArray) and value.struct_class is self.struct_class and len(value) == len(idxs):
                for k, col in self.attrs.items():
                    col[key] = value.attrs[k]
                return
            if isinstance(value, (list, tuple)):
                if step == 1:
                    if len(value) == len(idxs):
                        for k, col in self.attrs.items():
                            col[key] = (row[k] for row in (_item_to_row(v, self.struct_class) for v in value))
                        return
                    for k, col in self.attrs.items():
                        del col[start:start + len(idxs)]
                    for off, r in enumerate((_item_to_row(v, self.struct_class) for v in value)):
                        for k, col in self.attrs.items():
                            col.insert(start + off, r[k])
                    return
                if len(value) != len(idxs):
                    raise ValueError("slice assignment length mismatch")
                for i, v in zip(idxs, value):
                    self[i] = v
            else:
                for i in idxs:
                    self[i] = value
            return
        key = key if key >= 0 else key + len(self)
        if not (0 <= key < len(self)):
            raise IndexError(f"index {key} out of range")
        if self._is_raw:
            self._raw[key] = value
            return
        self._evict(key)
        row = _item_to_row(value, self.struct_class)
        for k, v in row.items():
            self.attrs[k][key] = v

    def __delitem__(self, key):
        if isinstance(key, slice):
            start, stop, step = key.indices(len(self))
            for i in reversed(range(start, stop, step)):
                del self[i]
            return
        key = key if key >= 0 else key + len(self)
        if not (0 <= key < len(self)):
            raise IndexError(f"delete index {key} out of range")
        if self._is_raw:
            del self._raw[key]
            return
        self._evict(key)
        for storage in self.attrs.values():
            del storage[key]
        if self._nproxies == 0:
            return
        new_proxies = WeakValueDictionary()
        self._nproxies = 0
        for i, p in self._proxies.items():
            if i == key:
                continue
            if i > key:
                object.__setattr__(p, "index", i - 1)
                new_proxies[i - 1] = p
            else:
                new_proxies[i] = p
        self._proxies = new_proxies

    def insert(self, position, item):
        n = len(self)
        position = position if position >= 0 else position + n
        position = max(0, min(position, n))
        if self._is_raw:
            self._raw.insert(position, item)
            return
        row = _item_to_row(item, self.struct_class)
        for k, storage in self.attrs.items():
            storage.insert(position, row.get(k))
        if self._nproxies == 0:
            return
        new_proxies = WeakValueDictionary()
        self._nproxies = 0
        for i, p in self._proxies.items():
            if i >= position:
                object.__setattr__(p, "index", i + 1)
                new_proxies[i + 1] = p
            else:
                new_proxies[i] = p
        self._proxies = new_proxies

    def swap(self, idx1, idx2):
        """交换两行结构体：raw 直接交换引用，attrs 对每列做位级/引用交换。"""
        n = len(self)
        if idx1 < 0:
            idx1 += n
        if idx2 < 0:
            idx2 += n
        if not (0 <= idx1 < n and 0 <= idx2 < n):
            raise IndexError("swap index out of range")
        if idx1 == idx2:
            return
        if self._is_raw:
            self._raw[idx1], self._raw[idx2] = self._raw[idx2], self._raw[idx1]
            return
        for col in self.attrs.values():
            if hasattr(col, "swap"):
                col.swap(idx1, idx2)
            else:
                col[idx1], col[idx2] = col[idx2], col[idx1]

    def move(self, idx1, length, idx2):
        """memmove 式移动 length 行到 [idx2, idx2+length)，长度不变。"""
        n = len(self)
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
        if self._is_raw:
            block = self._raw[idx1:idx1 + length]
            del self._raw[idx1:idx1 + length]
            self._raw[idx2:idx2] = block
            return
        for col in self.attrs.values():
            if hasattr(col, "move"):
                col.move(idx1, length, idx2)
            else:
                block = col[idx1:idx1 + length]
                del col[idx1:idx1 + length]
                col[idx2:idx2] = block

    def append_row(self, pos_val, len_val, pow_val):
        p = len(self)
        self.attrs["pos"].insert(p, pos_val)
        self.attrs["length"].insert(p, len_val)
        self.attrs["power"].insert(p, pow_val)

    def append(self, item):
        self.insert(len(self), item)

    def extend(self, iterable):
        for v in iterable:
            self.append(v)

    def copy(self):
        cp = StructHybridArray(self.struct_class, size=0)
        cp.extend(self)
        return cp

    def pop(self, index=-1):
        n = len(self)
        index = index if index >= 0 else index + n
        if not (0 <= index < n):
            raise IndexError("pop index out of range")
        if self._is_raw:
            v = self._raw[index]
            del self._raw[index]
            return v
        p = self[index]
        self._evict(index)
        del self[index]
        return p

    def remove(self, item):
        try:
            idx = self.index(item)
        except ValueError:
            raise ValueError(f"{item!r} not in list")
        del self[idx]

    def optimize(self):
        if self._is_raw:
            return
        for storage in self.attrs.values():
            if hasattr(storage, "optimize"):
                storage.optimize()

    def clear(self):
        if self._is_raw:
            self._raw.clear()
            return
        for storage in self.attrs.values():
            try:
                storage.clear()
            except Exception:
                pass
        self._proxies.clear()

    def reverse(self):
        n = len(self)
        for i in range(n // 2):
            self[i], self[n - 1 - i] = self[n - 1 - i], self[i]

    def index(self, item, start=0, stop=None):
        n = len(self)
        if stop is None:
            stop = n
        start = max(0, start if start >= 0 else start + n)
        stop = min(n, stop if stop >= 0 else stop + n)
        row = _item_to_row(item, self.struct_class)
        for i in range(start, stop):
            if all(self.attrs[k][i] == v for k, v in row.items()):
                return i
        raise ValueError(f"{item!r} not in list")

    def count(self, item):
        row = _item_to_row(item, self.struct_class)
        return sum(1 for i in range(len(self))
                   if all(self.attrs[k][i] == v for k, v in row.items()))

    def __contains__(self, item):
        try:
            self.index(item)
            return True
        except ValueError:
            return False

    def __iter__(self):
        return BHA_Iterator(map(self.__getitem__, range(len(self))))

    def __reversed__(self):
        return BHA_Iterator(map(self.__getitem__, range(len(self) - 1, -1, -1)))

    def __deepcopy__(self, memo):
        return type(self)(self.struct_class, 0, iter(self))

    def __copy__(self):
        return type(self)(self.struct_class, 0, iter(self))

    def __getstate__(self):
        if self._is_raw:
            return (self.struct_class, self._raw)
        return (self.struct_class, self.attrs)

    def __setstate__(self, state):
        self.struct_class, payload = state
        self._is_raw = not (isinstance(self.struct_class, type) and issubclass(self.struct_class, BHA_Struct))
        if self._is_raw:
            self._raw = payload
        else:
            self.attrs = payload
            self._proxies = WeakValueDictionary()
            self._nproxies = 0

    def __iadd__(self, other):
        self.extend(other)
        return self

    def __add__(self, other):
        r = StructHybridArray(self.struct_class, 0)
        r.extend(self); r.extend(other)
        return r

    def __imul__(self, n):
        n = operator.index(n)
        if n <= 0:
            self.clear()
            return self
        if self._is_raw:
            self._raw *= n
        else:
            for k, col in self.attrs.items():
                self.attrs[k] = col * n
        return self

    def __mul__(self, n):
        r = StructHybridArray(self.struct_class, 0)
        r.extend(self)
        r *= n
        return r

    __rmul__ = __mul__

    def __str__(self):
        return f"StructHybridArray([{', '.join(map(repr, self))}])"

    __repr__ = __str__


class BHA_Complex(BHA_Struct):
    __BHAStructAttrs__ = {"real": float, "imag": float}
    def __init__(self, real=0.0, imag=0.0):
        if isinstance(real, complex):
            real, imag = real.real, real.imag
        elif isinstance(real, (dict, BHA_Struct)):
            d = real.as_dict() if isinstance(real, BHA_Struct) else real
            real = d.get("real", 0.0); imag = d.get("imag", 0.0)
        self.real, self.imag = real, imag

    def __hash__(self):
        return hash((float(self.real), float(self.imag)))

    def __eq__(self, o):
        if isinstance(o, BHA_Struct):
            return (float(self.real), float(self.imag)) == (float(o.real), float(o.imag))
        if isinstance(o, (int, float, complex)):
            return complex(float(self.real), float(self.imag)) == o
        return NotImplemented
    def conjugate(self): return complex(float(self.real), -float(self.imag))
    def magnitude(self): return (float(self.real) ** 2 + float(self.imag) ** 2) ** 0.5
    def to_complex(self): return complex(float(self.real), float(self.imag))
    def __abs__(self): return self.magnitude()
    def __complex__(self): return self.to_complex()
    def __add__(self, o):
        if isinstance(o, BHA_Struct):
            return complex(float(self.real) + float(o.real), float(self.imag) + float(o.imag))
        return complex(float(self.real) + float(o), float(self.imag))
    def __radd__(self, o): return self + o
    def __sub__(self, o):
        if isinstance(o, BHA_Struct):
            return complex(float(self.real) - float(o.real), float(self.imag) - float(o.imag))
        return complex(float(self.real) - float(o), float(self.imag))
    def __rsub__(self, o):
        if isinstance(o, BHA_Struct):
            return complex(float(o.real) - float(self.real), float(o.imag) - float(self.imag))
        return complex(float(o) - float(self.real), -float(self.imag))
    def __mul__(self, o):
        if isinstance(o, BHA_Struct):
            a, b = float(self.real), float(self.imag)
            c, d = float(o.real), float(o.imag)
            return complex(a * c - b * d, a * d + b * c)
        return complex(float(self.real) * float(o), float(self.imag) * float(o))
    def __rmul__(self, o): return self * o
    def __truediv__(self, o):
        if isinstance(o, BHA_Struct):
            a, b = float(self.real), float(self.imag)
            c, d = float(o.real), float(o.imag)
            denom = c * c + d * d
            return complex((a * c + b * d) / denom, (b * c - a * d) / denom)
        return complex(float(self.real) / float(o), float(self.imag) / float(o))
    def __neg__(self): return complex(-float(self.real), -float(self.imag))
    def __pos__(self): return self.to_complex()


class BHA_Slice(BHA_Struct):
    __BHAStructAttrs__ = {"start": int, "stop": int, "step": int}
    def __init__(self, start=0, stop=None, step=1):
        if isinstance(start, (dict, BHA_Struct)):
            d = start.as_dict() if isinstance(start, BHA_Struct) else start
            self.start = d.get("start", 0); self.stop = d.get("stop", 0); self.step = d.get("step", 1)
            return
        if stop is None:
            start, stop = 0, start
        self.start, self.stop, self.step = start, stop, step
    def indices(self, n): return slice(self.start, self.stop, self.step).indices(n)


class BHA_Rect(BHA_Struct):
    __BHAStructAttrs__ = {"x": int, "y": int, "w": int, "h": int}
    def area(self): return int(self.w) * int(self.h)
    def contains(self, x, y):
        return int(self.x) <= x < int(self.x) + int(self.w) and int(self.y) <= y < int(self.y) + int(self.h)
    def __eq__(self, o):
        if isinstance(o, BHA_Rect):
            return (int(self.x) == int(o.x) and int(self.y) == int(o.y)
                    and int(self.w) == int(o.w) and int(self.h) == int(o.h))
        return NotImplemented


class BHA_RGBA(BHA_Struct):
    __BHAStructAttrs__ = {"r": BHA_Char, "g": BHA_Char, "b": BHA_Char, "a": BHA_Char}
    def __init__(self, r=0, g=0, b=0, a=255):
        if isinstance(r, (dict, BHA_Struct)):
            d = r.as_dict() if isinstance(r, BHA_Struct) else r
            r = d.get("r", 0); g = d.get("g", 0); b = d.get("b", 0); a = d.get("a", 255)
        self.r, self.g, self.b, self.a = r, g, b, a
    def to_hex(self):
        return "#{:02X}{:02X}{:02X}{:02X}".format(max(0, min(255, int(self.r))), max(0, min(255, int(self.g))), max(0, min(255, int(self.b))), max(0, min(255, int(self.a))))
    def __eq__(self, o):
        if isinstance(o, BHA_RGBA):
            return (int(self.r) == int(o.r) and int(self.g) == int(o.g)
                    and int(self.b) == int(o.b) and int(self.a) == int(o.a))
        return NotImplemented


class BHA_RGB(BHA_Struct):
    __BHAStructAttrs__ = {"r": BHA_Char, "g": BHA_Char, "b": BHA_Char}
    def to_hex(self): return "#{:02X}{:02X}{:02X}".format(max(0, min(255, int(self.r))), max(0, min(255, int(self.g))), max(0, min(255, int(self.b))))


class BHA_Vec2(BHA_Struct):
    __BHAStructAttrs__ = {"x": float, "y": float}
    def dot(self, o): return float(self.x) * float(o.x) + float(self.y) * float(o.y)
    def length(self): return (float(self.x) ** 2 + float(self.y) ** 2) ** 0.5
    def normalized(self):
        n = self.length()
        return BHA_Vec2(0.0, 0.0) if n == 0 else BHA_Vec2(float(self.x) / n, float(self.y) / n)
    def __add__(self, o): return BHA_Vec2(float(self.x) + float(o.x), float(self.y) + float(o.y))
    def __sub__(self, o): return BHA_Vec2(float(self.x) - float(o.x), float(self.y) - float(o.y))
    def __mul__(self, s): return BHA_Vec2(float(self.x) * float(s), float(self.y) * float(s))
    def __rmul__(self, s): return self * s
    def __neg__(self): return BHA_Vec2(-float(self.x), -float(self.y))


class BHA_Vec3(BHA_Struct):
    __BHAStructAttrs__ = {"x": float, "y": float, "z": float}
    def dot(self, o): return float(self.x) * float(o.x) + float(self.y) * float(o.y) + float(self.z) * float(o.z)
    def cross(self, o):
        return BHA_Vec3(float(self.y) * float(o.z) - float(self.z) * float(o.y),
                        float(self.z) * float(o.x) - float(self.x) * float(o.z),
                        float(self.x) * float(o.y) - float(self.y) * float(o.x))
    def length(self): return (float(self.x) ** 2 + float(self.y) ** 2 + float(self.z) ** 2) ** 0.5
    def normalized(self):
        n = self.length()
        return BHA_Vec3(0.0, 0.0, 0.0) if n == 0 else BHA_Vec3(float(self.x) / n, float(self.y) / n, float(self.z) / n)
    def normalize(self):
        return self.normalized()
    def __add__(self, o): return BHA_Vec3(float(self.x) + float(o.x), float(self.y) + float(o.y), float(self.z) + float(o.z))
    def __sub__(self, o): return BHA_Vec3(float(self.x) - float(o.x), float(self.y) - float(o.y), float(self.z) - float(o.z))
    def __mul__(self, s): return BHA_Vec3(float(self.x) * float(s), float(self.y) * float(s), float(self.z) * float(s))
    def __rmul__(self, s): return self * s
    def __neg__(self): return BHA_Vec3(-float(self.x), -float(self.y), -float(self.z))


class BHA_Vec4(BHA_Struct):
    __BHAStructAttrs__ = {"x": float, "y": float, "z": float, "w": float}
    def dot(self, o):
        return (float(self.x) * float(o.x) + float(self.y) * float(o.y)
                + float(self.z) * float(o.z) + float(self.w) * float(o.w))
    def length(self):
        return (float(self.x) ** 2 + float(self.y) ** 2 + float(self.z) ** 2 + float(self.w) ** 2) ** 0.5
    def normalized(self):
        n = self.length()
        return BHA_Vec4(0.0, 0.0, 0.0, 0.0) if n == 0 else BHA_Vec4(float(self.x) / n, float(self.y) / n, float(self.z) / n, float(self.w) / n)
    def __add__(self, o): return BHA_Vec4(float(self.x) + float(o.x), float(self.y) + float(o.y), float(self.z) + float(o.z), float(self.w) + float(o.w))
    def __sub__(self, o): return BHA_Vec4(float(self.x) - float(o.x), float(self.y) - float(o.y), float(self.z) - float(o.z), float(self.w) - float(o.w))
    def __mul__(self, s): return BHA_Vec4(float(self.x) * float(s), float(self.y) * float(s), float(self.z) * float(s), float(self.w) * float(s))
    def __rmul__(self, s): return self * s
    def __neg__(self): return BHA_Vec4(-float(self.x), -float(self.y), -float(self.z), -float(self.w))


class BHA_Point(BHA_Struct):
    __BHAStructAttrs__ = {"x": int, "y": int}
    def __add__(self, o): return BHA_Point(int(self.x) + int(o.x), int(self.y) + int(o.y))
    def __sub__(self, o): return BHA_Point(int(self.x) - int(o.x), int(self.y) - int(o.y))


class BHA_Point3D(BHA_Struct):
    __BHAStructAttrs__ = {"x": int, "y": int, "z": int}
    def __add__(self, o): return BHA_Point3D(int(self.x) + int(o.x), int(self.y) + int(o.y), int(self.z) + int(o.z))
    def __sub__(self, o): return BHA_Point3D(int(self.x) - int(o.x), int(self.y) - int(o.y), int(self.z) - int(o.z))


class BHA_Quaternion(BHA_Struct):
    __BHAStructAttrs__ = {"x": float, "y": float, "z": float, "w": float}
    def __init__(self, x=0.0, y=0.0, z=0.0, w=1.0):
        if isinstance(x, (dict, BHA_Struct)):
            d = x.as_dict() if isinstance(x, BHA_Struct) else x
            x = d.get("x", 0.0); y = d.get("y", 0.0); z = d.get("z", 0.0); w = d.get("w", 1.0)
        self.x, self.y, self.z, self.w = x, y, z, w
    def conjugate(self): return BHA_Quaternion(float(self.x), float(self.y), float(self.z), -float(self.w))
    def __mul__(self, o):
        if isinstance(o, BHA_Struct):
            a1, b1, c1, d1 = float(self.x), float(self.y), float(self.z), float(self.w)
            a2, b2, c2, d2 = float(o.x), float(o.y), float(o.z), float(o.w)
            return BHA_Quaternion(d1 * a2 + a1 * d2 + b1 * c2 - c1 * b2,
                                  d1 * b2 - a1 * c2 + b1 * d2 + c1 * a2,
                                  d1 * c2 + a1 * b2 - b1 * a2 + c1 * d2,
                                  d1 * d2 - a1 * a2 - b1 * b2 - c1 * c2)
        return BHA_Quaternion(float(self.x) * float(o), float(self.y) * float(o),
                              float(self.z) * float(o), float(self.w) * float(o))
    __rmul__ = __mul__
    def rotate(self, v):
        x, y, z = (float(v.x), float(v.y), float(v.z)) if isinstance(v, BHA_Struct) else (float(v[0]), float(v[1]), float(v[2]))
        qx, qy, qz, qw = float(self.x), float(self.y), float(self.z), float(self.w)
        tx = 2 * (qy * z - qz * y)
        ty = 2 * (qz * x - qx * z)
        tz = 2 * (qx * y - qy * x)
        return BHA_Vec3(x + qw * tx + (qy * tz - qz * ty),
                        y + qw * ty + (qz * tx - qx * tz),
                        z + qw * tz + (qx * ty - qy * tx))


class BHA_Range(BHA_Struct):
    __BHAStructAttrs__ = {"start": int, "stop": int, "step": int}
    def __init__(self, start=0, stop=None, step=1):
        if isinstance(start, (dict, BHA_Struct)):
            d = start.as_dict() if isinstance(start, BHA_Struct) else start
            self.start = d.get("start", 0); self.stop = d.get("stop", 0); self.step = d.get("step", 1)
            return
        if stop is None:
            start, stop = 0, start
        self.start, self.stop, self.step = start, stop, step
    def contains(self, v): return int(self.start) <= v < int(self.stop)
    def length(self): return int(self.stop) - int(self.start)
    def to_slice(self): return slice(int(self.start), int(self.stop), int(self.step))


class BHA_Time(BHA_Struct):
    __BHAStructAttrs__ = {"hour": int, "minute": int, "second": int}
    def __init__(self, hour=None, minute=None, second=None):
        if hour is None and minute is None and second is None:
            now = _datetime.datetime.now()
            hour, minute, second = now.hour, now.minute, now.second
        elif isinstance(hour, str):
            parts = hour.split(":")
            if len(parts) not in (2, 3):
                raise ValueError(f"invalid time string {hour!r}")
            hour, minute = int(parts[0]), int(parts[1])
            second = int(parts[2]) if len(parts) == 3 else 0
        elif isinstance(hour, (dict, BHA_Struct)):
            d = hour.as_dict() if isinstance(hour, BHA_Struct) else hour
            hour = d.get("hour", 0); minute = d.get("minute", 0); second = d.get("second", 0)
        else:
            hour = 0 if hour is None else hour
            minute = 0 if minute is None else minute
            second = 0 if second is None else second
        if not (0 <= hour < 24 and 0 <= minute < 60 and 0 <= second < 60):
            raise ValueError(f"invalid time {hour}:{minute}:{second}")
        self.hour, self.minute, self.second = hour, minute, second
    def to_seconds(self): return int(self.hour) * 3600 + int(self.minute) * 60 + int(self.second)
    def __str__(self): return f"{int(self.hour):02d}:{int(self.minute):02d}:{int(self.second):02d}"
    def isoformat(self): return self.__str__()
    def __lt__(self, o): return (int(self.hour), int(self.minute), int(self.second)) < (int(o.hour), int(o.minute), int(o.second))
    def __le__(self, o): return (int(self.hour), int(self.minute), int(self.second)) <= (int(o.hour), int(o.minute), int(o.second))


class BHA_Date(BHA_Struct):
    __BHAStructAttrs__ = {"year": int, "month": int, "day": int}
    def __init__(self, year=None, month=None, day=None):
        if year is None and month is None and day is None:
            now = _datetime.datetime.now()
            year, month, day = now.year, now.month, now.day
        elif isinstance(year, str):
            parts = year.split("-")
            if len(parts) != 3:
                raise ValueError(f"invalid date string {year!r}")
            year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
        elif isinstance(year, (dict, BHA_Struct)):
            d = year.as_dict() if isinstance(year, BHA_Struct) else year
            year = d.get("year", 0); month = d.get("month", 0); day = d.get("day", 0)
        else:
            year = 0 if year is None else year
            month = 0 if month is None else month
            day = 0 if day is None else day
        leap = year % 400 == 0 or (year % 4 == 0 and year % 100 != 0)
        dim = [31, 29 if leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        if not (1 <= month <= 12 and 1 <= day <= dim[month - 1]):
            raise ValueError(f"invalid date {year}-{month:02d}-{day:02d}")
        self.year, self.month, self.day = year, month, day
    def __str__(self): return f"{int(self.year):04d}-{int(self.month):02d}-{int(self.day):02d}"
    def isoformat(self): return self.__str__()
    def __lt__(self, o): return (int(self.year), int(self.month), int(self.day)) < (int(o.year), int(o.month), int(o.day))
    def __le__(self, o): return (int(self.year), int(self.month), int(self.day)) <= (int(o.year), int(o.month), int(o.day))
    def to_datetime(self):
        return _datetime.date(int(self.year), int(self.month), int(self.day))
    def sub(self, o):
        return (self.to_datetime() - o.to_datetime()).days


class BHA_DateTime(BHA_Struct):
    __BHAStructAttrs__ = {"year": int, "month": int, "day": int, "hour": int, "minute": int, "second": int}
    def __init__(self, year=None, month=None, day=None, hour=None, minute=None, second=None):
        if year is None and month is None and day is None and hour is None and minute is None and second is None:
            now = _datetime.datetime.now()
            year, month, day = now.year, now.month, now.day
            hour, minute, second = now.hour, now.minute, now.second
        elif isinstance(year, str):
            s = year
            if "T" in s:
                date_part, time_part = s.split("T", 1)
            elif " " in s:
                date_part, time_part = s.split(" ", 1)
            else:
                date_part, time_part = s, "00:00:00"
            y, m, d = (int(x) for x in date_part.split("-"))
            hh, mm, ss = (int(x) for x in time_part.split(":"))
            year, month, day, hour, minute, second = y, m, d, hh, mm, ss
        elif isinstance(year, (dict, BHA_Struct)):
            d = year.as_dict() if isinstance(year, BHA_Struct) else year
            year = d.get("year", 0); month = d.get("month", 0); day = d.get("day", 0)
            hour = d.get("hour", 0); minute = d.get("minute", 0); second = d.get("second", 0)
        else:
            year = 0 if year is None else year
            month = 0 if month is None else month
            day = 0 if day is None else day
            hour = 0 if hour is None else hour
            minute = 0 if minute is None else minute
            second = 0 if second is None else second
        leap = year % 400 == 0 or (year % 4 == 0 and year % 100 != 0)
        dim = [31, 29 if leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        if not (1 <= month <= 12 and 1 <= day <= dim[month - 1]):
            raise ValueError(f"invalid date {year}-{month:02d}-{day:02d}")
        if not (0 <= hour < 24 and 0 <= minute < 60 and 0 <= second < 60):
            raise ValueError(f"invalid time {hour}:{minute}:{second}")
        self.year, self.month, self.day = year, month, day
        self.hour, self.minute, self.second = hour, minute, second
    def __str__(self):
        return (f"{int(self.year):04d}-{int(self.month):02d}-{int(self.day):02d} "
                f"{int(self.hour):02d}:{int(self.minute):02d}:{int(self.second):02d}")
    def isoformat(self):
        return (f"{int(self.year):04d}-{int(self.month):02d}-{int(self.day):02d}"
                f"T{int(self.hour):02d}:{int(self.minute):02d}:{int(self.second):02d}")
    def __lt__(self, o):
        a = (int(self.year), int(self.month), int(self.day),
             int(self.hour), int(self.minute), int(self.second))
        b = (int(o.year), int(o.month), int(o.day),
             int(o.hour), int(o.minute), int(o.second))
        return a < b


class BHA_BBox(BHA_Struct):
    __BHAStructAttrs__ = {"min_x": int, "min_y": int, "max_x": int, "max_y": int}
    def contains(self, x, y): return int(self.min_x) <= x <= int(self.max_x) and int(self.min_y) <= y <= int(self.max_y)
    def area(self): return (int(self.max_x) - int(self.min_x)) * (int(self.max_y) - int(self.min_y))


class BHA_UV(BHA_Struct):
    __BHAStructAttrs__ = {"u": float, "v": float}
    def flip_v(self): return BHA_UV(float(self.u), 1.0 - float(self.v))
    def __add__(self, o): return BHA_UV(float(self.u) + float(o.u), float(self.v) + float(o.v))


class BHA_ColorF(BHA_Struct):
    __BHAStructAttrs__ = {"r": float, "g": float, "b": float, "a": float}
    def __init__(self, r=0.0, g=0.0, b=0.0, a=1.0):
        if isinstance(r, (dict, BHA_Struct)):
            d = r.as_dict() if isinstance(r, BHA_Struct) else r
            r = d.get("r", 0.0); g = d.get("g", 0.0); b = d.get("b", 0.0); a = d.get("a", 1.0)
        self.r, self.g, self.b, self.a = r, g, b, a
    def to_rgba8(self):
        return (max(0, min(255, round(float(self.r) * 255))), max(0, min(255, round(float(self.g) * 255))), max(0, min(255, round(float(self.b) * 255))), max(0, min(255, round(float(self.a) * 255))))
    def to_hex(self):
        r, g, b, a = self.to_rgba8()
        return "#{:02X}{:02X}{:02X}{:02X}".format(r, g, b, a)
    @classmethod
    def from_hex(cls, s):
        s = s.lstrip('#')
        if len(s) == 6:
            r, g, b = (int(s[i:i + 2], 16) for i in (0, 2, 4))
            return cls(r / 255.0, g / 255.0, b / 255.0, 1.0)
        if len(s) == 8:
            r, g, b, a = (int(s[i:i + 2], 16) for i in (0, 2, 4, 6))
            return cls(r / 255.0, g / 255.0, b / 255.0, a / 255.0)
        raise ValueError(f"无效 hex 颜色: #{s}")
    def to_rgb(self):
        r, g, b, _ = self.to_rgba8()
        return BHA_RGB(r, g, b)
    def to_rgba(self):
        r, g, b, a = self.to_rgba8()
        return BHA_RGBA(r, g, b, a)
    def to_hsv(self):
        h, s, v = _colorsys.rgb_to_hsv(float(self.r), float(self.g), float(self.b))
        return BHA_HSV(h, s, v)
    def to_hsva(self):
        h, s, v = _colorsys.rgb_to_hsv(float(self.r), float(self.g), float(self.b))
        return BHA_HSVA(h, s, v, float(self.a))
    def lerp(self, o, t):
        t = float(t)
        return BHA_ColorF(float(self.r) + (float(o.r) - float(self.r)) * t,
                          float(self.g) + (float(o.g) - float(self.g)) * t,
                          float(self.b) + (float(o.b) - float(self.b)) * t,
                          float(self.a) + (float(o.a) - float(self.a)) * t)


class BHA_Size(BHA_Struct):
    __BHAStructAttrs__ = {"w": int, "h": int}
    def area(self): return int(self.w) * int(self.h)


class BHA_SizeF(BHA_Struct):
    __BHAStructAttrs__ = {"w": float, "h": float}
    def area(self): return float(self.w) * float(self.h)


class BHA_Circle(BHA_Struct):
    __BHAStructAttrs__ = {"x": float, "y": float, "r": float}
    def area(self): return _math.pi * float(self.r) ** 2
    def contains(self, x, y):
        dx = float(x) - float(self.x); dy = float(y) - float(self.y)
        return dx * dx + dy * dy <= float(self.r) ** 2


class BHA_Sphere(BHA_Struct):
    __BHAStructAttrs__ = {"x": float, "y": float, "z": float, "r": float}
    def volume(self): return (4.0 / 3.0) * _math.pi * float(self.r) ** 3
    def contains(self, x, y, z):
        dx = float(x) - float(self.x); dy = float(y) - float(self.y); dz = float(z) - float(self.z)
        return dx * dx + dy * dy + dz * dz <= float(self.r) ** 2


class BHA_Line(BHA_Struct):
    __BHAStructAttrs__ = {"x1": float, "y1": float, "x2": float, "y2": float}
    def length(self):
        dx = float(self.x2) - float(self.x1); dy = float(self.y2) - float(self.y1)
        return (dx * dx + dy * dy) ** 0.5
    def midpoint(self):
        return BHA_Vec2((float(self.x1) + float(self.x2)) / 2, (float(self.y1) + float(self.y2)) / 2)


class BHA_Polar(BHA_Struct):
    __BHAStructAttrs__ = {"angle": float, "radius": float}
    def to_xy(self):
        return BHA_Vec2(float(self.radius) * _math.cos(float(self.angle)), float(self.radius) * _math.sin(float(self.angle)))


class BHA_HSV(BHA_Struct):
    __BHAStructAttrs__ = {"h": float, "s": float, "v": float}
    def to_rgb(self):
        return tuple(max(0, min(255, round(c * 255))) for c in _colorsys.hsv_to_rgb(float(self.h), float(self.s), float(self.v)))
    def to_hex(self):
        return "#{:02X}{:02X}{:02X}".format(*self.to_rgb())


class BHA_HSVA(BHA_Struct):
    __BHAStructAttrs__ = {"h": float, "s": float, "v": float, "a": float}
    def __init__(self, h=0.0, s=0.0, v=0.0, a=1.0):
        if isinstance(h, (dict, BHA_Struct)):
            d = h.as_dict() if isinstance(h, BHA_Struct) else h
            h = d.get("h", 0.0); s = d.get("s", 0.0); v = d.get("v", 0.0); a = d.get("a", 1.0)
        self.h, self.s, self.v, self.a = h, s, v, a
    def to_rgba8(self):
        r, g, b = _colorsys.hsv_to_rgb(float(self.h), float(self.s), float(self.v))
        return (max(0, min(255, round(r * 255))), max(0, min(255, round(g * 255))), max(0, min(255, round(b * 255))), max(0, min(255, round(float(self.a) * 255))))
    def to_hex(self):
        return "#{:02X}{:02X}{:02X}{:02X}".format(*self.to_rgba8())


class BHA_Interval(BHA_Struct):
    __BHAStructAttrs__ = {"lo": float, "hi": float}
    def contains(self, v): return float(self.lo) <= float(v) <= float(self.hi)
    def width(self): return float(self.hi) - float(self.lo)


class BHA_Mat2(BHA_Struct):
    __BHAStructAttrs__ = {"m00": float, "m01": float, "m10": float, "m11": float}
    def __init__(self, m00=None, m01=None, m10=None, m11=None):
        if isinstance(m00, (dict, BHA_Struct)):
            d = m00.as_dict() if isinstance(m00, BHA_Struct) else m00
            m00 = d.get("m00"); m01 = d.get("m01"); m10 = d.get("m10"); m11 = d.get("m11")
        if m00 is None and m01 is None and m10 is None and m11 is None:
            m00, m01, m10, m11 = 1.0, 0.0, 0.0, 1.0
        else:
            m00 = 0.0 if m00 is None else m00
            m01 = 0.0 if m01 is None else m01
            m10 = 0.0 if m10 is None else m10
            m11 = 0.0 if m11 is None else m11
        self.m00, self.m01, self.m10, self.m11 = m00, m01, m10, m11
    def determinant(self): return float(self.m00) * float(self.m11) - float(self.m01) * float(self.m10)
    def trace(self): return float(self.m00) + float(self.m11)
    def transpose(self):
        return BHA_Mat2(float(self.m00), float(self.m10), float(self.m01), float(self.m11))
    def __mul__(self, o):
        if isinstance(o, BHA_Mat2):
            return BHA_Mat2(
                float(self.m00) * float(o.m00) + float(self.m01) * float(o.m10),
                float(self.m00) * float(o.m01) + float(self.m01) * float(o.m11),
                float(self.m10) * float(o.m00) + float(self.m11) * float(o.m10),
                float(self.m10) * float(o.m01) + float(self.m11) * float(o.m11))
        if isinstance(o, BHA_Vec2):
            return BHA_Vec2(float(self.m00) * float(o.x) + float(self.m01) * float(o.y),
                            float(self.m10) * float(o.x) + float(self.m11) * float(o.y))
        if isinstance(o, (int, float)):
            return BHA_Mat2(*(float(getattr(self, f"m{i}{j}")) * o for i in range(2) for j in range(2)))
        return NotImplemented
    def __rmul__(self, o):
        return self * o if isinstance(o, (int, float)) else NotImplemented


class BHA_Mat3(BHA_Struct):
    __BHAStructAttrs__ = {f"m{i}{j}": float for i in range(3) for j in range(3)}
    def __init__(self, m00=None, m01=None, m02=None, m10=None, m11=None, m12=None, m20=None, m21=None, m22=None):
        if isinstance(m00, (dict, BHA_Struct)):
            d = m00.as_dict() if isinstance(m00, BHA_Struct) else m00
            m00 = d.get("m00"); m01 = d.get("m01"); m02 = d.get("m02")
            m10 = d.get("m10"); m11 = d.get("m11"); m12 = d.get("m12")
            m20 = d.get("m20"); m21 = d.get("m21"); m22 = d.get("m22")
        if all(x is None for x in (m00, m01, m02, m10, m11, m12, m20, m21, m22)):
            m00, m01, m02, m10, m11, m12, m20, m21, m22 = 1, 0, 0, 0, 1, 0, 0, 0, 1
        else:
            m00 = 0.0 if m00 is None else m00; m01 = 0.0 if m01 is None else m01; m02 = 0.0 if m02 is None else m02
            m10 = 0.0 if m10 is None else m10; m11 = 0.0 if m11 is None else m11; m12 = 0.0 if m12 is None else m12
            m20 = 0.0 if m20 is None else m20; m21 = 0.0 if m21 is None else m21; m22 = 0.0 if m22 is None else m22
        self.m00, self.m01, self.m02 = m00, m01, m02
        self.m10, self.m11, self.m12 = m10, m11, m12
        self.m20, self.m21, self.m22 = m20, m21, m22
    def determinant(self):
        return (float(self.m00) * (float(self.m11) * float(self.m22) - float(self.m12) * float(self.m21))
                - float(self.m01) * (float(self.m10) * float(self.m22) - float(self.m12) * float(self.m20))
                + float(self.m02) * (float(self.m10) * float(self.m21) - float(self.m11) * float(self.m20)))
    def trace(self): return float(self.m00) + float(self.m11) + float(self.m22)
    def det(self):
        return self.determinant()
    def inv(self):
        d = self.determinant()
        if d == 0:
            raise ValueError("矩阵不可逆（行列式为 0）")
        m00, m01, m02 = float(self.m00), float(self.m01), float(self.m02)
        m10, m11, m12 = float(self.m10), float(self.m11), float(self.m12)
        m20, m21, m22 = float(self.m20), float(self.m21), float(self.m22)
        return BHA_Mat3(
            (m11 * m22 - m12 * m21) / d, (m02 * m21 - m01 * m22) / d, (m01 * m12 - m02 * m11) / d,
            (m12 * m20 - m10 * m22) / d, (m00 * m22 - m02 * m20) / d, (m02 * m10 - m00 * m12) / d,
            (m10 * m21 - m11 * m20) / d, (m01 * m20 - m00 * m21) / d, (m00 * m11 - m01 * m10) / d)
    def transpose(self):
        return BHA_Mat3(float(self.m00), float(self.m10), float(self.m20),
                        float(self.m01), float(self.m11), float(self.m21),
                        float(self.m02), float(self.m12), float(self.m22))
    def __mul__(self, o):
        if isinstance(o, BHA_Mat3):
            return BHA_Mat3(
                float(self.m00) * float(o.m00) + float(self.m01) * float(o.m10) + float(self.m02) * float(o.m20),
                float(self.m00) * float(o.m01) + float(self.m01) * float(o.m11) + float(self.m02) * float(o.m21),
                float(self.m00) * float(o.m02) + float(self.m01) * float(o.m12) + float(self.m02) * float(o.m22),
                float(self.m10) * float(o.m00) + float(self.m11) * float(o.m10) + float(self.m12) * float(o.m20),
                float(self.m10) * float(o.m01) + float(self.m11) * float(o.m11) + float(self.m12) * float(o.m21),
                float(self.m10) * float(o.m02) + float(self.m11) * float(o.m12) + float(self.m12) * float(o.m22),
                float(self.m20) * float(o.m00) + float(self.m21) * float(o.m10) + float(self.m22) * float(o.m20),
                float(self.m20) * float(o.m01) + float(self.m21) * float(o.m11) + float(self.m22) * float(o.m21),
                float(self.m20) * float(o.m02) + float(self.m21) * float(o.m12) + float(self.m22) * float(o.m22))
        if isinstance(o, BHA_Vec3):
            return BHA_Vec3(float(self.m00) * float(o.x) + float(self.m01) * float(o.y) + float(self.m02) * float(o.z),
                            float(self.m10) * float(o.x) + float(self.m11) * float(o.y) + float(self.m12) * float(o.z),
                            float(self.m20) * float(o.x) + float(self.m21) * float(o.y) + float(self.m22) * float(o.z))
        if isinstance(o, (int, float)):
            return BHA_Mat3(*(float(getattr(self, f"m{i}{j}")) * o for i in range(3) for j in range(3)))
        return NotImplemented
    def __rmul__(self, o):
        return self * o if isinstance(o, (int, float)) else NotImplemented


class BHA_Transform(BHA_Struct):
    __BHAStructAttrs__ = {"position": BHA_Vec3, "rotation": BHA_Quaternion}
    def __init__(self, position=None, rotation=None):
        if isinstance(position, dict):
            d = position
            position = d.get("position"); rotation = d.get("rotation")
        if position is None:
            position = BHA_Vec3()
        if rotation is None:
            rotation = BHA_Quaternion()
        if not isinstance(position, BHA_Struct):
            position = BHA_Vec3(*position)
        if not isinstance(rotation, BHA_Struct):
            rotation = BHA_Quaternion(*rotation)
        self.position, self.rotation = position, rotation
    def __repr__(self): return f"Transform(pos={self.position}, rot={self.rotation})"


class BHA_ScreenPos(BHA_Struct):
    __BHAStructAttrs__ = {"x": int, "y": int, "z": int}
    def to_tuple(self): return (int(self.x), int(self.y), int(self.z))


class BHA_Frequency(BHA_Struct):
    __BHAStructAttrs__ = {"hz": float, "unit": str}
    def __init__(self, hz=0.0, unit="hz"):
        if isinstance(hz, (dict, BHA_Struct)):
            d = hz.as_dict() if isinstance(hz, BHA_Struct) else hz
            hz = d.get("hz", 0.0); unit = d.get("unit", "hz")
        self.hz, self.unit = hz, unit
    def to_hz(self):
        u = self.unit.lower()
        if u == "khz": return float(self.hz) * 1000
        if u == "mhz": return float(self.hz) * 1_000_000
        if u == "ghz": return float(self.hz) * 1_000_000_000
        return float(self.hz)


class BHA_Version(BHA_Struct):
    __BHAStructAttrs__ = {"major": int, "minor": int, "patch": int}
    def __init__(self, major=0, minor=0, patch=0):
        if isinstance(major, (dict, BHA_Struct)):
            d = major.as_dict() if isinstance(major, BHA_Struct) else major
            major = d.get("major", 0); minor = d.get("minor", 0); patch = d.get("patch", 0)
        self.major, self.minor, self.patch = major, minor, patch
    def __str__(self): return f"{int(self.major)}.{int(self.minor)}.{int(self.patch)}"
    __repr__ = __str__
import ctypes as _ct


import bisect
import ctypes as _ct
from collections.abc import MutableSet


class StructRSBTSet(MutableSet):
    def _bs(self):
        return len(self).bit_length() << 3

    class _Node(_ct.Structure):
        _fields_ = [
            ("keys", _ct.py_object),
            ("size", _ct.c_uint8),
            ("height", _ct.c_uint16),
            ("left", _ct.c_void_p),
            ("right", _ct.c_void_p),
            ("parent", _ct.c_void_p),
        ]
        def __init__(self):
            self.keys = []
            self.size = 0
            self.height = 1
            self.left = 0
            self.right = 0
            self.parent = 0

    def __init__(self, struct_class, key=None, items=None):
        self._struct_class = struct_class
        self._key = key if key is not None else (lambda x: x)
        self._nil = self._Node()
        self._nil.keys = []
        self._nil.size = 0
        self._nil.height = 0
        na = _ct.addressof(self._nil)
        self._nil.left = na
        self._nil.right = na
        self._nil.parent = na
        self.root = na
        self._min_node = na
        self._max_node = na
        self._nil_addr = na
        self._count = 0
        self._ver = 0
        self._keepalive = [self._nil]
        self._by_addr = {na: self._nil}
        self._nk = {na: []}
        if items:
            for v in items:
                self.add(v)

    def _k(self, x):
        return self._key(x)

    def _n(self, addr):
        return self._by_addr.get(addr)

    def _h(self, addr):
        n = self._n(addr)
        return n.height if n else 0

    def _upd_h(self, addr):
        n = self._n(addr)
        n.height = 1 + max(self._h(n.left), self._h(n.right))

    def _ratio(self, addr):
        n = self._n(addr)
        return (self._h(n.left) + 1) / (self._h(n.right) + 1)

    def _set_left(self, p_addr, c_addr):
        self._n(p_addr).left = c_addr
        if c_addr and c_addr != self._nil_addr:
            self._n(c_addr).parent = p_addr

    def _set_right(self, p_addr, c_addr):
        self._n(p_addr).right = c_addr
        if c_addr and c_addr != self._nil_addr:
            self._n(c_addr).parent = p_addr

    def _replace(self, old_addr, new_addr):
        op = self._n(old_addr).parent
        if op == self._nil_addr:
            self.root = new_addr
            if new_addr and new_addr != self._nil_addr:
                self._n(new_addr).parent = self._nil_addr
        else:
            if self._n(op).left == old_addr:
                self._set_left(op, new_addr)
            else:
                self._set_right(op, new_addr)

    def _rot_right(self, x_addr):
        y_addr = self._n(x_addr).left
        self._set_left(x_addr, self._n(y_addr).right)
        self._replace(x_addr, y_addr)
        self._set_right(y_addr, x_addr)
        self._upd_h(x_addr)
        self._upd_h(y_addr)
        return y_addr

    def _rot_left(self, x_addr):
        y_addr = self._n(x_addr).right
        self._set_right(x_addr, self._n(y_addr).left)
        self._replace(x_addr, y_addr)
        self._set_left(y_addr, x_addr)
        self._upd_h(x_addr)
        self._upd_h(y_addr)
        return y_addr

    def _rebalance(self, addr):
        while addr and addr != self._nil_addr:
            n = self._n(addr)
            old_h = n.height
            self._upd_h(addr)
            r = self._ratio(addr)
            if r > 2:
                if self._ratio(n.left) < 1:
                    self._rot_left(n.left)
                addr = self._rot_right(addr)
            elif r < 0.5:
                if self._ratio(n.right) > 1:
                    self._rot_right(n.right)
                addr = self._rot_left(addr)
            if self._n(addr).height == old_h:
                break
            addr = self._n(addr).parent

    def _leftmost(self, addr):
        while addr and addr != self._nil_addr and self._n(addr).left != self._nil_addr:
            addr = self._n(addr).left
        return addr

    def _rightmost(self, addr):
        while addr and addr != self._nil_addr and self._n(addr).right != self._nil_addr:
            addr = self._n(addr).right
        return addr

    def min(self):
        if self._min_node == self._nil_addr:
            raise KeyError("empty set")
        return self._nk[self._min_node][0]

    def max(self):
        if self._max_node == self._nil_addr:
            raise KeyError("empty set")
        mk = self._nk[self._max_node]
        return mk[len(mk) - 1]

    def pop_min(self):
        v = self.min()
        self.discard(self._k(v))
        return v

    def pop_max(self):
        v = self.max()
        self.discard(self._k(v))
        return v

    def _search(self, addr, key):
        stack = [addr] if addr and addr != self._nil_addr else []
        while stack:
            cur = stack.pop()
            n = self._n(cur)
            if n.size == 0:
                if n.left and n.left != self._nil_addr:
                    stack.append(n.left)
                if n.right and n.right != self._nil_addr:
                    stack.append(n.right)
                continue
            nk = self._nk[cur]
            mk = self._k(nk[0])
            xk = self._k(nk[len(nk) - 1])
            if key < mk:
                if n.left and n.left != self._nil_addr:
                    stack.append(n.left)
            elif key > xk:
                if n.right and n.right != self._nil_addr:
                    stack.append(n.right)
            else:
                return cur
        return 0

    def _mk(self):
        n = self._Node()
        n.size = 0
        n.height = 1
        n.left = self._nil_addr
        n.right = self._nil_addr
        n.parent = self._nil_addr
        a = _ct.addressof(n)
        self._keepalive.append(n)
        self._by_addr[a] = n
        self._nk[a] = []
        return a

    def _insert(self, item):
        key = self._k(item)
        if self.root == self._nil_addr:
            a = self._mk()
            self._nk[a] = [item]
            self._n(a).size = 1
            self.root = a
            self._min_node = a
            self._max_node = a
            self._count = 1
            return

        cur = self.root
        par = 0
        while cur and cur != self._nil_addr:
            n = self._n(cur)
            nk = self._nk[cur]
            mk = self._k(nk[0]) if nk else None
            xk = self._k(nk[len(nk) - 1]) if nk else None
            if mk is not None and key < mk and n.left != self._nil_addr:
                par = cur
                cur = n.left
            elif xk is not None and key > xk and n.right != self._nil_addr:
                par = cur
                cur = n.right
            else:
                break

        if cur and cur != self._nil_addr:
            n = self._n(cur)
            ck = self._nk[cur]
            keys = [self._k(x) for x in ck]
            idx = bisect.bisect_left(keys, key)
            if idx < n.size and keys[idx] == key:
                return
            ck.insert(idx, item)
            n.size = len(ck)
            deepest = cur
            inserted = cur
        else:
            a = self._mk()
            self._nk[a] = [item]
            self._n(a).size = 1
            if key < self._k(self._nk[par][0]):
                self._set_left(par, a)
            else:
                self._set_right(par, a)
            deepest = a
            inserted = a

        self._count += 1
        if self._min_node == self._nil_addr or key < self._k(self._nk[self._min_node][0]):
            self._min_node = inserted
        if self._max_node != self._nil_addr:
            mx = self._nk[self._max_node]
            if key > self._k(mx[len(mx) - 1]):
                self._max_node = inserted
        else:
            self._max_node = inserted
        was_max = inserted == self._max_node

        bs = self._bs()
        d = deepest
        while True:
            dn = self._n(d)
            dk = self._nk[d]
            nkeys = len(dk)
            if nkeys <= bs:
                break
            L = dn.left != self._nil_addr
            R = dn.right != self._nil_addr
            if not L and not R:
                third = nkeys // 3
                left_keys = dk[:third]
                right_keys = dk[third * 2:]
                dk = dk[third:third * 2]
                self._nk[d] = dk
                dn.size = third
                nl = self._mk()
                self._nk[nl] = left_keys
                self._n(nl).size = third
                nr = self._mk()
                self._nk[nr] = right_keys
                self._n(nr).size = nkeys - third * 2
                self._set_left(d, nl)
                self._set_right(d, nr)
                if self._min_node == d:
                    self._min_node = nl
                if self._max_node == d:
                    self._max_node = nr
                d = nr
                break
            elif L and not R:
                half = nkeys // 2
                right_keys = dk[half:]
                dk = dk[:half]
                self._nk[d] = dk
                dn.size = half
                nr = self._mk()
                self._nk[nr] = right_keys
                self._n(nr).size = nkeys - half
                self._set_right(d, nr)
                if self._max_node == d:
                    self._max_node = nr
                d = nr
            elif not L and R:
                half = nkeys // 2
                left_keys = dk[:half]
                dk = dk[half:]
                self._nk[d] = dk
                dn.size = nkeys - half
                nl = self._mk()
                self._nk[nl] = left_keys
                self._n(nl).size = half
                self._set_left(d, nl)
                if self._min_node == d:
                    self._min_node = nl
                break
            else:
                sk_item = dk.pop()
                dn.size = len(dk)
                lm = dn.right
                while self._n(lm).left != self._nil_addr:
                    lm = self._n(lm).left
                lmn = self._n(lm)
                lmk = self._nk[lm]
                lmk.append(sk_item)
                lmk.sort(key=self._k)
                lmn.size = len(lmk)
                d = lm

        if was_max and d != self._max_node:
            self._max_node = d

        rb = self._n(d).parent
        if rb == self._nil_addr:
            rb = d
        self._rebalance(rb)

    def add(self, item):
        key = self._k(item)
        node = self._search(self.root, key)
        if node:
            n = self._n(node)
            ck = self._nk[node]
            keys = [self._k(x) for x in ck]
            idx = bisect.bisect_left(keys, key)
            if idx < n.size and keys[idx] == key:
                return
        self._ver += 1
        self._insert(item)

    def discard(self, key):
        if self.root == self._nil_addr:
            return
        cur = self._search(self.root, key)
        if not cur:
            return
        n = self._n(cur)
        ck = self._nk[cur]
        keys = [self._k(x) for x in ck]
        idx = bisect.bisect_left(keys, key)
        if idx >= n.size or keys[idx] != key:
            return
        was_min = cur == self._min_node
        was_max = cur == self._max_node
        self._ver += 1
        ck.pop(idx)
        n.size = len(ck)
        self._count -= 1

        if n.size == 0:
            p = n.parent
            l = n.left
            r = n.right
            if l != self._nil_addr and r != self._nil_addr:
                succ = r
                while self._n(succ).left != self._nil_addr:
                    succ = self._n(succ).left
                self._nk[cur] = list(self._nk[succ])
                n.size = self._n(succ).size
                sp = self._n(succ).parent
                sr = self._n(succ).right
                if sp == cur:
                    n.right = sr
                else:
                    self._n(sp).left = sr
                if sr and sr != self._nil_addr:
                    self._n(sr).parent = sp
                rb = sp if sp != cur else cur
            else:
                repl = l if l != self._nil_addr else r
                rb = repl
                if p == self._nil_addr:
                    self.root = repl
                    if repl and repl != self._nil_addr:
                        self._n(repl).parent = self._nil_addr
                else:
                    if self._n(p).left == cur:
                        self._set_left(p, repl)
                    else:
                        self._set_right(p, repl)
            if rb and rb != self._nil_addr:
                self._rebalance(rb)
            if was_min:
                self._min_node = self._leftmost(self.root)
            if was_max:
                self._max_node = self._rightmost(self.root)
        else:
            self._rebalance(cur)
            if was_min:
                self._min_node = cur
            if was_max:
                self._max_node = cur

    def __contains__(self, key):
        node = self._search(self.root, key)
        if not node:
            return False
        n = self._n(node)
        ck = self._nk[node]
        keys = [self._k(x) for x in ck]
        i = bisect.bisect_left(keys, key)
        return i < n.size and keys[i] == key

    def __len__(self):
        return self._count

    def __iter__(self):
        ver = self._ver
        stack = []
        cur = self.root
        while stack or (cur and cur != self._nil_addr):
            while cur and cur != self._nil_addr:
                stack.append(cur)
                cur = self._n(cur).left
            cur = stack.pop()
            for item in self._nk[cur]:
                if self._ver != ver:
                    raise RuntimeError("set changed size during iteration")
                yield item
            cur = self._n(cur).right

    def __str__(self):
        return "StructRSBTSet({" + ",".join(map(str, self)) + "})"


class BHA_Dict(MutableMapping):
    """有序映射：底层为 StructRSBTSet + 动态生成的 Pair(BHA_Struct) 键值对。

    用法与内置 dict 完全一致：d[k] / d[k]=v / del d[k] / k in d / len(d) /
    iter(d) / keys / values / items / get / setdefault / pop / update /
    clear / copy。仅构造函数需指定 key/value 类型：

        d = BHA_Dict(int, str)
        d[1] = "one"; d[2] = "two"
    """

    def __init__(self, keytype, valuetype, items=None, **kwargs):
        self.keytype = keytype
        self.valuetype = valuetype
        # 在构造函数里动态生成 Pair 结构体类
        pair_name = "BHA_Pair_%s_%s" % (keytype.__name__, valuetype.__name__)
        self.Pair = type(pair_name, (BHA_Struct,),
                         {"__BHAStructAttrs__": {"k": keytype, "v": valuetype}})
        self._rsbt = StructRSBTSet(self.Pair, key=lambda p: p.k)
        if items:
            if isinstance(items, dict):
                items = items.items()
            for k, v in items:
                self[k] = v
        for k, v in kwargs.items():
            self[k] = v

    # ---- 5 个 MutableMapping 抽象方法 ----
    def _ckey(self, k):
        if not isinstance(k, self.keytype):
            k = self.keytype(k)
        return k

    def __setitem__(self, k, v):
        # 更新已有键：替换值而不改树结构
        k = self._ckey(k)
        node = self._rsbt._search(self._rsbt.root, k)
        if node:
            n = self._rsbt._n(node)
            ck = self._rsbt._nk[node]
            keys = [self._rsbt._k(x) for x in ck]
            i = bisect.bisect_left(keys, k)
            if i < n.size and keys[i] == k:
                ck[i].v = v
                return
        self._rsbt.add(self.Pair(k=k, v=v))

    def __getitem__(self, k):
        k = self._ckey(k)
        node = self._rsbt._search(self._rsbt.root, k)
        if not node:
            raise KeyError(k)
        n = self._rsbt._n(node)
        ck = self._rsbt._nk[node]
        keys = [self._rsbt._k(x) for x in ck]
        i = bisect.bisect_left(keys, k)
        if i >= n.size or keys[i] != k:
            raise KeyError(k)
        return ck[i].v

    def __delitem__(self, k):
        k = self._ckey(k)
        if k not in self._rsbt:
            raise KeyError(k)
        self._rsbt.discard(k)

    def __iter__(self):
        for p in self._rsbt:
            yield p.k

    def __len__(self):
        return len(self._rsbt)

    # ---- 键值访问（覆盖派生实现，保持有序） ----
    def keys(self):
        return (p.k for p in self._rsbt)

    def values(self):
        return (p.v for p in self._rsbt)

    def items(self):
        return ((p.k, p.v) for p in self._rsbt)

    def __contains__(self, k):
        k = self._ckey(k)
        return k in self._rsbt

    def __repr__(self):
        return "BHA_Dict({%s})" % ", ".join("%r: %r" % (k, v) for k, v in self.items())

    def __eq__(self, other):
        if not isinstance(other, MutableMapping):
            return NotImplemented
        return len(self) == len(other) and all(other[k] == v for k, v in self.items())

    def copy(self):
        return BHA_Dict(self.keytype, self.valuetype, items=self.items())

    def __copy__(self):
        return self.copy()

