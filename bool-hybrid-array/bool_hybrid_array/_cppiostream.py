import sys
from ctypes import *
import ctypes
import numpy as np
try:
    import msvcrt
except:
    pass
class InPutObject:
    def __init__(self):
        self._stdout = sys.stdout
        self.backch = " \b"
        if sys.platform == "win32":
            self._get_char = lambda: ord(msvcrt.getche())
            self.eof = 26
        else:
            libc_path = "libc.so.6" if sys.platform == "linux" else "libSystem.B.dylib"
            try:self.libc = ctypes.cdll.LoadLibrary(libc_path)
            except:self.libc= ctypes.CDLL("libc.so")
            self._get_char = lambda:(c:=self.libc.getchar(),
                self._stdout.write(chr(c) if c != -1 else '\0'),self._stdout.flush())[0]
            self.eof = -1
        self._whitespace = {ord('\n'), ord('\t'), ord(' '), 0, ord("\r")}
        self.getchar = self._get_char
        self._buf = []
        self.eofbit = False
    
    def _read_char(self):
        while True:
            if self._buf:char = self._buf.pop(0)
            else:char = self._get_char()
            if char in self._whitespace:
                continue
            if char == self.eof:
                self.eofbit = True
                return 0
            return char

    def _parse_int(self):
        chars = []
        while True:
            if self._buf:
                char = self._buf.pop(0)
            else:
                char = self._get_char()
            if char in self._whitespace or char==self.eof:
                self.eofbit = char==self.eof
                break
            if char == 8:
                sys.stdout.write(self.backch)
                sys.stdout.flush()
                try:
                    chars.pop()
                except:
                    pass
                continue
            elif chr(char) not in '+-0123456789':
                self._buf.append(char)
                break
            else:
                chars.append(chr(char))
        return ''.join(chars) if chars else '0'

    def _parse_float(self):
        chars = []
        while True:
            if self._buf:
                char = self._buf.pop(0)
            else:
                char = self._get_char()
            if char in self._whitespace or char == self.eof:
                self.eofbit = char==self.eof
                break
            if char == 8:
                sys.stdout.write(self.backch)
                sys.stdout.flush()
                try:
                    chars.pop()
                except:
                    pass
                continue
            elif chr(char) not in '+-0123456789.eE':
                self._buf.append(char)
                break
            chars.append(chr(char))
        return ''.join(chars) if chars else '0.0'

    def _parse_complex(self):
        chars = []
        while True:
            if self._buf:
                char = self._buf.pop(0)
            else:
                char = self._get_char()
            if char in self._whitespace or char == self.eof:
                self.eofbit = char==self.eof
                break
            if char == 8:
                sys.stdout.write(self.backch)
                sys.stdout.flush()
                try:
                    chars.pop()
                except:
                    pass
                continue
            if chr(char) not in '+-0123456789.eEj':
                self._buf.append(char)
                break
            chars.append(chr(char))
        return ''.join(chars) if chars else '0+0j'

    def _parse_char(self):
        char = self._read_char()
        return chr(char) if char not in self._whitespace else '\0'

    def _parse_char_array(self, max_len=1024):
        chars = []
        count = 0
        while count < max_len - 1:
            if self._buf:char = self._buf.pop(0)
            else:char = self._get_char()
            if char == 8:
                sys.stdout.write(self.backch)
                sys.stdout.flush()
                try:
                    chars.pop()
                except:
                    pass
                continue
            if char in self._whitespace or char == self.eof:
                self.eofbit = char==self.eof
                break
            chars.append(chr(char))
            count += 1
        return ''.join(chars)
    def _parse_ptr(self):
        chars = []
        while True:
            if self._buf:
                char = self._buf.pop(0)
            else:
                char = self._get_char()
            if char in self._whitespace or char == self.eof:
                self.eofbit = char==self.eof
                break
            if char == 8:
                sys.stdout.write(self.backch)
                sys.stdout.flush()
                try:
                    chars.pop()
                except:
                    pass
                continue
            if chr(char) not in '0123456789abcdefABCDEFx':
                self._buf.append(char)
                break
            chars.append(chr(char))
        return ''.join(chars) if chars else '0'
    def __rshift__(self, target):
        if self.eofbit:
            raise EOFError("Input stream reached EOF while parsing integer")
        if isinstance(target, ctypes._SimpleCData):
            target_type = type(target)
            if target_type == c_void_p:
                ptr_str = self._parse_ptr()
                if ptr_str.startswith('0x') or ptr_str.startswith('0X'):
                    val = c_void_p(int(ptr_str, 16))
                else:
                    val = c_void_p(int(ptr_str) if ptr_str.isdigit() else 0)
            elif target_type == c_char_p:
                str_val = self._parse_char_array()
                val = c_char_p(str_val.encode('utf-8'))
                ctypes.memmove(target, val, len(str_val.encode('utf-8')))
            elif target_type == c_wchar_p:
                str_val = self._parse_char_array()
                val = c_wchar_p(str_val)
                ctypes.memmove(target, val, len(str_val) * ctypes.sizeof(c_wchar))
            elif np.issubdtype(np.dtype(target_type), np.integer):
                val = target_type(int(self._parse_int()))
            elif np.issubdtype(np.dtype(target_type), np.floating):
                val = target_type(float(self._parse_float()))
            elif np.issubdtype(np.dtype(target_type), np.complexfloating):
                val = target_type(complex(self._parse_complex()))
            elif target_type == c_char:
                val = c_char(self._parse_char().encode('utf-8')[0])
            elif target_type == c_wchar:
                val = c_wchar(self._parse_char())
            else:
                raise TypeError(f"Unsupported ctypes type: {target_type}")
            if target_type not in (c_char_p, c_wchar_p):
                ctypes.memmove(byref(target), byref(val), sizeof(target))
        elif isinstance(target, (np.generic, np.ndarray)):
            if isinstance(target, np.generic) or target.ndim == 0:
                if np.issubdtype(target.dtype, np.integer):
                    val = np.array(self._parse_int(), dtype=target.dtype)
                elif np.issubdtype(target.dtype, np.floating):
                    val = np.array(self._parse_float(), dtype=target.dtype)
                elif np.issubdtype(target.dtype, np.complexfloating):
                    val = np.array(self._parse_complex(), dtype=target.dtype)
                elif np.issubdtype(target.dtype, np.character):
                    val = np.array(self._parse_char(), dtype=target.dtype)
                else:
                    val = np.array(self._parse_int(), dtype=target.dtype)
                target[...] = val[()]
            else:
                for i in range(target.size):
                    if np.issubdtype(target.dtype, np.integer):
                        val = np.array(self._parse_int(), dtype=target.dtype)
                    elif np.issubdtype(target.dtype, np.floating):
                        val = np.array(self._parse_float(), dtype=target.dtype)
                    elif np.issubdtype(target.dtype, np.complexfloating):
                        val = np.array(self._parse_complex(), dtype=target.dtype)
                    elif np.issubdtype(target.dtype, np.character):
                        val = np.array(self._parse_char(), dtype=target.dtype)
                    else:
                        val = np.array(self._parse_int(), dtype=target.dtype)
                    target.flat[i] = val[()]
        else:
            raise TypeError(f"Unsupported target type: {type(target)}")
        return self
    __str__ = lambda self:""
    __repr__ = lambda self:""
    __bool__ = lambda self:not self._buf or self.eofbit
    def clear(self):
        self._buf.clear()
        self.eofbit = False
class OutPutObject:
    def __lshift__(self, data):
        sys.stdout.write(str(data))
        return self
    __str__ = lambda self:""
    __repr__ = lambda self:""
cin = InPutObject()
cout = OutPutObject()
endl = "\r\n"
