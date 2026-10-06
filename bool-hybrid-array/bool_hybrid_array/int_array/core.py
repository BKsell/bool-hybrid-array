# cython: language_level=3,boundscheck=False,wraparound=False,cdivision=True,nonecheck=False,overflowcheck=False,initializedcheck=False,infer_types=True,annotation_typing=True,profile=False,linetrace=False,emit_code_comments=False,c_api_binop_methods=True
from __future__ import annotations
from collections.abc import Iterable, MutableSequence, MutableSet
from ..core import *
from ..twg_sort import twg_sort
import builtins, ctypes, numpy as np, itertools, bisect, operator


class IntBitTag(BHA_bool, metaclass=ResurrectMeta):
    def __str__(self):
        return "'-1'" if (hasattr(self, 'is_sign_bit') and self.is_sign_bit and self) else "'1'" if self else "'0'"
    __repr__ = __str__
    __del__ = lambda self: self


class IntHybridArray(MutableSequence, metaclass=ResurrectMeta):
    def __reversed__(self):
        if not self:
            return BHA_Iterator([])
        return BHA_Iterator(map(self.__getitem__, range(len(self) - 1, -1, -1)))

    def __deepcopy__(self, memo):
        return type(self)(iter(self), bit_length=self.bit_length, Type=self.Type)

    def __copy__(self):
        return type(self)(iter(self), bit_length=self.bit_length, Type=self.Type)

    def copy(self):
        return type(self)._from_bits(self._bits.copy(), self.bit_length, self.Type)

    def __init__(self, int_array=(), bit_length=None, Type=int, *, hash_=True):
        self.Type = Type
        it0 = iter(int_array)
        if isinstance(it0, BHA_Iterator):
            it0 = it0.data
        first, second = itertools.tee(it0, 2)
        max_required_bits = 1
        for num in first:
            if num == 0:
                required_bits = 1
            else:
                required_bits = 1 + abs(int(num)).bit_length()
            if required_bits > max_required_bits:
                max_required_bits = required_bits
        self.bit_length = max(bit_length, max_required_bits) if bit_length is not None else max_required_bits

        def _gen():
            for num in second:
                num = int(num)
                if num >= 0:
                    yield False
                    for i in range(self.bit_length - 1):
                        yield bool((num >> i) & 1)
                else:
                    yield True
                    av = abs(num)
                    carry = 1
                    for i in range(self.bit_length - 1):
                        b = not bool((av >> i) & 1)
                        if carry:
                            b = not b
                            carry = 0 if b else 1
                        yield b

        self._bits = BoolHybridArr(_gen(), Type=IntBitTag, hash_=hash_)

    @classmethod
    def _from_bits(cls, bits_bha, bl, Type, hash_=False):
        """从现成位段 BHA 直接构造（O(1)，绕过逐值编码）。"""
        obj = cls.__new__(cls)
        obj.Type = Type
        obj.bit_length = bl
        obj._bits = bits_bha
        return obj

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

    def _bit(self, idx):
        return bool(self._bits[idx])


    def to_int(self, bit_chunk):
        sign_bit = bit_chunk[0].value
        num_bits = [bit.value for bit in bit_chunk[1:]]
        if not sign_bit:
            num = 0
            for j in range(len(num_bits)):
                if num_bits[j]:
                    num += int(1) << j
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
                    num += int(1) << j
            num = -num
        return num

    def __getitem__(self, key):
        if isinstance(key, slice):
            start, stop, step = key.indices(len(self))
            bl = self.bit_length
            bits = self._bits
            if step == 1:
                seg = bits._slice_bits(start * bl, stop * bl)
                return IntHybridArray._from_bits(seg, bl, self.Type, hash_=False)
            def _slice_gen():
                for i in range(start, stop, step):
                    block_start = i * bl
                    if block_start + bl > bits.size:
                        raise IndexError("索引超出范围")
                    yield self._decode_block(block_start)
            return IntHybridArray(_slice_gen(), bl, Type=self.Type, hash_=False)
        key = key if key >= 0 else key + len(self)
        if not (0 <= key < len(self)):
            raise IndexError("索引超出范围")
        block_start = key * self.bit_length
        block_end = block_start + self.bit_length
        if block_end > self._bits.size:
            raise IndexError("索引超出范围")
        return self.Type(self._decode_block(block_start))

    @staticmethod
    def _encode_gen(value, bl):
        """生成 value 的 bl 位补码编码（迭代器，避免 BHA 构造开销）。"""
        if value >= 0:
            return (bool((value >> (i - 1)) & 1) if i else False for i in range(bl))
        av = abs(value)
        def _gen():
            yield True
            carry = 1
            for i in range(bl - 1):
                b = not bool((av >> i) & 1)
                if carry:
                    b = not b
                    carry = 0 if b else 1
                yield b
        return _gen()

    @staticmethod
    def _encode_value(value, bl):
        return BoolHybridArr(IntHybridArray._encode_gen(value, bl), hash_=False)


    def _decode_block(self, block_start):
        bl = self.bit_length
        bits = self._bits
        split = bits.split_index
        raw = 0
        small_len = 0
        if block_start <= split:
            # small 段（字节段批量）
            small_len = min(split + 1, block_start + bl) - block_start
            sm = bits.small
            start_byte = block_start >> 3
            seg = int.from_bytes(
                sm.data[start_byte:((block_start + small_len + 7) >> 3)].tobytes(), 'little')
            raw = (seg >> (block_start & 7)) & ((int(1) << small_len) - int(1))
        large_start = block_start + small_len
        n_large = bl - small_len
        if n_large > 0:
            # large 段（稀疏索引批量：一次 bisect 定位 + 顺序扫描）
            large = bits.large
            is_sparse = bits.is_sparse
            lo = bisect.bisect_left(large, large_start)
            hi = bisect.bisect_left(large, large_start + n_large)
            if is_sparse:
                for p in large[lo:hi]:
                    raw |= int(1) << ((p - large_start) + small_len)
            else:
                raw |= ((int(1) << n_large) - int(1)) << small_len
                for p in large[lo:hi]:
                    raw &= ~(int(1) << ((p - large_start) + small_len))
        mag_bits = raw >> 1
        if not (raw & 1):
            return mag_bits
        mag = ((int(1) << (bl - 1)) - int(1)) ^ mag_bits
        return -(mag + 1)

    def _expand_bit_length(self, delta, n, old_bl):
        required = old_bl + delta
        bits = self._bits
        split = bits.split_index
        if split >= 0:
            sm = bits.small
            small_bits = split + 1
            full_blocks = small_bits // old_bl
            rem = small_bits % old_bl
            val = int.from_bytes(sm.data.tobytes(), 'little')
            new_val = 0
            shift = 0
            for b in range(full_blocks):
                block = (val >> (b * old_bl)) & ((int(1) << old_bl) - int(1))
                new_val |= block << shift
                shift += old_bl
                sign = block & 1
                new_val |= (sign * ((int(1) << delta) - int(1))) << shift
                shift += delta
            if rem:
                block = (val >> (full_blocks * old_bl)) & ((int(1) << rem) - int(1))
                new_val |= block << shift
                shift += rem
            new_small_bits = small_bits + full_blocks * delta
            new_n = (new_small_bits + 7) >> 3
            sm.data = np.frombuffer(new_val.to_bytes(new_n, 'little'), dtype=np.uint8).copy()
            sm.n_uint8 = new_n
            sm.size = new_small_bits
            sm._cptr = None
            bits.split_index = split + full_blocks * delta
        if len(bits.large):
            if isinstance(bits.large, array.array):
                bits.large = array.array(bits.large.typecode, ((x // old_bl) * required + (x % old_bl) for x in bits.large))
            else:
                bits.large = [(x // old_bl) * required + (x % old_bl) for x in bits.large]
        if split >= 0 and rem:
            sign_val = (new_val >> (full_blocks * required)) & 1
            if (bits.is_sparse and sign_val) or (not bits.is_sparse and not sign_val):
                ext_start = full_blocks * required + old_bl
                large = bits.large
                for k in range(delta):
                    p = ext_start + k
                    pos = bisect.bisect_right(large, p)
                    large.insert(pos, p)
        if len(bits.large):
            large = bits.large
            if split >= 0:
                first_large_block = full_blocks + (1 if rem else 0)
            else:
                first_large_block = 0
            for b in range(first_large_block, n):
                sign_pos = b * required
                lo = bisect.bisect_left(large, sign_pos)
                if lo < len(large) and large[lo] == sign_pos:
                    ext_start = sign_pos + old_bl
                    for k in range(delta):
                        p = ext_start + k
                        pos = bisect.bisect_right(large, p)
                        large.insert(pos, p)
        bits.size = n * required
        self.bit_length = required

    def _set_block(self, key, value):
        bl = self.bit_length
        bits = self._bits
        split = bits.split_index
        block_start = key * bl
        if value >= 0:
            enc = value << 1
        else:
            enc = 1 + (((int(1) << (bl - 1)) + value) << 1)
        small_len = 0
        if block_start <= split:
            # small 段（字节段批量）
            small_len = min(split + 1, block_start + bl) - block_start
            sm = bits.small
            start_byte = block_start >> 3
            end_byte = (block_start + small_len + 7) >> 3
            seg = int.from_bytes(sm.data[start_byte:end_byte].tobytes(), 'little')
            shift = block_start & 7
            mask = ((int(1) << small_len) - int(1)) << shift
            seg = (seg & ~mask) | ((enc & ((int(1) << small_len) - int(1))) << shift)
            sm.data[start_byte:end_byte] = np.frombuffer(
                seg.to_bytes(end_byte - start_byte, 'little'), dtype=np.uint8).copy()
        large_start = block_start + small_len
        n_large = bl - small_len
        if n_large > 0:
            # large 段（稀疏索引批量：期望存在集合与现有集合的差）
            large = bits.large
            is_sparse = bits.is_sparse
            large_enc = (enc >> small_len) & ((int(1) << n_large) - int(1))
            need = []
            for i in range(n_large):
                if ((large_enc >> i) & 1) == (1 if is_sparse else 0):
                    need.append(large_start + i)
            lo = bisect.bisect_left(large, large_start)
            hi = bisect.bisect_left(large, large_start + n_large)
            existing = list(large[lo:hi])
            need_set = set(need)
            for k in range(len(existing) - 1, -1, -1):
                if existing[k] not in need_set:
                    del large[lo + k]
            if need:
                existing_set = set(existing)
                for p in need:
                    if p not in existing_set:
                        pos = bisect.bisect_left(large, p)
                        large.insert(pos, p)

    def __setitem__(self, key, value):
        if isinstance(key, slice):
            start, stop, step = key.indices(len(self))
            if step == 1:
                bl = self.bit_length
                if isinstance(value, IntHybridArray) and value.bit_length == bl and len(value) == stop - start:
                    self._bits._replace_bits(start * bl, stop * bl, value._bits)
                    return
                if isinstance(value, (list, tuple, IntHybridArray)) or hasattr(value, '__iter__'):
                    del self[start:stop]
                    for off, v in enumerate(value):
                        self.insert(start + off, v)
                    return
                for i in range(start, stop):
                    self[i] = value
                return
            if isinstance(value, (list, tuple)):
                indices = range(start, stop, step)
                if len(value) != len(indices):
                    raise ValueError(f"值数量不匹配")
                for i, v in zip(indices, value):
                    self[i] = v
            else:
                for i in range(start, stop, step):
                    self[i] = value
            return
        key = key if key >= 0 else key + len(self)
        if not (0 <= key < len(self)):
            raise IndexError("索引超出范围")
        try:
            value = operator.index(value)
        except TypeError:
            raise TypeError("IntHybridArray 只接受整数") from None
        required = 1 if value == 0 else 1 + abs(value).bit_length()
        old_bl = self.bit_length
        if required <= old_bl:
            self._set_block(key, value)
        else:
            delta = required - old_bl
            n = len(self)
            self._expand_bit_length(delta, n, old_bl)
            self._set_block(key, value)

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
            if step > 0:
                for i in reversed(range(start, stop, step)):
                    del self[i]
            else:
                for i in range(start, stop, step):
                    del self[i]
            return
        key = key if key >= 0 else key + len(self)
        if not (0 <= key < len(self)):
            raise IndexError("删除索引超出范围")
        start = key * self.bit_length
        self._bits._del_bits(start, start + self.bit_length)

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

    def extend(self, iterable):
        for v in iterable:
            self.append(v)

    def append(self, value):
        try:
            value = operator.index(value)
        except TypeError:
            raise TypeError("IntHybridArray 只接受整数") from None
        required = 1 if value == 0 else 1 + abs(value).bit_length()
        bl = self.bit_length
        n = len(self)
        if required > bl:
            self._expand_bit_length(required - bl, n, bl)
            bl = required
        if value >= 0:
            enc = value << 1
        else:
            enc = 1 + (((int(1) << (bl - 1)) + value) << 1)
        bits = self._bits
        for i in range(bl):
            bits.append(bool((enc >> i) & 1))

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
        result = IntHybridArray(iter(self), bit_length=self.bit_length, Type=self.Type, hash_=False)
        result.extend(other)
        return result

    def __imul__(self, n):
        n = operator.index(n)
        if n <= 0:
            self.clear()
            return self
        if n == 1:
            return self
        # 位级拼接：把 self 的位模式整块复制 n 次（几何级数大整数 + large 平移）
        bits = self._bits
        L = bits.size
        if L == 0:
            return self
        if bits.split_index >= 0:
            sm = bits.small
            v = int.from_bytes(sm.data.tobytes(), 'little') & ((int(1) << sm.size) - int(1))
            # 每份扩展为完整 L 位：large 区占位按稀疏语义显式写入（非稀疏默认全真，稀疏默认全假）
            if not bits.is_sparse:
                v |= ((int(1) << L) - (int(1) << sm.size))
                for x in bits.large:
                    v &= ~(int(1) << x)
            else:
                for x in bits.large:
                    v |= int(1) << x
            if v:
                # 倍增拼接：res 按 v 的 2^k 份倍增，n 二进制分解（避免大整数除法）
                rep = 0
                step = v
                cnt = 1
                shift = 0
                rem_n = n
                while rem_n:
                    if rem_n & 1:
                        rep |= step << shift
                        shift += cnt * L
                    step = step | (step << (cnt * L))
                    cnt *= 2
                    rem_n >>= 1
            else:
                rep = 0
            new_small_bits = n * L
            new_nb = (new_small_bits + 7) >> 3
            sm.data = np.frombuffer(rep.to_bytes(new_nb, 'little'), dtype=np.uint8).copy()
            sm.size = new_small_bits
            sm.n_uint8 = new_nb
            sm._cptr = None
            bits.split_index = (n - 1) * L + bits.split_index
            # large 区只保留最后一份的索引（中间份已显式并入 small.data）
            if len(bits.large):
                if isinstance(bits.large, array.array):
                    bits.large = array.array(bits.large.typecode, (x + (n - 1) * L for x in bits.large))
                else:
                    bits.large = [x + (n - 1) * L for x in bits.large]
        else:
            # split=-1：small 空，全部在 large
            if len(bits.large):
                if isinstance(bits.large, array.array):
                    bits.large = array.array(bits.large.typecode, (x + k * L for k in range(n) for x in bits.large))
                else:
                    bits.large = [x + k * L for k in range(n) for x in bits.large]
        bits.size = L * n
        return self

    def __mul__(self, n):
        result = IntHybridArray(iter(self), bit_length=self.bit_length, Type=self.Type, hash_=False)
        result *= n
        return result
    __rmul__ = __mul__

    def __hash__(self):
        return hash(self._bits)

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
        if type(self) is type(other) and getattr(other, 'bit_length', None) == self.bit_length:
            return self._bits == other._bits
        return all(map(operator.eq, self, other))

    def __ne__(self, other) -> bool:
        return not self == other

    sort = twg_sort

    def swap(self, idx1, idx2):
        """直接交换底层位数组的两个元素块，避免解码/编码。"""
        n = len(self)
        if idx1 < 0:
            idx1 += n
        if idx2 < 0:
            idx2 += n
        if not (0 <= idx1 < n and 0 <= idx2 < n):
            raise IndexError("swap 索引超出范围")
        if idx1 == idx2:
            return
        bl = self.bit_length
        bits = self._bits
        b1 = idx1 * bl
        b2 = idx2 * bl
        for i in range(bl):
            x = bits[b1 + i]
            y = bits[b2 + i]
            bits[b1 + i] = y
            bits[b2 + i] = x

    def move(self, idx1, length, idx2):
        """剪切 [idx1, idx1+length) 这 length 个元素，插入到删除后数组的第 idx2 位。
        直接操作底层位数组，避免解码/编码。"""
        n = len(self)
        if idx1 < 0:
            idx1 += n
        if idx2 < 0:
            idx2 += n
        idx1 = max(0, min(idx1, n))
        length = max(0, min(length, n - idx1))
        if length == 0:
            return
        # memmove 式：块最终占 [idx2, idx2+length)，越界 clamp
        idx2 = max(0, min(idx2, n - length))
        if idx2 == idx1:
            return
        bl = self.bit_length
        bits = self._bits
        start1 = idx1 * bl
        nbits = length * bl
        target = idx2 * bl
        # small 区内：一次大整数重组（免 unpackbits 全量展开、免 _del_range/_ins_range 双移位、size 不变故不触发扩容）
        if start1 + nbits <= bits.split_index + 1 and target + nbits <= bits.split_index + 1:
            sm = bits.small
            old_size = sm.size
            val = int.from_bytes(sm.data.tobytes(), 'little')
            seg1 = val & ((int(1) << start1) - int(1)) if start1 else 0
            chunk = (val >> start1) & ((int(1) << nbits) - int(1))
            tail_len = old_size - start1 - nbits
            seg2 = (val >> (start1 + nbits)) & ((int(1) << tail_len) - int(1)) if tail_len > 0 else 0
            if target <= start1:
                seg1_low = seg1 & ((int(1) << target) - int(1)) if target else 0
                seg1_high = seg1 >> target
                new_val = seg1_low | (chunk << target) | (seg1_high << (target + nbits)) | (seg2 << (start1 + nbits))
            else:
                off = target - start1
                seg2_low = seg2 & ((int(1) << off) - int(1)) if off else 0
                seg2_high = seg2 >> off
                new_val = seg1 | (seg2_low << start1) | (chunk << (start1 + off)) | (seg2_high << (start1 + off + nbits))
            new_n = (old_size + 7) >> 3
            sm.data = np.frombuffer(new_val.to_bytes(new_n, 'little'), dtype=np.uint8).copy()
            sm.n_uint8 = new_n
            sm._cptr = None
            return
        chunk = bits._slice_bits(start1, start1 + nbits)
        bits._del_bits(start1, start1 + nbits)
        # idx2 指删除后数组中的插入位置；块最终占 [idx2, idx2+length)
        bits._insert_bits(target, chunk)

    def insert(self, index, value):
        index = index if index >= 0 else index + len(self)
        index = max(0, min(index, len(self)))
        try:
            value = operator.index(value)
        except TypeError:
            raise TypeError("IntHybridArray 只接受整数") from None
        required = 1 if value == 0 else 1 + abs(value).bit_length()
        old_bl = self.bit_length
        if required > old_bl:
            self._expand_bit_length(required - old_bl, len(self), old_bl)
        bl = self.bit_length
        self._bits._insert_bits(index * bl, self._encode_value(value, bl))
import ctypes as _ct


import bisect
import ctypes as _ct
from collections.abc import MutableSet


class RightSplitBlockAVLSet(MutableSet):
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

    def _n(self, addr) -> object:
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
        x = self._n(x_addr)
        y_addr = x.left
        self._set_left(x_addr, self._n(y_addr).right)
        self._replace(x_addr, y_addr)
        self._set_right(y_addr, x_addr)
        self._upd_h(x_addr)
        self._upd_h(y_addr)
        return y_addr

    def _rot_left(self, x_addr):
        x = self._n(x_addr)
        y_addr = x.right
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
            k0 = ks[0]
            kl = ks[len(ks) - 1]
            if key < k0:
                if n.left and n.left != self._nil_addr:
                    stack.append(n.left)
            elif key > kl:
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
            if nk:
                mk = nk[0]
                xk = nk[len(nk) - 1]
            else:
                mk = None
                xk = None
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
        node = self._search(self.root, key)
        if node:
            nk = self._nk[node]
            n = self._n(node)
            idx = bisect.bisect_left(nk, key)
            if idx < n.size and nk[idx] == key:
                return
        self._insert(key)

    def discard(self, key):
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
        node = self._search(self.root, key)
        if not node:
            return False
        nk = self._nk[node]
        n = self._n(node)
        i = bisect.bisect_left(nk, key)
        return i < n.size and nk[i] == key

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
        return "RightSplitBlockAVLSet({" + ",".join(map(str, self)) + "})"


IntRSBTSet = RightSplitBlockAVLSet
