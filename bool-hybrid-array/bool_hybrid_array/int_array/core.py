from __future__ import annotations
from collections.abc import Iterable,MutableSet
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
        if isinstance(key, slice):
            start, stop, step = key.indices(len(self))
            for i,v in zip(range(start,stop,step),value):self[i] = v
            return
        tmp1 = IntHybridArray([value],bit_length = self.bit_length)
        tmp = tmp1.view()
        if tmp1[0] == value:
            for i,v in zip(range(key*self.bit_length,(key+1)*self.bit_length),tmp):
                super().__setitem__(i,v)
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
        start = 0
        while start < n - 1:
            end = start
            while end < n - 1 and self[end] > self[end + 1]:
                end += 1
            segment_length = end - start + 1
            if segment_length > 3:
                self[start:end+1] = self[start:end+1][::-1]
            start = end + 1
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
    def insert(self,index,value):
        tmp1 = IntHybridArray([value],bit_length = self.bit_length)
        tmp = tmp1.view()
        if tmp1[0] == value:
            for i,v in zip(range(index*self.bit_length,(index+1)*self.bit_length),tmp):
                super().insert(i,v)
        else:
            lst = list(self)
            lst.insert(index,value)
            self.__init__(lst)

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
                self.left = self.right = ctypes.POINTER(RightSplitBlockAVLSet.BlockNode)()
    BlockNode._fields_ = [
            ("keys", ctypes.py_object),
            ("size", ctypes.c_uint8),
            ("left", ctypes.POINTER(BlockNode)),
            ("right", ctypes.POINTER(BlockNode)),
            ("height", ctypes.c_uint16),
        ]
    NULL = BlockNode()
    NULL.height = 0
    NULL.size = 0

    def __init__(self, iterable=None):
        self.root = self.NULL
        if iterable is not None:
            for val in iterable:
                self.add(val)

    def _insert(self, key):
        if self.root is self.NULL:
            new_node = self.BlockNode()
            bisect.insort(new_node.keys, key)
            new_node.size = 1
            self.root = new_node
            return

        current = self.root
        path = []

        while True:
            path.append(current)
            if key in current.keys:
                return
            
            bisect.insort(current.keys, key)
            current.size = len(current.keys)
            
            split_key = None
            if len(current.keys) > self.BLOCK_SIZE:
                split_key = current.keys.pop()
                current.size = len(current.keys)
            
            if split_key is not None:
                right_parent = current
                right_current = right_parent.right.contents if right_parent.right else self.NULL
                
                while True:
                    if right_current is self.NULL:
                        new_right = self.BlockNode()
                        bisect.insort(new_right.keys, split_key)
                        new_right.size = 1
                        if not right_parent.right:
                            right_parent.right = ctypes.pointer(self.NULL)
                        right_parent.right.contents = new_right
                        path.append(new_right)
                        break
                    
                    bisect.insort(right_current.keys, split_key)
                    right_current.size = len(right_current.keys)
                    
                    if len(right_current.keys) > self.BLOCK_SIZE:
                        split_key = right_current.keys.pop()
                        right_current.size = len(right_current.keys)
                        right_parent = right_current
                        right_current = right_parent.right.contents if right_parent.right else self.NULL
                    else:
                        path.append(right_current)
                        break
            
            break

        while path:
            node = path.pop()
            left_height = self._get_height(node.left.contents) if node.left else 0
            right_height = self._get_height(node.right.contents) if node.right else 0
            node.height = 1 + max(left_height, right_height)

    def discard(self, key):
        if self.root is self.NULL:
            return
        
        current = self.root
        target_node = None
        
        while current is not self.NULL:
            if key in current.keys:
                target_node = current
                break
            
            min_key = current.keys[0] if current.keys else None
            max_key = current.keys[-1] if current.keys else None
            if min_key and key < min_key:
                current = current.left.contents if (current.left and current.left.contents is not self.NULL) else self.NULL
            elif max_key and key > max_key:
                current = current.right.contents if (current.right and current.right.contents is not self.NULL) else self.NULL
            else:
                break
        
        if target_node is not None:
            idx = bisect.bisect_left(target_node.keys, key)
            if idx < len(target_node.keys) and target_node.keys[idx] == key:
                target_node.keys.pop(idx)
                target_node.size = len(target_node.keys)
                left_height = self._get_height(target_node.left.contents) if target_node.left else 0
                right_height = self._get_height(target_node.right.contents) if target_node.right else 0
                target_node.height = 1 + max(left_height, right_height)

    def _get_height(self, node):
        return node.height if node is not self.NULL else 0

    def add(self, key):
        if key not in self:
            self._insert(key)

    def __contains__(self, key):
        node = self.root
        while node is not self.NULL:
            min_key = node.keys[0] if node.keys else None
            max_key = node.keys[-1] if node.keys else None
            if min_key and key < min_key:
                node = node.left.contents if node.left else self.NULL
            elif max_key and key > max_key:
                node = node.right.contents if node.right else self.NULL
            elif (i:=bisect.bisect_left(node.keys,key))<node.size and node.keys[i] == key:
                return True
            else:
                break
        else:return False

    def _update_heights(self, start_node):
        stack = []
        current = start_node
        while current is not self.NULL or stack:
            while current is not self.NULL:
                stack.append(current)
                current = current.left.contents if current.left else self.NULL
            current = stack.pop()
            current.height = 1 + max(self._get_height(current.left.contents) if current.left else 0,
                                  self._get_height(current.right.contents) if current.right else 0)
            current = current.right.contents if current.right else self.NULL

    def __len__(self):
        count = 0
        stack = []
        current = self.root
        while stack or current is not self.NULL:
            while current is not self.NULL and current.left and current.left.contents is not self.NULL:
                stack.append(current)
                current = current.left.contents
            if current is not self.NULL:
                count += current.size
                current = current.right.contents if current.right else self.NULL
            if not current and stack:
                current = stack.pop()
                count += current.size
                current = current.right.contents if current.right else self.NULL
        return count
    def __iter__(self):
        current = self.root
        while current is not self.NULL and current:
            if not current.left or current.left.contents is self.NULL:
                yield from current.keys
                current = current.right.contents if current.right else self.NULL
            else:
                predecessor = current.left.contents
                while predecessor.right is not None and predecessor.right.contents is not self.NULL and predecessor.right.contents != current and predecessor.right:
                    predecessor = predecessor.right.contents
                if predecessor.right is None or predecessor.right.contents is self.NULL or not predecessor.right:
                    predecessor.right = ctypes.pointer(current)
                    current = current.left.contents if current.left else self.NULL
                else:
                    predecessor.right = ctypes.pointer(self.NULL)
                    yield from current.keys
                    current = current.right.contents if current.right else self.NULL
    def __str__(self):
        return f"RightSplitBlockAVLSet({{{','.join(map(str, self))}}})"
