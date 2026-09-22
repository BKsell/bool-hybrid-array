# cython: language_level=3,boundscheck=False,wraparound=False,cdivision=True,nonecheck=False,overflowcheck=False,initializedcheck=False,infer_types=True,annotation_typing=True,profile=False,linetrace=False,emit_code_comments=False,c_api_binop_methods=True
from __future__ import annotations
from collections.abc import MutableSequence
from weakref import WeakValueDictionary, proxy as _wproxy
from ..core import *
from ..int_array import IntHybridArray
from ..float_array import FloatHybridArray, BHA_Float
import math as _math
import colorsys as _colorsys


def _item_to_row(item, struct_class):
    if isinstance(item, dict):
        return dict(item)
    if isinstance(item, BHA_Struct):
        arr = item.__dict__.get("_arr")
        i = item.__dict__.get("index")
        return {k: arr.attrs[k][i] for k in struct_class.__BHAStructAttrs__}
    raise TypeError(f"cannot treat {type(item).__name__} as {struct_class.__name__}")


class BHAStructMeta(type, metaclass=ResurrectMeta):
    def __mul__(cls, n):
        if not isinstance(n, int):
            return NotImplemented
        return StructHybridArray(cls, n)
    __rmul__ = __mul__

    def __call__(cls, *args, **kwargs):
        tmp = StructHybridArray(cls, 1)
        if len(args) == 1 and not kwargs:
            arg = args[0]
            if isinstance(arg, (dict, cls)):
                tmp[0] = arg
            else:
                raise TypeError(f"{cls.__name__}() takes a dict or instance")
        elif args:
            fields = list(cls.__BHAStructAttrs__)
            if len(args) > len(fields):
                raise TypeError(f"{cls.__name__}() takes at most {len(fields)} positional args, got {len(args)}")
            row = tmp[0]
            for k, v in zip(fields, args):
                setattr(row, k, v)
            for k, v in kwargs.items():
                setattr(row, k, v)
        else:
            row = tmp[0]
            for k, v in kwargs.items():
                setattr(row, k, v)
        proxy = tmp[0]
        object.__setattr__(proxy, "_arr", tmp)
        return proxy


class BHA_Char(int, metaclass=ResurrectMeta):
    __module__ = 'bool_hybrid_array.struct_array'
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
        if name in ("_arr", "index"):
            object.__setattr__(self, name, value)
            return
        arr = self.__dict__.get("_arr")
        i = self.__dict__.get("index")
        if arr is not None and i is not None:
            if name in arr.attrs:
                arr.attrs[name][i] = value
                return
        raise AttributeError(f"{type(self).__name__!r} has no field {name!r}")

    def __repr__(self):
        arr = self.__dict__.get("_arr")
        i = self.__dict__.get("index")
        if arr is None:
            return f"<{type(self).__name__} unbound>"
        fields = ", ".join(f"{k}={arr.attrs[k][i]!r}"
                           for k in arr.struct_class.__BHAStructAttrs__)
        return f"{type(self).__name__}({fields})"

    def __eq__(self, other):
        if isinstance(other, BHA_Struct):
            a = self.__dict__.get("_arr"); i = self.__dict__.get("index")
            b = other.__dict__.get("_arr"); j = other.__dict__.get("index")
            if a is None or b is None:
                return NotImplemented
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
            return [self._col._flat[start + i] for i in idxs]
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
            idxs = list(range(*j.indices(n)))
            vals = list(v)
            if len(idxs) != len(vals):
                raise ValueError("slice assignment length mismatch")
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
            idxs = list(range(*j.indices(n)))
            for i in reversed(idxs):
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
        for i in range(n):
            yield self._col._flat[start + i]
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
            return list(self) == list(other)
        if isinstance(other, (list, tuple)):
            return list(self) == list(other)
        return NotImplemented
    def __repr__(self):
        return f"RowArrayView({list(self)})"


class RowArrayColumn(metaclass=ResurrectMeta):
    def __init__(self, flat_cls, size):
        self._flat = flat_cls([])
        self._lengths = IntHybridArray([0] * size)
        self._offsets = IntHybridArray([0] * (size + 1))
        self._flat_cls = flat_cls
    def __len__(self):
        return len(self._lengths)
    def __getitem__(self, row):
        return RowArrayView(self, row)
    def __setitem__(self, row, values):
        values = list(values)
        old_len = self._lengths[row]
        start = self._offsets[row]
        del self._flat[start:start + old_len]
        for v in values:
            self._flat.insert(start, v)
            start += 1
        self._lengths[row] = len(values)
        off = 0
        for i in range(len(self._lengths)):
            self._offsets[i] = off
            off += self._lengths[i]
        self._offsets[len(self._lengths)] = off
    def insert_row(self, row, values=()):
        values = list(values)
        self._lengths.insert(row, len(values))
        off = self._offsets[row]
        for v in values:
            self._flat.insert(off, v)
            off += 1
        self._offsets.insert(row + 1, self._offsets[row] + len(values))
        for i in range(row + 1, len(self._offsets)):
            self._offsets[i] = self._offsets[i - 1] + self._lengths[i - 1]
    def delete_row(self, row):
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
        self._flat.insert(start + j, v)
        self._lengths[row] = n + 1
        self._recompute_offsets()
    def row_delete(self, row, j):
        start = self._offsets[row]
        n = self._lengths[row]
        if j < 0:
            j += n
        del self._flat[start + j]
        self._lengths[row] = n - 1
        self._recompute_offsets()
    def __delitem__(self, row):
        self.delete_row(row)
    def insert(self, position, values=()):
        self.insert_row(position, values if values is not None else ())
    def clear(self):
        self._flat = self._flat_cls([])
        self._lengths = IntHybridArray([])
        self._offsets = IntHybridArray([0])


class StructHybridArray(MutableSequence, metaclass=ResurrectMeta):
    def __init__(self, struct_class, size: int = 0, items=None):
        if not (isinstance(struct_class, type) and issubclass(struct_class, BHA_Struct)):
            raise TypeError(f"expected BHA_Struct subclass, got {struct_class!r}")
        self.struct_class = struct_class
        self.attrs: dict = {}
        for fn, ft in struct_class.__BHAStructAttrs__.items():
            self.attrs[fn] = self._build_storage(ft, size)
        self._proxies: WeakValueDictionary = WeakValueDictionary()
        if items:
            self.extend(items)

    @staticmethod
    def _build_storage(ft, size):
        if ft is bool or ft is BHA_bool or ft is BHA_Bool:
            return BoolHybridArr([False] * size)
        if ft is int or ft is BHA_Char:
            return IntHybridArray([0] * size, Type=BHA_Char if ft is BHA_Char else int)
        if ft is float or ft is BHA_Float:
            return FloatHybridArray([0.0] * size)
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
        return [None] * size

    def _evict(self, key):
        old = self._proxies.pop(key, None)
        if old is None:
            return
        tmp = StructHybridArray(self.struct_class, 1)
        for k in self.struct_class.__BHAStructAttrs__:
            tmp.attrs[k][0] = self.attrs[k][key]
        object.__setattr__(old, "_arr", tmp)
        object.__setattr__(old, "index", 0)

    def __del__(self):
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
        return len(next(iter(self.attrs.values())))

    def __getitem__(self, key):
        if isinstance(key, slice):
            return [self[i] for i in range(*key.indices(len(self)))]
        key = key if key >= 0 else key + len(self)
        if not (0 <= key < len(self)):
            raise IndexError(f"index {key} out of range")
        p = self._proxies.get(key)
        if p is None:
            p = self.struct_class.__new__(self.struct_class)
            object.__setattr__(p, "_arr", _wproxy(self))
            object.__setattr__(p, "index", key)
            self._proxies[key] = p
        return p

    def __setitem__(self, key, value):
        if isinstance(key, slice):
            start, stop, step = key.indices(len(self))
            idxs = list(range(start, stop, step))
            if isinstance(value, (list, tuple)):
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
        self._evict(key)
        for storage in self.attrs.values():
            del storage[key]
        new_proxies = WeakValueDictionary()
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
        row = _item_to_row(item, self.struct_class)
        for k, storage in self.attrs.items():
            storage.insert(position, row.get(k))
        new_proxies = WeakValueDictionary()
        for i, p in self._proxies.items():
            if i >= position:
                object.__setattr__(p, "index", i + 1)
                new_proxies[i + 1] = p
            else:
                new_proxies[i] = p
        self._proxies = new_proxies

    def append(self, item):
        self.insert(len(self), item)

    def extend(self, iterable):
        for v in iterable:
            self.append(v)

    def pop(self, index=-1):
        n = len(self)
        index = index if index >= 0 else index + n
        if not (0 <= index < n):
            raise IndexError("pop index out of range")
        snapshot = self[index].as_dict()
        del self[index]
        return self.struct_class(snapshot)

    def remove(self, item):
        try:
            idx = self.index(item)
        except ValueError:
            raise ValueError(f"{item!r} not in list")
        del self[idx]

    def clear(self):
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
        return map(self.__getitem__, range(len(self)))

    def __reversed__(self):
        return map(self.__getitem__, range(len(self) - 1, -1, -1))

    def __iadd__(self, other):
        self.extend(other)
        return self

    def __add__(self, other):
        r = StructHybridArray(self.struct_class, 0)
        r.extend(self); r.extend(other)
        return r

    def __imul__(self, n):
        if n <= 0:
            self.clear()
            return self
        orig = list(self)
        for _ in range(n - 1):
            self.extend(orig)
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
    def to_hex(self):
        return "#{:02X}{:02X}{:02X}{:02X}".format(int(self.r), int(self.g), int(self.b), int(self.a))
    def __eq__(self, o):
        if isinstance(o, BHA_RGBA):
            return (int(self.r) == int(o.r) and int(self.g) == int(o.g)
                    and int(self.b) == int(o.b) and int(self.a) == int(o.a))
        return NotImplemented


class BHA_RGB(BHA_Struct):
    __BHAStructAttrs__ = {"r": BHA_Char, "g": BHA_Char, "b": BHA_Char}
    def to_hex(self): return "#{:02X}{:02X}{:02X}".format(int(self.r), int(self.g), int(self.b))


class BHA_Vec2(BHA_Struct):
    __BHAStructAttrs__ = {"x": float, "y": float}
    def dot(self, o): return float(self.x) * float(o.x) + float(self.y) * float(o.y)
    def length(self): return (float(self.x) ** 2 + float(self.y) ** 2) ** 0.5
    def normalized(self):
        n = self.length()
        return (0.0, 0.0) if n == 0 else (float(self.x) / n, float(self.y) / n)
    def __add__(self, o): return (float(self.x) + float(o.x), float(self.y) + float(o.y))
    def __sub__(self, o): return (float(self.x) - float(o.x), float(self.y) - float(o.y))
    def __mul__(self, s): return (float(self.x) * float(s), float(self.y) * float(s))
    def __rmul__(self, s): return self * s
    def __neg__(self): return (-float(self.x), -float(self.y))


class BHA_Vec3(BHA_Struct):
    __BHAStructAttrs__ = {"x": float, "y": float, "z": float}
    def dot(self, o): return float(self.x) * float(o.x) + float(self.y) * float(o.y) + float(self.z) * float(o.z)
    def cross(self, o):
        return (float(self.y) * float(o.z) - float(self.z) * float(o.y),
                float(self.z) * float(o.x) - float(self.x) * float(o.z),
                float(self.x) * float(o.y) - float(self.y) * float(o.x))
    def length(self): return (float(self.x) ** 2 + float(self.y) ** 2 + float(self.z) ** 2) ** 0.5
    def normalized(self):
        n = self.length()
        return (0.0, 0.0, 0.0) if n == 0 else (float(self.x) / n, float(self.y) / n, float(self.z) / n)
    def __add__(self, o): return (float(self.x) + float(o.x), float(self.y) + float(o.y), float(self.z) + float(o.z))
    def __sub__(self, o): return (float(self.x) - float(o.x), float(self.y) - float(o.y), float(self.z) - float(o.z))
    def __mul__(self, s): return (float(self.x) * float(s), float(self.y) * float(s), float(self.z) * float(s))
    def __rmul__(self, s): return self * s
    def __neg__(self): return (-float(self.x), -float(self.y), -float(self.z))


class BHA_Vec4(BHA_Struct):
    __BHAStructAttrs__ = {"x": float, "y": float, "z": float, "w": float}
    def __add__(self, o): return (float(self.x) + float(o.x), float(self.y) + float(o.y), float(self.z) + float(o.z), float(self.w) + float(o.w))
    def __sub__(self, o): return (float(self.x) - float(o.x), float(self.y) - float(o.y), float(self.z) - float(o.z), float(self.w) - float(o.w))
    def __neg__(self): return (-float(self.x), -float(self.y), -float(self.z), -float(self.w))


class BHA_Point(BHA_Struct):
    __BHAStructAttrs__ = {"x": int, "y": int}
    def __add__(self, o): return (int(self.x) + int(o.x), int(self.y) + int(o.y))
    def __sub__(self, o): return (int(self.x) - int(o.x), int(self.y) - int(o.y))


class BHA_Point3D(BHA_Struct):
    __BHAStructAttrs__ = {"x": int, "y": int, "z": int}
    def __add__(self, o): return (int(self.x) + int(o.x), int(self.y) + int(o.y), int(self.z) + int(o.z))
    def __sub__(self, o): return (int(self.x) - int(o.x), int(self.y) - int(o.y), int(self.z) - int(o.z))


class BHA_Quaternion(BHA_Struct):
    __BHAStructAttrs__ = {"x": float, "y": float, "z": float, "w": float}
    def conjugate(self): return (float(self.x), float(self.y), float(self.z), -float(self.w))


class BHA_Range(BHA_Struct):
    __BHAStructAttrs__ = {"start": int, "stop": int, "step": int}
    def contains(self, v): return int(self.start) <= v < int(self.stop)
    def length(self): return int(self.stop) - int(self.start)
    def to_slice(self): return slice(int(self.start), int(self.stop), int(self.step))


class BHA_Time(BHA_Struct):
    __BHAStructAttrs__ = {"hour": int, "minute": int, "second": int}
    def to_seconds(self): return int(self.hour) * 3600 + int(self.minute) * 60 + int(self.second)
    def __lt__(self, o): return (int(self.hour), int(self.minute), int(self.second)) < (int(o.hour), int(o.minute), int(o.second))
    def __le__(self, o): return (int(self.hour), int(self.minute), int(self.second)) <= (int(o.hour), int(o.minute), int(o.second))


class BHA_Date(BHA_Struct):
    __BHAStructAttrs__ = {"year": int, "month": int, "day": int}
    def __lt__(self, o): return (int(self.year), int(self.month), int(self.day)) < (int(o.year), int(o.month), int(o.day))


class BHA_DateTime(BHA_Struct):
    __BHAStructAttrs__ = {"year": int, "month": int, "day": int, "hour": int, "minute": int, "second": int}
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
    def flip_v(self): return (float(self.u), 1.0 - float(self.v))
    def __add__(self, o): return (float(self.u) + float(o.u), float(self.v) + float(o.v))


class BHA_ColorF(BHA_Struct):
    __BHAStructAttrs__ = {"r": float, "g": float, "b": float, "a": float}
    def to_rgba8(self):
        return (round(float(self.r) * 255), round(float(self.g) * 255), round(float(self.b) * 255), round(float(self.a) * 255))
    def to_hex(self):
        r, g, b, a = self.to_rgba8()
        return "#{:02X}{:02X}{:02X}{:02X}".format(r, g, b, a)


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
        return ((float(self.x1) + float(self.x2)) / 2, (float(self.y1) + float(self.y2)) / 2)


class BHA_Polar(BHA_Struct):
    __BHAStructAttrs__ = {"angle": float, "radius": float}
    def to_xy(self):
        return (float(self.radius) * _math.cos(float(self.angle)), float(self.radius) * _math.sin(float(self.angle)))


class BHA_HSV(BHA_Struct):
    __BHAStructAttrs__ = {"h": float, "s": float, "v": float}
    def to_rgb(self):
        return tuple(round(c * 255) for c in _colorsys.hsv_to_rgb(float(self.h), float(self.s), float(self.v)))


class BHA_HSVA(BHA_Struct):
    __BHAStructAttrs__ = {"h": float, "s": float, "v": float, "a": float}
    def to_rgba8(self):
        r, g, b = _colorsys.hsv_to_rgb(float(self.h), float(self.s), float(self.v))
        return (round(r * 255), round(g * 255), round(b * 255), round(float(self.a) * 255))


class BHA_Interval(BHA_Struct):
    __BHAStructAttrs__ = {"lo": float, "hi": float}
    def contains(self, v): return float(self.lo) <= float(v) <= float(self.hi)
    def width(self): return float(self.hi) - float(self.lo)


class BHA_Mat2(BHA_Struct):
    __BHAStructAttrs__ = {"m00": float, "m01": float, "m10": float, "m11": float}
    def determinant(self): return float(self.m00) * float(self.m11) - float(self.m01) * float(self.m10)
    def trace(self): return float(self.m00) + float(self.m11)


class BHA_Mat3(BHA_Struct):
    __BHAStructAttrs__ = {f"m{i}{j}": float for i in range(3) for j in range(3)}
    def trace(self): return float(self.m00) + float(self.m11) + float(self.m22)


class BHA_Transform(BHA_Struct):
    __BHAStructAttrs__ = {"position": BHA_Vec3, "rotation": BHA_Quaternion}
    def __repr__(self): return f"Transform(pos={self.position}, rot={self.rotation})"


class BHA_ScreenPos(BHA_Struct):
    __BHAStructAttrs__ = {"x": int, "y": int, "z": int}
    def to_tuple(self): return (int(self.x), int(self.y), int(self.z))


class BHA_Frequency(BHA_Struct):
    __BHAStructAttrs__ = {"hz": float, "unit": str}
    def to_hz(self):
        u = self.unit.lower()
        if u == "khz": return float(self.hz) * 1000
        if u == "mhz": return float(self.hz) * 1_000_000
        if u == "ghz": return float(self.hz) * 1_000_000_000
        return float(self.hz)


class BHA_Version(BHA_Struct):
    __BHAStructAttrs__ = {"major": int, "minor": int, "patch": int}
    def __str__(self): return f"{int(self.major)}.{int(self.minor)}.{int(self.patch)}"
    __repr__ = __str__
