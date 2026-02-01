from __future__ import annotations
from collections.abc import Iterable
from ..core import *
import builtins
def block_insert_sort(arr, start, end):
    for i in range(start + 1, end):
        current = arr[i]
        insert_pos = bisect.bisect_right(arr, current, start, i)
        j = i
        while j > insert_pos:
            arr[j], arr[j-1] = arr[j-1], arr[j]
            j -= 1
def merge_two_blocks(arr, left_start, left_end, right_end):
    if arr[left_end - 1] <= arr[left_end]:
        return
    left = arr[left_start:left_end]
    right = arr[left_end:right_end]
    i = j = 0
    k = left_start
    while i < len(left) and j < len(right):
        if left[i] <= right[j]:
            arr[k] = left[i]
            i += 1
        else:
            arr[k] = right[j]
            j += 1
        k += 1
    while i < len(left):
        arr[k] = left[i]
        i += 1
        k += 1
    while j < len(right):
        arr[k] = right[j]
        j += 1
        k += 1
class IntBitTag(BHA_bool, metaclass=ResurrectMeta):
    def __str__(self):
        return "'-1'" if (hasattr(self, 'is_sign_bit') and self.is_sign_bit and self) else "'1'" if self else "'0'"
    __repr__ = __str__
    __del__ = lambda self:self
class IntHybridArray(BoolHybridArray,metaclass=ResurrectMeta):
    def __init__(self, int_array: list[int], bit_length: int = 8):
        self.bit_length = bit_length
        bool_data = []
        max_required_bits = 1
        for num in int_array:
            if num == 0:
                required_bits = 1
            else:
                abs_num = abs(num)
                num_bits_needed = abs_num.bit_length()
                required_bits = 1 + num_bits_needed
            if required_bits > max_required_bits:
                max_required_bits = required_bits
        self.bit_length = max_required_bits
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
        self.total_bits = len(bool_data)
        super().__init__(0, self.total_bits, False, IntBitTag, False)
        for idx in range(self.total_bits):
            if idx < self.size:
                super().__setitem__(idx, bool_data[idx])
            else:
                super().append(bool_data[idx])
        for i in range(0, self.total_bits, self.bit_length):
            if i < self.size:
                bit_tag = super().__getitem__(i)
                bit_tag.is_sign_bit = True

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
                if block_end > self.size:
                    raise IndexError("索引超出范围")
                bit_chunk = [super(self.__class__, self).__getitem__(j) for j in range(block_start, block_end)]
                num = self.to_int(bit_chunk)
                result.append(num)
            return IntHybridArray(result, self.bit_length)
        key = key if key >= 0 else key + len(self)
        if not (0 <= key < len(self)):
            raise IndexError("索引超出范围")
        block_start = key * self.bit_length
        block_end = block_start + self.bit_length
        if block_end > self.size:
            raise IndexError("索引超出范围")
        bit_chunk = [super(self.__class__, self).__getitem__(j) for j in range(block_start, block_end)]
        return self.to_int(bit_chunk)

    def __setitem__(self, key, value):
        tmp1 = IntHybridArray([value],bit_length = self.bit_length)
        tmp = tmp1.view()
        if tmp1[0] == value:
            super().__setitem__(slice(key*self.bit_length,(key+1)*self.bit_length),tmp)
        else:
            lst = list(self)
            lst[key] = value
            self.__init__(lst)
    def __iter__(self):
        return map(self.__getitem__,range(len(self)))

    def __str__(self):
        return f"IntHybridArray([{', '.join(map(str, self))}])"
    __repr__ = __str__

    def __len__(self):
        return self.total_bits // self.bit_length
    def __delitem__(self, index: int = -1):
        index = index if index >= 0 else index + len(self)
        if not (0 <= index < len(self)):
            raise IndexError("删除索引超出范围")
        target_num = self[index]
        pop_bit_start = index * self.bit_length
        pop_bit_end = pop_bit_start + self.bit_length
        for _ in range(self.bit_length):
            super().__delitem__(pop_bit_start)
        self.total_bits -= self.bit_length
    def index(self, value):
        value = int(value)
        x = f"{value} 不在 IntHybridArray 中"
        for idx in range(len(self)+1>>1):
            if self[idx] == value:
                return idx
            elif self[-idx] == value:
                x = len(self)-idx
        if x != f"{value} 不在 IntHybridArray 中":
            return x
        raise ValueError(x)
    def rindex(self, value):
        value = int(value)
        x = f"{value} 不在 IntHybridArray 中"
        for idx in range(len(self)+1>>1):
            if self[-idx] == value:
                return -idx
            elif self[idx] == value:
                x = -(len(self)-idx)
        if x != f"{value} 不在 IntHybridArray 中":
            return x
        raise ValueError(x)
    def extend(self, iterable:Iterable) -> None:
        if isinstance(iterable, (Iterator, Generator, map)):
            iterable,copy = itertools.tee(iterable, 2)
            len_ = sum(1 for _ in copy)
        else:
            len_ = len(iterable)
        self.total_bits += len_*self.bit_length
        for i,j in zip(range(len_),iterable):
            self[-i-1] = j
    def append(self,value):
        self.total_bits += self.bit_length
        self.size = self.total_bits
        self[-1] = value
    def sort(self):
        n = len(self)
        BLOCK_SIZE = 32
        for start in range(0, n, BLOCK_SIZE):
            end = min(start + BLOCK_SIZE, n)
            block_insert_sort(self, start, end)
        merge_size = BLOCK_SIZE
        while merge_size < n:
            for start in range(0, n, merge_size * 2):
                mid = min(start + merge_size, n)
                end = min(start + merge_size * 2, n)
                if mid < end:
                    merge_two_blocks(self, start, mid, end)
            merge_size *= 2        
