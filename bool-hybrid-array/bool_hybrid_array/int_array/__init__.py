from __future__ import annotations
from ..core import *
import builtins

class IntBitTag(BHA_Bool, metaclass=ResurrectMeta):
    def __str__(self):
        return "'-1'" if (hasattr(self, 'is_sign_bit') and self.is_sign_bit and self) else "'1'" if self else "'0'"
    __repr__ = __str__

class IntHybridArray(BoolHybridArray):
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
                bit_chunk = [super().__getitem__(j) for j in range(block_start, block_end)]
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
        bit_chunk = [super().__getitem__(j) for j in range(block_start, block_end)]
        return self.to_int(bit_chunk)

    def __setitem__(self, key, value):
        value = int(value)
        if isinstance(key, slice):
            start, stop, step = key.indices(len(self))
            values = list(value) if isinstance(value, (list, tuple, IntHybridArray)) else [value] * ((stop - start + step - 1) // step)
            idx = 0
            for int_idx in range(start, stop, step):
                block_start = int_idx * self.bit_length
                block_end = block_start + self.bit_length
                if block_end > self.size:
                    raise IndexError("索引超出范围")
                num = values[idx % len(values)]
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
                bool_data = [sign_bit] + num_bits
                for bit_idx in range(self.bit_length):
                    super().__setitem__(block_start + bit_idx, bool_data[bit_idx])
                idx += 1
            return
        key = key if key >= 0 else key + len(self)
        if not (0 <= key < len(self)):
            raise IndexError("索引超出范围")
        block_start = key * self.bit_length
        block_end = block_start + self.bit_length
        if block_end > self.size:
            raise IndexError("索引超出范围")
        num = value
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
        bool_data = [sign_bit] + num_bits
        for bit_idx in range(self.bit_length):
            super().__setitem__(block_start + bit_idx, bool_data[bit_idx])

    def __iter__(self):
        for i in range(0, self.total_bits, self.bit_length):
            if i + self.bit_length > self.size:
                break
            bit_chunk = [super().__getitem__(j) for j in range(i, i + self.bit_length)]
            yield self.to_int(bit_chunk)

    def __str__(self):
        return f"IntHybridArray([{', '.join(map(str, self))}])"
    __repr__ = __str__

    def __len__(self):
        return self.total_bits // self.bit_length