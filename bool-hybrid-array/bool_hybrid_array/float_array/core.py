# cython: language_level=3,boundscheck=False,wraparound=False,cdivision=True,nonecheck=False,overflowcheck=False,initializedcheck=False,infer_types=True,annotation_typing=True,profile=False,linetrace=False,emit_code_comments=False,c_api_binop_methods=True
from __future__ import annotations
from collections.abc import Iterable, MutableSequence, MutableSet
from ..core import *
from ..int_array import IntHybridArray
import operator, math, itertools, ctypes
from ..twg_sort import twg_sort


class BHA_Float(float):
    def __new__(cls, data: int | str | float | BHA_Float | tuple):
        if isinstance(data, tuple):
            a, b, length = data
            if length > 0:
                val = float(f"{a}.{str(b).zfill(length)}")
            else:
                val = float(a)
            self = super().__new__(cls, val)
            self.a, self.b, self.length = a, b, length
            return self
        self = super().__new__(cls)
        if isinstance(data, BHA_Float):
            self = super().__new__(cls, float(data))
            self.a = data.a
            self.b = data.b
            self.length = data.length
            return self
        if isinstance(data, int):
            data = str(data)
        elif isinstance(data, float):
            data = f"{data:.16f}".rstrip('0').rstrip('.')
        if '.' in data:
            a, b = data.split('.')
        else:
            a, b = data, ''
        b = b.rstrip('0')
        self.length = len(b) if b else 1
        self.a, self.b = int(a) if a else 0, int(b) if b else 0
        return self

    def _align_decimal(self, other):
        max_len = max(self.length, other.length)
        self_num = self.a * (10 ** max_len) + self.b * (10 ** (max_len - self.length))
        other_num = other.a * (10 ** max_len) + other.b * (10 ** (max_len - other.length))
        return self_num, other_num, max_len

    def __add__(self, other):
        other = BHA_Float(other)
        self_num, other_num, max_len = self._align_decimal(other)
        sum_num = self_num + other_num
        string = repr(sum_num)
        integer_part = string[:-max_len] if len(string) > max_len else '0'
        decimal_part = string[-max_len:] if len(string) >= max_len else string.zfill(max_len)
        return BHA_Float(f"{integer_part}.{decimal_part}")

    def __sub__(self, other):
        other = BHA_Float(other)
        self_num, other_num, max_len = self._align_decimal(other)
        sub_num = self_num - other_num
        if sub_num < 0:
            string = repr(-sub_num)
            sign = '-'
        else:
            string = repr(sub_num)
            sign = ''
        integer_part = string[:-max_len] if len(string) > max_len else '0'
        decimal_part = string[-max_len:] if len(string) >= max_len else string.zfill(max_len)
        return BHA_Float(f"{sign}{integer_part}.{decimal_part}")

    def __mul__(self, other):
        other = BHA_Float(other)
        self_num = self.a * (10 ** self.length) + self.b
        other_num = other.a * (10 ** other.length) + other.b
        product = self_num * other_num
        string = repr(product)
        total_decimal = self.length + other.length
        string = string.zfill(total_decimal + 1)
        integer_part = string[:-total_decimal]
        decimal_part = string[-total_decimal:]
        return BHA_Float(f"{integer_part}.{decimal_part}")

    def __format__(self, length):
        if length == '': return str(self)
        if length == '!r': return repr(self)
        length = int(length[1:].split('f')[0].split('d')[0])
        if length > self.length: return str(self).ljust(length, '0')
        else: return str(round(self, length))

    def __truediv__(self, other, total_decimal=22):
        other = BHA_Float(other)
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
        return BHA_Float(f"{integer_part}.{decimal_part}")

    def __repr__(self):
        return f"BHA_Float({self.a}.{str(self.b).zfill(self.length)})"

    def __str__(self):
        return f"{self.a}.{str(self.b).zfill(self.length)}"

    __radd__ = __add__
    __rmul__ = __mul__
    __rsub__ = lambda self, other: BHA_Float(other) - self
    __rtruediv__ = lambda self, other: BHA_Float(other) / self

    def __float__(self):
        return float(str(self))

    def __int__(self):
        return self.a

    is_integer = lambda self: not self.b
    __bool__ = lambda self: self.a or self.b

    def as_integer_ratio(self) -> tuple[int, int]:
        denominator = 10 ** self.length
        numerator = self.a * denominator + self.b
        if numerator < 0:
            numerator = -numerator
            sign = -1
        else:
            sign = 1
        gcd_val = math.gcd(numerator, denominator)
        if gcd_val == 0:
            gcd_val = 1
        simplified_num = sign * (numerator // gcd_val)
        simplified_den = denominator // gcd_val
        return (simplified_num, simplified_den)

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

    @staticmethod
    def _nth_root(n, k):
        if n == 0:
            return 0
        if k == 1:
            return n
        x = 10 ** ((n.bit_length() + k - 1) // k)
        for _ in range(100):
            y = ((k - 1) * x + n // x ** (k - 1)) // k
            if y >= x:
                break
            x = y
        return x

    def __pow__(self, power, m=None):
        self_num = self.a * (10 ** self.length) + self.b
        self_den = 10 ** self.length
        power = BHA_Float(power)
        if m is not None:
            return BHA_Float(pow(self_num, power.a, m))
        if power.b == 0:
            p = power.a
            if p == 0:
                return BHA_Float("1")
            neg = p < 0
            ep = -p if neg else p
            rn = self_num ** ep
            rd = self_den ** ep
            if neg:
                rn, rd = rd, rn
            total_dec = self.length * ep
            scaled = (rn * (10 ** total_dec)) // rd
            s = repr(scaled).zfill(total_dec + 1)
            return BHA_Float(f"{s[:-total_dec]}.{s[-total_dec:]}")
        else:
            p = power.a * (10 ** power.length) + power.b
            q = 10 ** power.length
            prec = 22
            scale = 10 ** (self.length + prec)
            scaled = (self_num * scale) // self_den
            result = self._nth_root(scaled ** p, q)
            s = repr(result).zfill(prec + 1)
            return BHA_Float(f"{s[:-prec]}.{s[-prec:]}")

    def __neg__(self):
        return BHA_Float((-self.a, self.b, self.length))

    def __pos__(self):
        return self

    def __abs__(self):
        return BHA_Float((abs(self.a), self.b, self.length))

    def __lt__(self, other):
        other = BHA_Float(other)
        a, b, _ = self._align_decimal(other)
        return a < b

    def __gt__(self, other):
        other = BHA_Float(other)
        a, b, _ = self._align_decimal(other)
        return a > b

    def __le__(self, other):
        other = BHA_Float(other)
        a, b, _ = self._align_decimal(other)
        return a <= b

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
            if self.a >= 0:
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
    __reversed__ = BoolHybridArray.__reversed__

    def __init__(self, data, Type=BHA_Float):
        self.Type = Type
        data = list(BHA_Iterator(map(BHA_Float, data)))
        self.lengths = IntHybridArray([d.length for d in data])
        self.a = IntHybridArray([d.a for d in data])
        self.b = IntHybridArray([d.b for d in data])

    @staticmethod
    def _split(value):
        v = BHA_Float(value)
        return v.length, v.a, v.b

    def __getitem__(self, index):
        if isinstance(index, slice):
            lengths = self.lengths[index]
            a_part = self.a[index]
            b_part = self.b[index]
            result = FloatHybridArray([], Type=self.Type)
            result.lengths = lengths
            result.a = a_part
            result.b = b_part
            return result
        return self.Type(BHA_Float((self.a[index], self.b[index], self.lengths[index])))

    def __setitem__(self, index, value):
        if isinstance(index, slice):
            start, stop, step = index.indices(len(self))
            if step == 1:
                slice_len = stop - start
                if isinstance(value, FloatHybridArray):
                    vlen = len(value)
                elif isinstance(value, (list, tuple)):
                    vlen = len(value)
                else:
                    vlen = -1
                if vlen == slice_len:
                    for off in range(vlen):
                        self.lengths[start + off] = value.lengths[off]
                        self.a[start + off] = value.a[off]
                        self.b[start + off] = value.b[off]
                    return
                del self[start:stop]
                for off, v in enumerate(value):
                    self.insert(start + off, v)
                return
            indices = list(range(start, stop, step))
            if isinstance(value, (list, tuple)):
                if len(value) != len(indices):
                    raise ValueError(f'值数量 {len(value)} 与切片长度 {len(indices)} 不匹配')
                for i, v in zip(indices, value):
                    self[i] = v
            else:
                for i in indices:
                    self[i] = value
            return
        length, a, b = self._split(value)
        self.lengths[index] = length
        self.a[index] = a
        self.b[index] = b

    def __delitem__(self, index):
        if isinstance(index, slice):
            start, stop, step = index.indices(len(self))
            indices = list(range(start, stop, step))
            for i in reversed(indices):
                del self[i]
            return
        del self.lengths[index]
        del self.a[index]
        del self.b[index]

    def __len__(self):
        return len(self.a)

    def insert(self, index, value):
        length, a, b = self._split(value)
        index = max(0, min(index, len(self))) if index >= 0 else max(0, min(index + len(self), len(self)))
        self.lengths.insert(index, length)
        self.a.insert(index, a)
        self.b.insert(index, b)

    def append(self, value):
        self.insert(len(self), value)

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

    def __eq__(self, other) -> bool:
        if not isinstance(other, Iterable):
            return NotImplemented
        if len(self) != len(other) if hasattr(other, "__len__") else len(self) != len(BHA_Iterator(other)):
            return False
        return all(map(operator.eq, self, other))

    def __ne__(self, other) -> bool:
        return not self == other

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
        result = FloatHybridArray(list(self), Type=self.Type)
        result.extend(other)
        return result

    def __imul__(self, n):
        if n <= 0:
            self.clear()
            return self
        original = list(self)
        for _ in range(n - 1):
            self.extend(original)
        return self

    def __mul__(self, n):
        result = FloatHybridArray(list(self), Type=self.Type)
        result *= n
        return result
    __rmul__ = __mul__

    def __iter__(self):
        return map(self.__getitem__, range(len(self)))

    def __str__(self):
        return f"FloatHybridArray([{', '.join(map(str, self))}])"
    __repr__ = __str__

    sort = twg_sort


_float_node_create_count = 0


class FloatRightSplitBlockAVLSet(MutableSet):
    BLOCK_SIZE = 16

    class BlockNode(ctypes.Structure):
        def __init__(self):
            global _float_node_create_count
            _float_node_create_count += 1
            self.keys = FloatHybridArray([])
            self.size = 0
            self.height = 1
            if "FloatRightSplitBlockAVLSet" in globals():
                _nilp = ctypes.pointer(FloatRightSplitBlockAVLSet.NIL)
                self.left = _nilp
                self.right = _nilp
                self.parent = _nilp

    BlockNode._fields_ = [
        ("keys", ctypes.py_object),
        ("size", ctypes.c_uint8),
        ("left", ctypes.POINTER(BlockNode)),
        ("right", ctypes.POINTER(BlockNode)),
        ("parent", ctypes.POINTER(BlockNode)),
        ("height", ctypes.c_uint16),
    ]

    NIL = BlockNode()
    NIL.height = 0
    NIL.size = 0
    _nil_self = ctypes.pointer(NIL)
    NIL.left = _nil_self
    NIL.right = _nil_self
    NIL.parent = _nil_self
    _NIL_ADDR = ctypes.addressof(NIL)

    def __init__(self, iterable=None):
        self.root = self.NIL
        self._min_node = self.NIL
        self._max_node = self.NIL
        if iterable is not None:
            for val in iterable:
                self.add(val)

    def _left(self, node):
        child = node.left.contents
        if ctypes.addressof(child) == self._NIL_ADDR:
            return self.NIL
        return child

    def _right(self, node):
        child = node.right.contents
        if ctypes.addressof(child) == self._NIL_ADDR:
            return self.NIL
        return child

    def _parent(self, node):
        parent = node.parent.contents
        if ctypes.addressof(parent) == self._NIL_ADDR:
            return self.NIL
        return parent

    def _addr(self, node):
        return self._NIL_ADDR if node is self.NIL else ctypes.addressof(node)

    def _set_left(self, parent, child):
        parent.left = ctypes.pointer(child)
        if child is not self.NIL:
            child.parent = ctypes.pointer(parent)

    def _set_right(self, parent, child):
        parent.right = ctypes.pointer(child)
        if child is not self.NIL:
            child.parent = ctypes.pointer(parent)

    def _replace_in_parent(self, old, new):
        p = self._parent(old)
        if p is self.NIL:
            self.root = new
            if new is not self.NIL:
                new.parent = ctypes.pointer(self.NIL)
        else:
            if self._addr(self._left(p)) == self._addr(old):
                self._set_left(p, new)
            else:
                self._set_right(p, new)

    def _height(self, node):
        return node.height if node is not self.NIL else 0

    def _update_height(self, node):
        node.height = 1 + max(self._height(self._left(node)),
                              self._height(self._right(node)))

    def _balance_ratio(self, node):
        lh = self._height(self._left(node))
        rh = self._height(self._right(node))
        return (lh + 1) / (rh + 1)

    def _rotate_right(self, x):
        y = self._left(x)
        self._set_left(x, self._right(y))
        self._replace_in_parent(x, y)
        self._set_right(y, x)
        self._update_height(x)
        self._update_height(y)
        return y

    def _rotate_left(self, x):
        y = self._right(x)
        self._set_right(x, self._left(y))
        self._replace_in_parent(x, y)
        self._set_left(y, x)
        self._update_height(x)
        self._update_height(y)
        return y

    def _rebalance(self, node):
        while node is not self.NIL:
            old_h = node.height
            self._update_height(node)
            ratio = self._balance_ratio(node)
            if ratio > 2:
                left = self._left(node)
                if self._balance_ratio(left) < 1:
                    self._rotate_left(left)
                node = self._rotate_right(node)
            elif ratio < 0.5:
                right = self._right(node)
                if self._balance_ratio(right) > 1:
                    self._rotate_right(right)
                node = self._rotate_left(node)
            if node.height == old_h:
                break
            node = self._parent(node)

    def _find_leftmost(self, node):
        while self._left(node) is not self.NIL:
            node = self._left(node)
        while node is not self.NIL and node.size == 0:
            if self._right(node) is not self.NIL:
                node = self._right(node)
                while self._left(node) is not self.NIL:
                    node = self._left(node)
            else:
                parent = self._parent(node)
                while parent is not self.NIL and self._addr(node) == self._addr(self._right(parent)):
                    node = parent
                    parent = self._parent(parent)
                node = parent
        return node

    def _find_rightmost(self, node):
        while self._right(node) is not self.NIL:
            node = self._right(node)
        while node is not self.NIL and node.size == 0:
            if self._left(node) is not self.NIL:
                node = self._left(node)
                while self._right(node) is not self.NIL:
                    node = self._right(node)
            else:
                parent = self._parent(node)
                while parent is not self.NIL and self._addr(node) == self._addr(self._left(parent)):
                    node = parent
                    parent = self._parent(parent)
                node = parent
        return node

    def min(self):
        if self._min_node is self.NIL:
            raise KeyError("empty set")
        return self._min_node.keys[0]

    def max(self):
        if self._max_node is self.NIL:
            raise KeyError("empty set")
        return self._max_node.keys[-1]

    def pop_min(self):
        val = self.min()
        self.discard(val)
        return val

    def pop_max(self):
        val = self.max()
        self.discard(val)
        return val

    def _insert(self, key):
        key = BHA_Float(key)
        if self.root is self.NIL:
            new_node = self.BlockNode()
            bisect.insort(new_node.keys, key)
            new_node.size = 1
            self.root = new_node
            self._min_node = new_node
            self._max_node = new_node
            return

        current = self.root
        parent = self.NIL
        while current is not self.NIL:
            min_key = current.keys[0] if len(current.keys) else None
            max_key = current.keys[-1] if len(current.keys) else None
            if min_key is not None and key < min_key and self._left(current) is not self.NIL:
                parent = current
                current = self._left(current)
            elif max_key is not None and key > max_key and self._right(current) is not self.NIL:
                parent = current
                current = self._right(current)
            else:
                break

        inserted_block = None
        if current is not self.NIL:
            idx = bisect.bisect_left(current.keys, key)
            if idx < current.size and current.keys[idx] == key:
                return
            bisect.insort(current.keys, key)
            current.size = len(current.keys)
            deepest = current
            inserted_block = current
        else:
            new_node = self.BlockNode()
            bisect.insort(new_node.keys, key)
            new_node.size = 1
            if key < parent.keys[0]:
                self._set_left(parent, new_node)
            else:
                self._set_right(parent, new_node)
            deepest = new_node
            inserted_block = new_node

        if key < self._min_node.keys[0]:
            self._min_node = inserted_block
        if key > self._max_node.keys[-1]:
            self._max_node = inserted_block
        was_max_block = self._addr(inserted_block) == self._addr(self._max_node)

        while len(deepest.keys) > self.BLOCK_SIZE:
            split_key = deepest.keys.pop()
            deepest.size = len(deepest.keys)
            right = self._right(deepest)
            if right is self.NIL:
                new_right = self.BlockNode()
                bisect.insort(new_right.keys, split_key)
                new_right.size = 1
                self._set_right(deepest, new_right)
                deepest = new_right
            else:
                leftmost = right
                while self._left(leftmost) is not self.NIL:
                    leftmost = self._left(leftmost)
                bisect.insort(leftmost.keys, split_key)
                leftmost.size = len(leftmost.keys)
                deepest = leftmost

        if was_max_block and self._addr(deepest) != self._addr(self._max_node):
            self._max_node = deepest

        self._rebalance(deepest)

    def add(self, key):
        key = BHA_Float(key)
        if key not in self:
            self._insert(key)

    def discard(self, key):
        if self.root is self.NIL:
            return
        key = BHA_Float(key)

        current = self.root
        while current is not self.NIL:
            min_key = current.keys[0] if len(current.keys) else None
            max_key = current.keys[-1] if len(current.keys) else None
            if min_key is not None and key < min_key:
                current = self._left(current)
            elif max_key is not None and key > max_key:
                current = self._right(current)
            else:
                break

        if current is self.NIL:
            return

        idx = bisect.bisect_left(current.keys, key)
        if idx >= len(current.keys) or current.keys[idx] != key:
            return

        was_min = (self._addr(current) == self._addr(self._min_node))
        was_max = (self._addr(current) == self._addr(self._max_node))

        current.keys.pop(idx)
        current.size = len(current.keys)
        self._rebalance(current)

        if current.size == 0:
            if was_min:
                self._min_node = self._find_leftmost(self.root)
            if was_max:
                self._max_node = self._find_rightmost(self.root)
        else:
            if was_min:
                self._min_node = current
            if was_max:
                self._max_node = current

    def __contains__(self, key):
        key = BHA_Float(key)
        node = self.root
        while node is not self.NIL:
            min_key = node.keys[0] if len(node.keys) else None
            max_key = node.keys[-1] if len(node.keys) else None
            if min_key is not None and key < min_key:
                node = self._left(node)
            elif max_key is not None and key > max_key:
                node = self._right(node)
            else:
                i = bisect.bisect_left(node.keys, key)
                if i < node.size and node.keys[i] == key:
                    return True
                break
        return False

    def __len__(self):
        count = 0
        stack = []
        current = self.root
        while stack or current is not self.NIL:
            while current is not self.NIL and self._left(current) is not self.NIL:
                stack.append(current)
                current = self._left(current)
            if current is not self.NIL:
                count += current.size
                current = self._right(current)
            if current is self.NIL and stack:
                current = stack.pop()
                count += current.size
                current = self._right(current)
        return count

    def __iter__(self):
        current = self.root
        while current is not self.NIL:
            if self._left(current) is self.NIL:
                yield from current.keys
                current = self._right(current)
            else:
                predecessor = self._left(current)
                while self._right(predecessor) is not self.NIL and self._addr(self._right(predecessor)) != self._addr(current):
                    predecessor = self._right(predecessor)
                if self._right(predecessor) is self.NIL:
                    predecessor.right = ctypes.pointer(current)
                    current = self._left(current)
                else:
                    predecessor.right = ctypes.pointer(self.NIL)
                    yield from current.keys
                    current = self._right(current)

    def __str__(self):
        return f"FloatRightSplitBlockAVLSet({{{','.join(map(str, self))}}})"
FloatRSBTSet = FloatRightSplitBlockAVLSet