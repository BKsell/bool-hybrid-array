# cython: language_level=3,boundscheck=False,wraparound=False,cdivision=True,nonecheck=False,overflowcheck=False,initializedcheck=False,infer_types=True,annotation_typing=True,profile=False,linetrace=False,emit_code_comments=False,c_api_binop_methods=True
from __future__ import annotations
from collections.abc import Iterable, MutableSet
from ..core import *
import builtins
from ..twg_sort import twg_sort


class IntBitTag(BHA_bool, metaclass=ResurrectMeta):
    def __str__(self):
        return "'-1'" if (hasattr(self, 'is_sign_bit') and self.is_sign_bit and self) else "'1'" if self else "'0'"
    __repr__ = __str__
    __del__ = lambda self: self


class IntHybridArray(MutableSequence, metaclass=ResurrectMeta):
    __reversed__ = BoolHybridArray.__reversed__

    def __init__(self, int_array: list[int], bit_length: int | None = None, Type=int):
        self.Type = Type
        self.bit_length = bit_length
        bool_data = []
        max_required_bits = 1
        for num in int_array:
            if num == 0:
                required_bits = 1
            else:
                abs_num = abs(num)
                required_bits = 1 + abs_num.bit_length()
            if required_bits > max_required_bits:
                max_required_bits = required_bits
        self.bit_length = max(bit_length, max_required_bits) if bit_length is not None else max_required_bits
        for num in int_array:
            if num >= 0:
                sign_bit = False
                num_bits = [bool((num >> i) & 1) for i in range(self.bit_length - 1)]
            else:
                sign_bit = True
                abs_num = abs(num)
                num_bits = [not bool((abs_num >> i) & 1) for i in range(self.bit_length - 1)]
                carry = 1
                for j in range(len(num_bits)):
                    if carry:
                        num_bits[j] = not num_bits[j]
                        carry = 0 if num_bits[j] else 1
            bool_data.append(sign_bit)
            bool_data.extend(num_bits)
        total_bits = len(bool_data)
        self._bits = BoolHybridArray(0, total_bits, False, IntBitTag, False)
        for idx in range(total_bits):
            if idx < self._bits.size:
                self._bits[idx] = bool_data[idx]
            else:
                self._bits.append(bool_data[idx])
        for i in range(0, total_bits, self.bit_length):
            if i < self._bits.size:
                bit_tag = self._bits[i]
                bit_tag.is_sign_bit = True

    def view(self):
        return self._bits

    def _set_bit(self, idx, value):
        value = bool(value)
        bits = self._bits
        if idx <= bits.split_index:
            bits.small[idx] = value
            return
        pos = bisect.bisect_left(bits.large, idx)
        exists = pos < len(bits.large) and bits.large[pos] == idx
        should_be_in_large = value if bits.is_sparse else not value
        if should_be_in_large and not exists:
            bits.large.insert(pos, idx)
        elif not should_be_in_large and exists:
            del bits.large[pos]

    def to_int(self, bit_chunk):
        sign_bit = bit_chunk[0].value
        num_bits = [bit.value for bit in bit_chunk[1:]]
        if not sign_bit:
            num = 0
            for j in range(len(num_bits)):
                if num_bits[j]:
                    num += (1 << j)
        else:
            num_bits_inv = [not b for b in num_bits]
            carry = 1
            for j in range(len(num_bits_inv)):
                if carry:
                    num_bits_inv[j] = not num_bits_inv[j]
                    carry = 0 if num_bits_inv[j] else 1
            num = 0
            for j in range(len(num_bits_inv)):
                if num_bits_inv[j]:
                    num += (1 << j)
            num = -num
        return num

    def __getitem__(self, key):
        if isinstance(key, slice):
            start, stop, step = key.indices(len(self))
            result = []
            for i in range(start, stop, step):
                block_start = i * self.bit_length
                block_end = block_start + self.bit_length
                if block_end > self._bits.size:
                    raise IndexError("索引超出范围")
                bit_chunk = [self._bits[j] for j in range(block_start, block_end)]
                num = self.to_int(bit_chunk)
                result.append(num)
            return IntHybridArray(result, self.bit_length, Type=self.Type)
        key = key if key >= 0 else key + len(self)
        if not (0 <= key < len(self)):
            raise IndexError("索引超出范围")
        block_start = key * self.bit_length
        block_end = block_start + self.bit_length
        if block_end > self._bits.size:
            raise IndexError("索引超出范围")
        bit_chunk = [self._bits[j] for j in range(block_start, block_end)]
        return self.Type(self.to_int(bit_chunk))

    @staticmethod
    def _encode_value(value, bl):
        if value >= 0:
            return [False] + [bool((value >> i) & 1) for i in range(bl - 1)]
        av = abs(value)
        mag = [not bool((av >> i) & 1) for i in range(bl - 1)]
        carry = 1
        for j in range(len(mag)):
            if carry:
                mag[j] = not mag[j]
                carry = 0 if mag[j] else 1
        return [True] + mag

    def __setitem__(self, key, value):
        if isinstance(key, slice):
            start, stop, step = key.indices(len(self))
            if step == 1:
                slice_len = stop - start
                if isinstance(value, IntHybridArray):
                    vlen = len(value)
                elif isinstance(value, (list, tuple)):
                    vlen = len(value)
                else:
                    vlen = -1
                if vlen == slice_len:
                    bl = self.bit_length
                    if isinstance(value, IntHybridArray) and value.bit_length == bl:
                        dst_base = start * bl
                        for i in range(vlen * bl):
                            self._set_bit(dst_base + i, bool(value._bits[i]))
                    else:
                        for off, v in enumerate(value):
                            bits = self._encode_value(int(v), bl)
                            base = (start + off) * bl
                            for bit_off, b in enumerate(bits):
                                self._set_bit(base + bit_off, b)
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
        key = key if key >= 0 else key + len(self)
        if not (0 <= key < len(self)):
            raise IndexError("索引超出范围")
        required = 1 + (abs(value).bit_length() if value != 0 else 1)
        old_bl = self.bit_length
        if required <= old_bl:
            bits = self._encode_value(value, old_bl)
            for off, b in enumerate(bits):
                self._set_bit(key * old_bl + off, b)
        else:
            delta = required - old_bl
            n = len(self)
            start = key * old_bl
            for _ in range(old_bl):
                del self._bits[start]
            for i in range(n - 2, -1, -1):
                sign = self._bits[i * old_bl]
                for _ in range(delta):
                    self._bits.insert(i * old_bl + old_bl, sign)
            self.bit_length = required
            bits = self._encode_value(value, required)
            for off, b in enumerate(bits):
                self._bits.insert(key * required + off, b)

    def __iter__(self):
        return map(self.__getitem__, range(len(self)))

    def __str__(self):
        return f"IntHybridArray([{', '.join(map(str, self))}])"
    __repr__ = __str__

    def __len__(self):
        return self._bits.size // self.bit_length

    def __delitem__(self, key):
        if isinstance(key, slice):
            start, stop, step = key.indices(len(self))
            indices = list(range(start, stop, step))
            for i in reversed(indices):
                del self[i]
            return
        key = key if key >= 0 else key + len(self)
        if not (0 <= key < len(self)):
            raise IndexError("删除索引超出范围")
        start = key * self.bit_length
        for _ in range(self.bit_length):
            del self._bits[start]

    def __contains__(self, value):
        value = int(value)
        for i in range(len(self)):
            if self[i] == value:
                return True
        return False

    def index(self, value, start=0, stop=None):
        value = int(value)
        n = len(self)
        if stop is None:
            stop = n
        start = max(0, start if start >= 0 else start + n)
        stop = min(n, stop if stop >= 0 else stop + n)
        for i in range(start, stop):
            if self[i] == value:
                return i
        raise ValueError(f"{value} 不在 IntHybridArray 中")

    def count(self, value):
        value = int(value)
        return sum(1 for i in range(len(self)) if self[i] == value)

    def __eq__(self, other) -> bool:
        if not isinstance(other, Iterable):
            return NotImplemented
        if len(self) != len(other) if hasattr(other, "__len__") else len(self) != len(BHA_Iterator(other)):
            return False
        return all(map(operator.eq, self, other))

    def __ne__(self, other) -> bool:
        return not self == other

    def extend(self, iterable):
        for v in iterable:
            self.append(v)

    def append(self, value):
        self.insert(len(self), value)

    def prepend(self, value):
        self.insert(0, value)

    def pop(self, index=-1):
        index = index if index >= 0 else index + len(self)
        if not (0 <= index < len(self)):
            raise IndexError("pop 索引超出范围")
        val = self[index]
        del self[index]
        return val

    def remove(self, value):
        try:
            idx = self.index(value)
        except ValueError:
            raise ValueError(f"{value} 不在 IntHybridArray 中")
        del self[idx]

    def clear(self):
        self._bits = BoolHybridArray(0, 0, False, IntBitTag, False)

    def reverse(self):
        n = len(self)
        for i in range(n >> 1):
            j = n - 1 - i
            self[i], self[j] = self[j], self[i]

    def __iadd__(self, other):
        self.extend(other)
        return self

    def __add__(self, other):
        result = IntHybridArray(list(self), bit_length=self.bit_length, Type=self.Type)
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
        result = IntHybridArray(list(self), bit_length=self.bit_length, Type=self.Type)
        result *= n
        return result
    __rmul__ = __mul__

    sort = twg_sort

    def insert(self, index, value):
        index = index if index >= 0 else index + len(self)
        index = max(0, min(index, len(self)))
        required = 1 + (abs(value).bit_length() if value != 0 else 1)
        old_bl = self.bit_length
        if required > old_bl:
            delta = required - old_bl
            n = len(self)
            for i in range(n - 1, -1, -1):
                sign = self._bits[i * old_bl]
                for _ in range(delta):
                    self._bits.insert(i * old_bl + old_bl, sign)
            self.bit_length = required
        bl = self.bit_length
        bits = self._encode_value(value, bl)
        start = index * bl
        for off, b in enumerate(bits):
            self._bits.insert(start + off, b)


node_create_count = 0


class RightSplitBlockAVLSet(MutableSet):
    BLOCK_SIZE = 16

    class BlockNode(ctypes.Structure):
        def __init__(self):
            global node_create_count
            node_create_count += 1
            self.keys = IntHybridArray([])
            self.size = 0
            self.height = 1
            if "RightSplitBlockAVLSet" in globals():
                _nilp = ctypes.pointer(RightSplitBlockAVLSet.NIL)
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
            min_key = current.keys[0] if current.keys else None
            max_key = current.keys[-1] if current.keys else None
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
        if key not in self:
            self._insert(key)

    def _search_block(self, node, key):
        if node is self.NIL:
            return self.NIL
        if node.size == 0:
            r = self._search_block(self._left(node), key)
            if r is not self.NIL:
                return r
            return self._search_block(self._right(node), key)
        min_key = node.keys[0]
        max_key = node.keys[-1]
        if key < min_key:
            return self._search_block(self._left(node), key)
        elif key > max_key:
            return self._search_block(self._right(node), key)
        return node

    def discard(self, key):
        if self.root is self.NIL:
            return

        current = self._search_block(self.root, key)
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
        node = self._search_block(self.root, key)
        if node is self.NIL:
            return False
        i = bisect.bisect_left(node.keys, key)
        return i < node.size and node.keys[i] == key

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
        return f"RightSplitBlockAVLSet({{{','.join(map(str, self))}}})"
IntRSBTSet = RightSplitBlockAVLSet
