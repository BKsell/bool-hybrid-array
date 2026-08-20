# cython: auto_super=True
from __future__ import annotations
from collections.abc import Sequence
from ..int_array import IntHybridArray
from .. import BoolHybridArr
from ..core import BHA_Iterator
import operator,math,itertools
class BHA_Float(float):
    def __new__(cls, data: int | str | float | BHA_Float | tuple):
        self = super().__new__(cls)
        if isinstance(data, tuple):
            if len(data) == 4:
                self.a,self.b,self.length,self.sign = data
            else:
                self.a,self.b,self.length = data
                self.sign = self.a < 0
                if self.sign:
                    self.a = -self.a
            return self
        if isinstance(data, BHA_Float):
            self.a = data.a
            self.b = data.b
            self.length = data.length
            self.sign = data.sign
            return self
        if isinstance(data, int):
            data = float(data)
        if isinstance(data, float):
            data = repr(data)
        neg = data.startswith('-')
        if neg:
            data = data[1:]
        a, b = data.split('.')
        b = b.rstrip('0')
        self.length = len(b) if b else 1
        self.a = int(a) if a else 0
        self.b = int(b) if b else 0
        self.sign = neg
        return self

    def _align_decimal(self, other):
        max_len = max(self.length, other.length)
        self_num = self.a * (10 ** max_len) + self.b * (10 ** (max_len - self.length))
        if self.sign:
            self_num = -self_num
        other_num = other.a * (10 ** max_len) + other.b * (10 ** (max_len - other.length))
        if other.sign:
            other_num = -other_num
        return self_num, other_num, max_len

    def __add__(self, other):
        other = BHA_Float(other)
        self_num, other_num, max_len = self._align_decimal(other)
        sum_num = self_num + other_num
        if sum_num < 0:
            sign = '-'
            sum_num = -sum_num
        else:
            sign = ''
        string = repr(sum_num)
        integer_part = string[:-max_len] if len(string) > max_len else '0'
        decimal_part = string[-max_len:] if len(string) >= max_len else string.zfill(max_len)
        return BHA_Float(f"{sign}{integer_part}.{decimal_part}")

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
        if self.sign:
            self_num = -self_num
        other_num = other.a * (10 ** other.length) + other.b
        if other.sign:
            other_num = -other_num
        product = self_num * other_num
        if product < 0:
            sign = '-'
            product = -product
        else:
            sign = ''
        string = repr(product)
        total_decimal = self.length + other.length
        string = string.zfill(total_decimal + 1)
        integer_part = string[:-total_decimal]
        decimal_part = string[-total_decimal:]
        return BHA_Float(f"{sign}{integer_part}.{decimal_part}")
    def __format__(self,length):
        if length == '':return str(self)
        if length == '!r':return repr(self)
        length = int(length[1:].split('f')[0].split('d')[0])
        if length > self.length:return str(self).ljust(length, '0')
        else:return str(round(self,length))
    def __truediv__(self, other, total_decimal = 22):
        other = BHA_Float(other)
        self_num = self.a * (10 ** self.length) + self.b
        if self.sign:
            self_num = -self_num
        other_num = other.a * (10 ** other.length) + other.b
        if other.sign:
            other_num = -other_num
        if other_num == 0:
            raise ZeroDivisionError("Cannot divide by zero")
        scale = total_decimal + other.length - self.length
        div_num = (self_num * (10 ** scale)) // other_num
        if div_num < 0:
            sign = '-'
            div_num = -div_num
        else:
            sign = ''
        string = repr(div_num)
        if len(string) <= total_decimal:
            string = '0' * (total_decimal - len(string) + 1) + string
        integer_part = string[:-total_decimal]
        decimal_part = string[-total_decimal:]
        return BHA_Float(f"{sign}{integer_part}.{decimal_part}")
    def __repr__(self):
        s = f"{self.a}.{str(self.b).zfill(self.length)}"
        return f"BHA_Float(-{s})" if self.sign else f"BHA_Float({s})"
    def __str__(self):
        s = f"{self.a}.{str(self.b).zfill(self.length)}"
        return f"-{s}" if self.sign else s
    __radd__ = __add__
    __rmul__ = __mul__
    __rsub__ = lambda self,other:BHA_Float(other)-self
    __rtruediv__ = lambda self,other:BHA_Float(other)/self
    def __float__(self):
        val = float(f"{self.a}.{str(self.b).zfill(self.length)}")
        return -val if self.sign else val
    def __int__(self):
        return -self.a if self.sign else self.a
    is_integer = lambda self:not self.b
    __bool__ = lambda self:self.a or self.b
    def as_integer_ratio(self) -> tuple[int, int]:
        denominator = 10 ** self.length
        numerator = self.a * denominator + self.b
        if self.sign:
            numerator = -numerator
        sign = -1 if numerator < 0 else 1
        numerator = abs(numerator)
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
        return BHA_Float((self.a, self.b, self.length, not self.sign))
    def __pos__(self):
        return self
    def __abs__(self):
        return BHA_Float((self.a, self.b, self.length, False))
    def __lt__(self,other):
        a, b, _ = self._align_decimal(other)
        return a<b
    def __gt__(self,other):
        a, b, _ = self._align_decimal(other)
        return a>b
    def __round__(self, n=None):
        tmp = BHA_Float((self.a, self.b, self.length, self.sign))
        if n is None or n == 0:
            tmp.b = 0
            tmp.length = 1
            half = 5 * 10 ** (self.length - 1)
            if self.b >= half:
                tmp.a = self.a + 1
            if tmp.a == 0 and tmp.b == 0:
                tmp.sign = False
            return tmp
        tmp.b = (self.b + 5 * 10 **(self.length - n - 1))//10**(self.length - n)
        tmp.length = n
        if tmp.b >= 10 ** n:
            tmp.a += 1
            tmp.b -= 10 ** n
        if tmp.a == 0 and tmp.b == 0:
            tmp.sign = False
        return tmp
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
        self.signs = BoolHybridArr(map(operator.attrgetter('sign'),data))
    def __getitem__(self,index):
        return self.Type(BHA_Float((self.a[index],self.b[index],self.lengths[index],self.signs[index])))
    def __setitem__(self,index,value):
        value = BHA_Float(value)
        self.lengths[index] = value.length
        self.a[index] = value.a
        self.b[index] = value.b
        self.signs[index] = value.sign
    def append(self,value):
        value = BHA_Float(value)
        self.lengths.append(value.length)
        self.a.append(value.a)
        self.b.append(value.b)
        self.signs.append(value.sign)
    def __len__(self):
        return len(self.a)
    def __iter__(self):
        return BHA_Iterator(value for value in itertools.takewhile(lambda x: x < len(self), itertools.count(0)))
