# cython: language_level=3,boundscheck=False,wraparound=False,cdivision=True,nonecheck=False,overflowcheck=False,initializedcheck=False,infer_types=True,annotation_typing=True,profile=False,linetrace=False,emit_code_comments=False,c_api_binop_methods=True
from __future__ import annotations
from collections.abc import Iterable, MutableSequence, MutableSet
from ..core import *
from ..int_array import IntHybridArray
import operator, math, itertools, ctypes
from ..twg_sort import twg_sort


class BHA_Float(float):
    def __new__(cls, data=0, prec=16):
        self = super().__new__(cls)
        if isinstance(data, tuple):
            a, b, length = data[0], data[1], data[2]
            sign = bool(data[3]) if len(data) > 3 else (a < 0)
            self.a, self.b, self.length, self.sign = abs(a), b, length, sign
            return self
        if isinstance(data, BHA_Float):
            self.a = data.a
            self.b = data.b
            self.length = data.length
            self.sign = data.sign
            return self
        if isinstance(data, int):
            data = str(data)
        elif isinstance(data, float):
            if math.isinf(data) or math.isnan(data):
                raise ValueError(f"BHA_Float 无法表示 {data!r}（inf/nan 超出十进制列式存储范围）")
            # .16f 固定十进制，覆盖所有量级（含指数形式的 repr），且尾 0 会被下方 rstrip 掉
            data = format(data, '.16f')
        sign = data.startswith('-')
        if sign:
            data = data[1:]
        if '.' in data:
            a, b = data.split('.')
        else:
            a, b = data, ''
        b = b.rstrip('0')
        self.length = len(b) if b else 1
        self.a, self.b = int(a) if a else 0, int(b) if b else 0
        self.sign = sign
        return self

    def _align_decimal(self, other):
        max_len = max(self.length, other.length)
        self_num = self.a * (10 ** max_len) + self.b * (10 ** (max_len - self.length))
        other_num = other.a * (10 ** max_len) + other.b * (10 ** (max_len - other.length))
        if self.sign: self_num = -self_num
        if other.sign: other_num = -other_num
        return self_num, other_num, max_len

    def __add__(self, other):
        other = BHA_Float(other)
        max_len = max(self.length, other.length)
        a_abs = self.a * (10 ** max_len) + self.b * (10 ** (max_len - self.length))
        b_abs = other.a * (10 ** max_len) + other.b * (10 ** (max_len - other.length))
        if self.sign == other.sign:
            result = a_abs + b_abs
            sign = self.sign
        elif a_abs >= b_abs:
            result = a_abs - b_abs
            sign = self.sign
        else:
            result = b_abs - a_abs
            sign = other.sign
        string = repr(result)
        integer_part = string[:-max_len] if len(string) > max_len else '0'
        decimal_part = string[-max_len:] if len(string) >= max_len else string.zfill(max_len)
        s = f"{integer_part}.{decimal_part}"
        return BHA_Float(("-" + s) if sign else s)

    def __sub__(self, other):
        other = BHA_Float(other)
        return self + BHA_Float((other.a, other.b, other.length, not other.sign))

    def __mul__(self, other):
        other = BHA_Float(other)
        sign = self.sign ^ other.sign
        self_num = self.a * (10 ** self.length) + self.b
        other_num = other.a * (10 ** other.length) + other.b
        product = self_num * other_num
        string = repr(product)
        total_decimal = self.length + other.length
        string = string.zfill(total_decimal + 1)
        integer_part = string[:-total_decimal]
        decimal_part = string[-total_decimal:]
        s = f"{integer_part}.{decimal_part}"
        return BHA_Float(("-" + s) if sign else s)

    def __format__(self, length):
        if length == '': return str(self)
        if length == '!r': return repr(self)
        length = int(length[1:].split('f')[0].split('d')[0])
        if length > self.length: return str(self).ljust(length, '0')
        else: return str(round(self, length))

    def __truediv__(self, other, total_decimal=32):
        other = BHA_Float(other)
        sign = self.sign ^ other.sign
        self_num = self.a * (10 ** self.length) + self.b
        other_num = other.a * (10 ** other.length) + other.b
        if other_num == 0:
            raise ZeroDivisionError("Cannot divide by zero")
        div_num = (self_num * (10 ** total_decimal)) // other_num
        string = repr(div_num)
        if len(string) <= total_decimal:
            string = '0' * (total_decimal - len(string) + 1) + string
        integer_part = string[:-total_decimal]
        decimal_part = string[-total_decimal:]
        s = f"{integer_part}.{decimal_part}"
        return BHA_Float(("-" + s) if sign else s)

    def __repr__(self):
        s2 = f"{self.a}.{str(self.b).zfill(self.length)}"
        return f"BHA_Float({'-' if self.sign else ''}{s2})"

    def __str__(self):
        s2 = f"{self.a}.{str(self.b).zfill(self.length)}"
        return f"{'-' if self.sign else ''}{s2}"

    __radd__ = __add__
    __rmul__ = __mul__
    __rsub__ = lambda self, other: BHA_Float(other) - self
    __rtruediv__ = lambda self, other: BHA_Float(other) / self

    def __float__(self):
        return float(str(self))

    def __int__(self):
        return -self.a if self.sign else self.a

    is_integer = lambda self: not self.b
    __bool__ = lambda self: self.a or self.b

    def as_integer_ratio(self):
        denominator = 10 ** self.length
        numerator = self.a * denominator + self.b
        gcd_val = math.gcd(numerator, denominator)
        if gcd_val == 0:
            gcd_val = 1
        simplified_num = (-numerator if self.sign else numerator) // gcd_val
        simplified_den = denominator // gcd_val
        return (simplified_num, simplified_den)

    __hash__ = float.__hash__

    def __eq__(self, other):
        try:
            other = BHA_Float(other)
            self_num, other_num, _ = self._align_decimal(other)
            return self_num == other_num
        except (ValueError, AttributeError):
            return False

    def __ne__(self, other):
        try:
            other = BHA_Float(other)
            self_num, other_num, _ = self._align_decimal(other)
            return self_num != other_num
        except (ValueError, AttributeError):
            return True

    def __floordiv__(self, other):
        return BHA_Float(int(self / other))

    def __mod__(self, other):
        return self - (self // other) * other

    def __pow__(self, power, m=None):
        self_num = self.a * (10 ** self.length) + self.b
        self_den = 10 ** self.length
        power = BHA_Float(power)
        if m is not None:
            v = pow(self_num, power.a, m)
            return BHA_Float((abs(v), 0, 1, v < 0))
        if power.b == 0:
            p = -power.a if power.sign else power.a
            if p == 0:
                return BHA_Float("1")
            neg = p < 0
            ep = -p if neg else p
            rn = self_num ** ep
            rd = self_den ** ep
            if neg:
                rn, rd = rd, rn
            result_sign = self.sign and (ep & 1)
            total_dec = self.length * ep
            scaled = (rn * (10 ** total_dec)) // rd
            s = repr(scaled).zfill(total_dec + 1)
            out = f"{s[:-total_dec]}.{s[-total_dec:]}"
            return BHA_Float(("-" + out) if result_sign else out)
        else:
            if self.sign:
                raise ValueError("负数的分数次幂无实数定义")
            p = power.a * (10 ** power.length) + power.b
            q = 10 ** power.length
            numer = self_num ** p
            denom = self_den ** p
            R = self.length + power.length
            scaled = (numer * (10 ** (R * q))) // denom
            lo, hi = 0, scaled
            while lo < hi:
                mid = (lo + hi + 1) // 2
                if mid ** q <= scaled:
                    lo = mid
                else:
                    hi = mid - 1
            root = lo
            s = repr(root).zfill(R + 1)
            return BHA_Float(f"{s[:-R]}.{s[-R:]}")

    def __neg__(self):
        return BHA_Float((self.a, self.b, self.length, not self.sign))

    def __pos__(self):
        return self

    def __abs__(self):
        return BHA_Float((self.a, self.b, self.length, False))

    def __lt__(self, other):
        other = BHA_Float(other)
        a, b, _ = self._align_decimal(other)
        return a < b

    def __le__(self, other):
        other = BHA_Float(other)
        a, b, _ = self._align_decimal(other)
        return a <= b

    def __gt__(self, other):
        other = BHA_Float(other)
        a, b, _ = self._align_decimal(other)
        return a > b

    def __ge__(self, other):
        other = BHA_Float(other)
        a, b, _ = self._align_decimal(other)
        return a >= b

    def __round__(self, n=None):
        tmp = BHA_Float(self)
        if n is None or n == 0:
            tmp.b = 0
            tmp.length = 1
            half = 5 * 10 ** (self.length - 1)
            if not self.sign:
                if self.b >= half:
                    tmp.a = self.a + 1
            else:
                if self.b >= half:
                    tmp.a = self.a - 1
            return tmp
        tmp.b = (self.b + 5 * 10 ** (self.length - n - 1)) // 10 ** (self.length - n)
        tmp.length = n
        if tmp.b >= 10 ** n:
            tmp.a += 1
            tmp.b -= 10 ** n
        return tmp

    __rmod__ = lambda self, other: BHA_Float(other) % self
    __rfloordiv__ = lambda self, other: BHA_Float(other) // self
    __rpow__ = lambda self, other, m=None: pow(BHA_Float(other), self, m)


class FloatHybridArray(MutableSequence):
    def __reversed__(self):
        if not self:
            return BHA_Iterator([])
        return BHA_Iterator(map(self.__getitem__, range(len(self) - 1, -1, -1)))
    reversed = __reversed__

    def __deepcopy__(self, memo):
        return type(self)(iter(self), Type=self.Type)

    def __copy__(self):
        return type(self)(iter(self), Type=self.Type)

    def copy(self):
        result = type(self)([], Type=self.Type, hash_=False)
        result.lengths = self.lengths.copy()
        result.a = self.a.copy()
        result.b = self.b.copy()
        result.signs = self.signs.copy()
        return result

    def __init__(self, data=(), Type=BHA_Float, *, hash_=True):
        self.Type = Type
        it0 = iter(data)
        if isinstance(it0, BHA_Iterator):
            it0 = it0.data
        t_len, t_a, t_b, t_sign = itertools.tee(map(BHA_Float, it0), 4)
        self.lengths = IntHybridArray(map(operator.attrgetter('length'), t_len), hash_=hash_)
        self.a = IntHybridArray(map(operator.attrgetter('a'), t_a), hash_=hash_)
        self.b = IntHybridArray(map(operator.attrgetter('b'), t_b), hash_=hash_)
        self.signs = BoolHybridArr(map(operator.attrgetter('sign'), t_sign), hash_=hash_)

    @staticmethod
    def _split(value):
        v = BHA_Float(value)
        return v.length, v.a, v.b, v.sign

    def __getitem__(self, index):
        if isinstance(index, slice):
            lengths = self.lengths[index]
            a_part = self.a[index]
            b_part = self.b[index]
            signs_part = self.signs[index]
            result = FloatHybridArray([], Type=self.Type, hash_=False)
            result.lengths = lengths
            result.a = a_part
            result.b = b_part
            result.signs = signs_part
            return result
        return self.Type(BHA_Float((self.a[index], self.b[index], self.lengths[index], self.signs[index])))

    def __setitem__(self, index, value):
        if isinstance(index, slice):
            start, stop, step = index.indices(len(self))
            indices = range(start, stop, step)
            if step == 1:
                if isinstance(value, FloatHybridArray) and len(value) == stop - start:
                    self.lengths[index] = value.lengths
                    self.a[index] = value.a
                    self.b[index] = value.b
                    self.signs[index] = value.signs
                    return
                if isinstance(value, (list, tuple)) and len(value) == stop - start:
                    for off, v in enumerate(value):
                        self[start + off] = v
                    return
                if isinstance(value, (list, tuple, FloatHybridArray)) or hasattr(value, '__iter__'):
                    del self[start:stop]
                    for off, v in enumerate(value):
                        self.insert(start + off, v)
                    return
                for i in range(start, stop):
                    self[i] = value
                return
            if isinstance(value, (list, tuple)):
                if len(value) != len(indices):
                    raise ValueError(f"值数量 {len(value)} 与切片长度 {len(indices)} 不匹配")
                for i, v in zip(indices, value):
                    self[i] = v
            else:
                for i in indices:
                    self[i] = value
            return
        length, a, b, sign = self._split(value)
        self.lengths[index] = length
        self.a[index] = a
        self.b[index] = b
        self.signs[index] = sign

    def __delitem__(self, index):
        if isinstance(index, slice):
            start, stop, step = index.indices(len(self))
            if step > 0:
                for i in reversed(range(start, stop, step)):
                    del self[i]
            else:
                for i in range(start, stop, step):
                    del self[i]
            return
        del self.lengths[index]
        del self.a[index]
        del self.b[index]
        del self.signs[index]

    def __len__(self):
        return len(self.a)

    def insert(self, index, value):
        length, a, b, sign = self._split(value)
        index = max(0, min(index, len(self))) if index >= 0 else max(0, min(index + len(self), len(self)))
        self.lengths.insert(index, length)
        self.a.insert(index, a)
        self.b.insert(index, b)
        self.signs.insert(index, sign)

    def __eq__(self, other) -> bool:
        if not isinstance(other, Iterable):
            return NotImplemented
        if hasattr(other, "__len__"):
            if len(self) != len(other):
                return False
        else:
            n = 0
            for _ in other:
                n += 1
            if len(self) != n:
                return False
        return all(map(operator.eq, self, other))

    def __ne__(self, other) -> bool:
        return not self == other

    def swap(self, idx1, idx2):
        """交换两个浮点元素（内部 4 个并行底层数组各自位级交换）。"""
        n = len(self)
        if idx1 < 0:
            idx1 += n
        if idx2 < 0:
            idx2 += n
        if not (0 <= idx1 < n and 0 <= idx2 < n):
            raise IndexError("swap index out of range")
        if idx1 == idx2:
            return
        self.lengths.swap(idx1, idx2)
        self.a.swap(idx1, idx2)
        self.b.swap(idx1, idx2)
        self.signs.swap(idx1, idx2)

    def move(self, idx1, length, idx2):
        """memmove 式移动 length 个浮点元素到 [idx2, idx2+length)，长度不变。"""
        self.lengths.move(idx1, length, idx2)
        self.a.move(idx1, length, idx2)
        self.b.move(idx1, length, idx2)
        self.signs.move(idx1, length, idx2)

    def __hash__(self):
        return hash(self.a) + hash(self.b) + hash(self.lengths) + hash(self.signs)

    def append(self, value):
        length, a, b, sign = self._split(value)
        self.lengths.append(length)
        self.a.append(a)
        self.b.append(b)
        self.signs.append(sign)

    def extend(self, iterable):
        for v in iterable:
            self.append(v)

    def pop(self, index=-1):
        length = len(self)
        index = index if index >= 0 else index + length
        if not (0 <= index < length):
            raise IndexError("pop 索引超出范围")
        val = self[index]
        del self[index]
        return val

    def remove(self, value):
        try:
            idx = self.index(value)
        except ValueError:
            raise ValueError(f"{value} 不在 FloatHybridArray 中")
        del self[idx]

    def clear(self):
        self.lengths.clear()
        self.a.clear()
        self.b.clear()
        self.signs.clear()

    def reverse(self):
        n = len(self)
        for i in range(n >> 1):
            j = n - 1 - i
            self[i], self[j] = self[j], self[i]

    def index(self, value, start=0, stop=None):
        v = BHA_Float(value)
        n = len(self)
        if stop is None:
            stop = n
        start = max(0, start if start >= 0 else start + n)
        stop = min(n, stop if stop >= 0 else stop + n)
        for i in range(start, stop):
            if self[i] == v:
                return i
        raise ValueError(f"{value} 不在 FloatHybridArray 中")

    def count(self, value):
        v = BHA_Float(value)
        return sum(1 for i in range(len(self)) if self[i] == v)

    def __contains__(self, value):
        v = BHA_Float(value)
        for i in range(len(self)):
            if self[i] == v:
                return True
        return False

    def __iadd__(self, other):
        self.extend(other)
        return self

    def __add__(self, other):
        result = FloatHybridArray(iter(self), Type=self.Type, hash_=False)
        result.extend(other)
        return result

    def __imul__(self, n):
        n = operator.index(n)
        if n <= 0:
            self.clear()
            return self
        self.lengths *= n
        self.a *= n
        self.b *= n
        self.signs *= n
        return self

    def __mul__(self, n):
        result = FloatHybridArray(iter(self), Type=self.Type, hash_=False)
        result *= n
        return result

    def __iter__(self):
        return map(self.__getitem__, range(len(self)))

    def __str__(self):
        return f"FloatHybridArray([{', '.join(map(str, self))}])"
    __repr__ = __str__

    sort = IntHybridArray.sort
import ctypes as _ct


import bisect
import ctypes as _ct
from collections.abc import MutableSet


class FloatRightSplitBlockAVLSet(MutableSet):
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

    def __init__(self, iterable=None):
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
        self._keepalive = [self._nil]
        self._by_addr = {na: self._nil}
        self._nk = {na: []}
        if iterable is not None:
            for val in iterable:
                self.add(val)

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
        self.discard(v)
        return v

    def pop_max(self):
        v = self.max()
        self.discard(v)
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
            ks = self._nk[cur]
            if key < ks[0]:
                if n.left and n.left != self._nil_addr:
                    stack.append(n.left)
            elif key > ks[len(ks) - 1]:
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

    def _insert(self, key):
        key = BHA_Float(key)
        if self.root == self._nil_addr:
            a = self._mk()
            self._nk[a] = [key]
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
            mk = nk[0] if nk else None
            xk = nk[len(nk) - 1] if nk else None
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
            idx = bisect.bisect_left(ck, key)
            if idx < n.size and ck[idx] == key:
                return
            bisect.insort(ck, key)
            n.size = len(ck)
            deepest = cur
            inserted = cur
        else:
            a = self._mk()
            self._nk[a] = [key]
            self._n(a).size = 1
            if key < self._nk[par][0]:
                self._set_left(par, a)
            else:
                self._set_right(par, a)
            deepest = a
            inserted = a

        self._count += 1
        if self._min_node == self._nil_addr or key < self._nk[self._min_node][0]:
            self._min_node = inserted
        if self._max_node != self._nil_addr:
            mx = self._nk[self._max_node]
            if key > mx[len(mx) - 1]:
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
                sk = dk.pop()
                dn.size = len(dk)
                lm = dn.right
                while self._n(lm).left != self._nil_addr:
                    lm = self._n(lm).left
                lmn = self._n(lm)
                lmk = self._nk[lm]
                bisect.insort(lmk, sk)
                lmn.size = len(lmk)
                d = lm

        if was_max and d != self._max_node:
            self._max_node = d

        rb = self._n(d).parent
        if rb == self._nil_addr:
            rb = d
        self._rebalance(rb)

    def add(self, key):
        key = BHA_Float(key)
        node = self._search(self.root, key)
        if node:
            n = self._n(node)
            ck = self._nk[node]
            idx = bisect.bisect_left(ck, key)
            if idx < n.size and ck[idx] == key:
                return
        self._insert(key)

    def discard(self, key):
        key = BHA_Float(key)
        if self.root == self._nil_addr:
            return
        cur = self._search(self.root, key)
        if not cur:
            return
        n = self._n(cur)
        ck = self._nk[cur]
        idx = bisect.bisect_left(ck, key)
        if idx >= len(ck) or ck[idx] != key:
            return
        was_min = cur == self._min_node
        was_max = cur == self._max_node
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
        key = BHA_Float(key)
        node = self._search(self.root, key)
        if not node:
            return False
        n = self._n(node)
        ck = self._nk[node]
        i = bisect.bisect_left(ck, key)
        return i < n.size and ck[i] == key

    def __len__(self):
        return self._count

    def __iter__(self):
        stack = []
        cur = self.root
        while stack or (cur and cur != self._nil_addr):
            while cur and cur != self._nil_addr:
                stack.append(cur)
                cur = self._n(cur).left
            cur = stack.pop()
            yield from self._nk[cur]
            cur = self._n(cur).right

    def __str__(self):
        return "FloatRightSplitBlockAVLSet({" + ",".join(map(str, self)) + "})"


FloatRSBTSet = FloatRightSplitBlockAVLSet
