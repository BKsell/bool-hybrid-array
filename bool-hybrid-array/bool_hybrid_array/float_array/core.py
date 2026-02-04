from __future__ import annotations
from collections.abc import Sequence
from ..int_array import IntHybridArray
from ..core import BHA_Iterator
import operator,math,itertools
class BHA_Float(float):
    def __init__(self, data: int | str | float | BHA_Float | tuple):
        if isinstance(data, tuple):
            self.a,self.b,self.length = data
            return
        if isinstance(data, BHA_Float):
            self.a = data.a
            self.b = data.b
            self.length = data.length
            return
        if isinstance(data, int):
            data = float(data)
        if isinstance(data, float):
            data = repr(data)
        a, b = data.split('.')
        b = b.rstrip('0')
        self.length = len(b) if b else 1
        self.a, self.b = int(a) if a else 0, int(b) if b else 0

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

    def __truediv__(self, other, total_decimal = 22):
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
    __rsub__ = lambda self,other:BHA_Float(other)-self
    __rtruediv__ = lambda self,other:BHA_Float(other)/self
    def __float__(self):
        return float(str(self))
    def __int__(self):
        return self.a
    is_integer = lambda self:not self.b
    __bool__ = lambda self:self.a or self.b
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
    def __eq__(self,other):
        try:
            other = BHA_Float(other)
            self_num, other_num, _ = self._align_decimal(other)
            return self_num == other_num
        except (ValueError, AttributeError):
            return False
    def __floordiv__(self, other):
        return BHA_Float(int(float(self / other)))
    def __mod__(self, other):
        return self - (self // other) * other
    def __pow__(self, power, m = None):
        return BHA_Float(pow(float(self),float(BHA_Float(power)),m))
    def __neg__(self):
        return BHA_Float((-self.a, self.b, self.length))
    def __pos__(self):
        return self
    def __abs__(self):
        return BHA_Float((abs(self.a), self.b, self.length))
    def __lt__(self,other):
        a, b, _ = self._align_decimal(other)
        return a<b
    def __gt__(self,other):
        a, b, _ = self._align_decimal(other)
        return a>b
    def __round__(self,n = None):
        return round(float(self),n)
    __rmod__ = lambda self,other:BHA_Float(other)%self
    __rfloordiv__ = lambda self,other:BHA_Float(other)//self
    __rpow__ = lambda self,other,m=None:pow(BHA_Float(other),self,m)
class FloatHybridArray(Sequence):
    def __init__(self,data,Type = BHA_Float):
        self.Type = Type
        data = BHA_Iterator(map(BHA_Float,data))
        self.lengths = IntHybridArray(map(operator.attrgetter('length'),data))
        self.a = IntHybridArray(map(operator.attrgetter('a'),data))
        self.b = IntHybridArray(map(operator.attrgetter('b'),data))
    def __getitem__(self,index):
        return self.Type(BHA_Float((self.a[index],self.b[index],self.lengths[index])))
    def __setitem__(self,index,value):
        value = BHA_Float(value)
        self.lengths[index] = value.length
        self.a[index] = value.a
        self.b[index] = value.b
    def append(self,value):
        value = BHA_Float(value)
        self.lengths.append(value.length)
        self.a.append(value.a)
        self.b.append(value.b)
    def __len__(self):
        return len(self.a)
    def __iter__(self):
        return BHA_Iterator(self[i] for i in itertools.count(0) if i < len(self))