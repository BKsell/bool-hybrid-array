import sys
from ctypes import *
import ctypes
import numpy as np
from typing import Any, Union, Callable, Optional, TextIO, BinaryIO
import mmap
import os

ios_base_goodbit = 0
ios_base_badbit = 1 << 0
ios_base_eofbit = 1 << 1
ios_base_failbit = 1 << 2

ios_dec = 1 << 0
ios_oct = 1 << 1
ios_hex = 1 << 2
ios_basefield = ios_dec | ios_oct | ios_hex

ios_left = 1 << 3
ios_right = 1 << 4
ios_internal = 1 << 5
ios_adjustfield = ios_left | ios_right | ios_internal

ios_scientific = 1 << 6
ios_fixed = 1 << 7
ios_floatfield = ios_scientific | ios_fixed

ios_boolalpha = 1 << 8
ios_showbase = 1 << 9
ios_showpoint = 1 << 10
ios_uppercase = 1 << 11
ios_showpos = 1 << 12

ios_in = 1 << 13
ios_out = 1 << 14
ios_ate = 1 << 15
ios_app = 1 << 16
ios_trunc = 1 << 17
ios_binary = 1 << 18

class Manipulator:
    def __init__(self, func: Callable):
        self.func = func

    def apply(self, stream):
        self.func(stream)

def endl_manip(s):
    s << "\r\n"
    s.flush()

def flush_manip(s):
    s.flush()

def boolalpha_manip(s):
    s.format_flags |= ios_boolalpha

def noboolalpha_manip(s):
    s.format_flags &= ~ios_boolalpha

def showbase_manip(s):
    s.format_flags |= ios_showbase

def noshowbase_manip(s):
    s.format_flags &= ~ios_showbase

def showpoint_manip(s):
    s.format_flags |= ios_showpoint

def noshowpoint_manip(s):
    s.format_flags &= ~ios_showpoint

def uppercase_manip(s):
    s.format_flags |= ios_uppercase

def nouppercase_manip(s):
    s.format_flags &= ~ios_uppercase

def showpos_manip(s):
    s.format_flags |= ios_showpos

def noshowpos_manip(s):
    s.format_flags &= ~ios_showpos

def fixed_manip(s):
    s.format_flags = (s.format_flags & ~ios_floatfield) | ios_fixed

def scientific_manip(s):
    s.format_flags = (s.format_flags & ~ios_floatfield) | ios_scientific

def left_manip(s):
    s.format_flags = (s.format_flags & ~ios_adjustfield) | ios_left

def right_manip(s):
    s.format_flags = (s.format_flags & ~ios_adjustfield) | ios_right

def internal_manip(s):
    s.format_flags = (s.format_flags & ~ios_adjustfield) | ios_internal

def setw(width: int) -> Manipulator:
    def impl(s):
        s.temp_width = width
    return Manipulator(impl)

def setprecision(prec: int) -> Manipulator:
    def impl(s):
        s.precision = prec
    return Manipulator(impl)

def setfill(ch: str) -> Manipulator:
    def impl(s):
        s.fill_char = ch[0] if ch else ' '
    return Manipulator(impl)

def ignore(n: int = 1, delim: int = -1) -> Manipulator:
    def impl(s):
        s.ignore(n, delim)
    return Manipulator(impl)

endl = Manipulator(endl_manip)
flush = Manipulator(flush_manip)
boolalpha = Manipulator(boolalpha_manip)
noboolalpha = Manipulator(noboolalpha_manip)
showbase = Manipulator(showbase_manip)
noshowbase = Manipulator(noshowbase_manip)
showpoint = Manipulator(showpoint_manip)
noshowpoint = Manipulator(noshowpoint_manip)
uppercase = Manipulator(uppercase_manip)
nouppercase = Manipulator(nouppercase_manip)
showpos = Manipulator(showpos_manip)
noshowpos = Manipulator(noshowpos_manip)
fixed = Manipulator(fixed_manip)
scientific = Manipulator(scientific_manip)
left = Manipulator(left_manip)
right = Manipulator(right_manip)
internal = Manipulator(internal_manip)

class istream:
    def __init__(self):
        self._stdout = sys.stdout
        self.backch = " \b"
        self._buf = []
        self.eofbit = False
        self.failbit = False
        self.badbit = False
        self._whitespace = {ord('\n'), ord('\t'), ord(' '), 0, ord("\r")}
        self.eof = -1
        self.libc = None
        self._get_char = None

        if sys.platform == "win32":
            import msvcrt
            self._get_char = lambda: ord(msvcrt.getche())
            self.eof = 26
        else:
            libc_path = "libc.so.6" if sys.platform == "linux" else "libSystem.B.dylib"
            try:
                self.libc = ctypes.cdll.LoadLibrary(libc_path)
            except:
                self.libc = CDLL("libc.so")
            self.libc.getchar.restype = c_int
            def _getch():
                c = self.libc.getchar()
                if c != -1:
                    self._stdout.write(chr(c))
                    self._stdout.flush()
                return c
            self._get_char = _getch

    def rdstate(self):
        st = ios_base_goodbit
        if self.badbit:
            st |= ios_base_badbit
        if self.eofbit:
            st |= ios_base_eofbit
        if self.failbit:
            st |= ios_base_failbit
        return st

    def good(self):
        return self.rdstate() == ios_base_goodbit

    def eof(self):
        return self.eofbit

    def fail(self):
        return self.failbit or self.badbit

    def bad(self):
        return self.badbit

    def clear(self, state=ios_base_goodbit):
        self.eofbit = bool(state & ios_base_eofbit)
        self.failbit = bool(state & ios_base_failbit)
        self.badbit = bool(state & ios_base_badbit)
        self._buf.clear()

    def setstate(self, state):
        self.clear(self.rdstate() | state)

    def peek(self):
        if not self._buf:
            c = self._get_char()
            self._buf.append(c)
            return c
        return self._buf[0]

    def putback(self, ch):
        self._buf.insert(0, ch)

    def ignore(self, count=1, delim=-1):
        cnt = 0
        while cnt < count and self.good():
            c = self._buf.pop(0) if self._buf else self._get_char()
            if c == self.eof:
                self.setstate(ios_base_eofbit)
                break
            if c == delim and delim != -1:
                break
            cnt += 1

    def _read_char(self):
        while True:
            char = self._buf.pop(0) if self._buf else self._get_char()
            if char in self._whitespace:
                continue
            if char == self.eof:
                self.setstate(ios_base_eofbit)
                return 0
            return char

    def _parse_int(self):
        chars = []
        while True:
            char = self._buf.pop(0) if self._buf else self._get_char()
            if char in self._whitespace or char == self.eof:
                if char == self.eof:
                    self.setstate(ios_base_eofbit)
                break
            if char == 8:
                self._stdout.write(self.backch)
                self._stdout.flush()
                if chars:
                    chars.pop()
                continue
            if chr(char) not in '+-0123456789':
                self._buf.append(char)
                break
            chars.append(chr(char))
        if not chars:
            self.setstate(ios_base_failbit)
            return "0"
        return ''.join(chars)

    def _parse_float(self):
        chars = []
        while True:
            char = self._buf.pop(0) if self._buf else self._get_char()
            if char in self._whitespace or char == self.eof:
                if char == self.eof:
                    self.setstate(ios_base_eofbit)
                break
            if char == 8:
                self._stdout.write(self.backch)
                self._stdout.flush()
                if chars:
                    chars.pop()
                continue
            if chr(char) not in '+-0123456789.eE':
                self._buf.append(char)
                break
            chars.append(chr(char))
        if not chars:
            self.setstate(ios_base_failbit)
            return "0.0"
        return ''.join(chars)

    def _parse_complex(self):
        chars = []
        while True:
            char = self._buf.pop(0) if self._buf else self._get_char()
            if char in self._whitespace or char == self.eof:
                if char == self.eof:
                    self.setstate(ios_base_eofbit)
                break
            if char == 8:
                self._stdout.write(self.backch)
                self._stdout.flush()
                if chars:
                    chars.pop()
                continue
            if chr(char) not in '+-0123456789.eEj':
                self._buf.append(char)
                break
            chars.append(chr(char))
        if not chars:
            self.setstate(ios_base_failbit)
            return "0+0j"
        return ''.join(chars)

    def _parse_char(self):
        c = self._read_char()
        return chr(c) if c else '\0'

    def _parse_char_array(self, max_len=1024):
        chars = []
        count = 0
        while count < max_len - 1:
            char = self._buf.pop(0) if self._buf else self._get_char()
            if char == 8:
                self._stdout.write(self.backch)
                self._stdout.flush()
                if chars:
                    chars.pop()
                continue
            if char in self._whitespace or char == self.eof:
                if char == self.eof:
                    self.setstate(ios_base_eofbit)
                break
            chars.append(chr(char))
            count += 1
        return ''.join(chars)

    def _parse_ptr(self):
        chars = []
        while True:
            char = self._buf.pop(0) if self._buf else self._get_char()
            if char in self._whitespace or char == self.eof:
                if char == self.eof:
                    self.setstate(ios_base_eofbit)
                break
            if char == 8:
                self._stdout.write(self.backch)
                self._stdout.flush()
                if chars:
                    chars.pop()
                continue
            if chr(char) not in '0123456789abcdefABCDEFx':
                self._buf.append(char)
                break
            chars.append(chr(char))
        if not chars:
            self.setstate(ios_base_failbit)
            return "0"
        return ''.join(chars)

    def getline(self, delim='\n', max_len=4096):
        buf = []
        d_ord = ord(delim)
        for _ in range(max_len - 1):
            c = self._buf.pop(0) if self._buf else self._get_char()
            if c == self.eof:
                self.setstate(ios_base_eofbit)
                break
            if c == d_ord:
                break
            buf.append(chr(c))
        return ''.join(buf)

    def __rshift__(self, target):
        if isinstance(target, Manipulator):
            target.apply(self)
            return self
        if not self.good():
            raise EOFError("Input stream reached EOF/Fail state")

        if isinstance(target, ctypes._SimpleCData):
            t_type = type(target)
            if t_type == c_void_p:
                s = self._parse_ptr()
                if s.startswith(("0x", "0X")):
                    val = c_void_p(int(s, 16))
                else:
                    val = c_void_p(int(s) if s.isdigit() else 0)
            elif t_type == c_char_p:
                s = self._parse_char_array()
                b = s.encode("utf-8")
                val = c_char_p(b)
                memmove(target, val, len(b))
            elif t_type == c_wchar_p:
                s = self._parse_char_array()
                val = c_wchar_p(s)
                memmove(target, val, len(s) * sizeof(c_wchar))
            elif np.issubdtype(np.dtype(t_type), np.integer):
                val = t_type(int(self._parse_int()))
            elif np.issubdtype(np.dtype(t_type), np.floating):
                val = t_type(float(self._parse_float()))
            elif np.issubdtype(np.dtype(t_type), np.complexfloating):
                val = t_type(complex(self._parse_complex()))
            elif t_type == c_char:
                val = c_char(self._parse_char().encode("utf-8")[0])
            elif t_type == c_wchar:
                val = c_wchar(self._parse_char())
            else:
                raise TypeError(f"Unsupported ctypes type: {t_type}")
            if t_type not in (c_char_p, c_wchar_p):
                memmove(byref(target), byref(val), sizeof(target))
        elif isinstance(target, (np.generic, np.ndarray)):
            if isinstance(target, np.generic) or target.ndim == 0:
                if np.issubdtype(target.dtype, np.integer):
                    v = np.array(self._parse_int(), dtype=target.dtype)
                elif np.issubdtype(target.dtype, np.floating):
                    v = np.array(self._parse_float(), dtype=target.dtype)
                elif np.issubdtype(target.dtype, np.complexfloating):
                    v = np.array(self._parse_complex(), dtype=target.dtype)
                elif np.issubdtype(target.dtype, np.character):
                    v = np.array(self._parse_char(), dtype=target.dtype)
                else:
                    v = np.array(self._parse_int(), dtype=target.dtype)
                target[...] = v[()]
            else:
                for idx in range(target.size):
                    flat = target.flat[idx]
                    if np.issubdtype(target.dtype, np.integer):
                        v = np.array(self._parse_int(), dtype=target.dtype)
                    elif np.issubdtype(target.dtype, np.floating):
                        v = np.array(self._parse_float(), dtype=target.dtype)
                    elif np.issubdtype(target.dtype, np.complexfloating):
                        v = np.array(self._parse_complex(), dtype=target.dtype)
                    elif np.issubdtype(target.dtype, np.character):
                        v = np.array(self._parse_char(), dtype=target.dtype)
                    else:
                        v = np.array(self._parse_int(), dtype=target.dtype)
                    flat[...] = v[()]
        elif hasattr(target, '__cin__'):
            target.__cin__()
        elif isinstance(target, int):
            target = int(self._parse_int())
        elif isinstance(target, float):
            target = float(self._parse_float())
        elif isinstance(target, complex):
            target = complex(self._parse_complex())
        elif isinstance(target, str):
            target = self._parse_char_array()
        elif isinstance(target, bool):
            target = bool(int(self._parse_int()))
        else:
            raise TypeError(f"Unsupported input target type: {type(target)}")
        return self

    __bool__ = lambda self: not self.eofbit
    __str__ = lambda self: ""
    __repr__ = lambda self: ""

    def clear_stream(self):
        self._buf.clear()
        self.eofbit = False
        self.failbit = False
        self.badbit = False

class ostream:
    def __init__(self):
        self.k32 = None
        self.h_stdout = c_void_p()
        self.format_flags = ios_dec | ios_right
        self.precision = 6
        self.fill_char = ' '
        self.temp_width = 0
        self.code = "utf-8"
        self.libc = None

        if sys.platform == "win32":
            import msvcrt
            self.libc = msvcrt
            self.k32 = CDLL("kernel32.dll", use_last_error=True)
            self.k32.WriteConsoleW.restype = c_bool
            self.k32.WriteConsoleW.argtypes = [c_void_p, POINTER(c_wchar), c_uint, POINTER(c_uint32), c_void_p]
            self.h_stdout = self.k32.GetStdHandle(-11)
            self.code = "utf-16le"
        else:
            libc_path = "libc.so.6" if sys.platform == "linux" else "libSystem.B.dylib"
            self.libc = CDLL(libc_path)

    def flush(self):
        sys.stdout.flush()

    def _format_num(self, val):
        w = self.temp_width
        self.temp_width = 0
        flags = self.format_flags
        prec = self.precision
        fill = self.fill_char

        if isinstance(val, bool):
            if flags & ios_boolalpha:
                s = "true" if val else "false"
            else:
                s = "1" if val else "0"
        elif isinstance(val, int):
            base = 10
            prefix = ""
            if flags & ios_hex:
                base = 16
                if flags & ios_showbase:
                    prefix = "0X" if flags & ios_uppercase else "0x"
            elif flags & ios_oct:
                base = 8
                if flags & ios_showbase:
                    prefix = "0"
            num_str = str(int(val), base)
            if flags & ios_uppercase:
                num_str = num_str.upper()
            s = prefix + num_str
            if val > 0 and flags & ios_showpos:
                s = "+" + s
        elif isinstance(val, float):
            if flags & ios_fixed:
                fmt = f".{prec}f"
            elif flags & ios_scientific:
                fmt = f".{prec}e"
            else:
                fmt = f".{prec}g"
            s = format(val, fmt)
            if val > 0 and flags & ios_showpos:
                s = "+" + s
            if flags & ios_showpoint and "." not in s:
                s += "."
        else:
            s = str(val)

        if w > 0 and len(s) < w:
            pad = fill * (w - len(s))
            if flags & ios_left:
                s = s + pad
            elif flags & ios_internal and isinstance(val, int) and val < 0:
                s = s[0] + pad + s[1:]
            else:
                s = pad + s
        return s

    def __lshift__(self, data):
        if isinstance(data, Manipulator):
            data.apply(self)
            return self
        text = self._format_num(data)
        buf = text.encode(self.code, errors="replace")
        buf_len = len(buf)
        if self.k32 is not None:
            written = c_uint32()
            char_count = buf_len >> 1
            wbuf = (c_wchar * char_count).from_buffer_copy(buf)
            self.k32.WriteConsoleW(self.h_stdout, wbuf, c_uint(char_count), byref(written), None)
        else:
            self.libc.write(1, buf, buf_len)
        return self

    __str__ = lambda self: ""
    __repr__ = lambda self: ""

class filebuf:
    def __init__(self):
        self._file: Optional[BinaryIO] = None
        self._mmap_obj: Optional[mmap.mmap] = None
        self._binary = False
        self._pos = 0
        self._file_size = 0
        self._write_mode = False
        self._win_mmap_handle = None
        self._win_file_handle = None

    def _unmap(self):
        if sys.platform == "win32":
            if self._win_mmap_handle is not None:
                ctypes.windll.kernel32.CloseHandle(self._win_mmap_handle)
                self._win_mmap_handle = None
            if self._mmap_obj is not None:
                self._mmap_obj.close()
                self._mmap_obj = None
        else:
            if self._mmap_obj is not None:
                self._mmap_obj.flush()
                self._mmap_obj.close()
                self._mmap_obj = None

    def open(self, path: str, mode_mask: int) -> bool:
        if self.is_open():
            self.close()
        py_mode = ""
        self._binary = bool(mode_mask & ios_binary)
        self._write_mode = bool(mode_mask & ios_out)

        if mode_mask & ios_in and mode_mask & ios_out:
            py_mode = "r+b"
        elif mode_mask & ios_out:
            if mode_mask & ios_trunc:
                py_mode = "w+b"
            elif mode_mask & ios_app:
                py_mode = "a+b"
            else:
                py_mode = "r+b"
        elif mode_mask & ios_in:
            py_mode = "rb"
        else:
            py_mode = "rb"

        try:
            self._file = open(path, py_mode)
            self._file.seek(0, os.SEEK_END)
            self._file_size = self._file.tell()
            self._file.seek(0, os.SEEK_SET)
            self._pos = 0

            if mode_mask & ios_ate:
                self._pos = self._file_size

            fd = self._file.fileno()
            access = mmap.ACCESS_WRITE if self._write_mode else mmap.ACCESS_READ

            if sys.platform == "win32":
                import msvcrt
                self._win_file_handle = msvcrt.get_osfhandle(fd)
                map_size = max(self._file_size, 4096) if self._write_mode else self._file_size
                self._win_mmap_handle = ctypes.windll.kernel32.CreateFileMappingW(
                    self._win_file_handle, None,
                    0x04 if self._write_mode else 0x02,
                    map_size >> 32, map_size & 0xFFFFFFFF, None
                )
                if not self._win_mmap_handle:
                    raise OSError("CreateFileMapping failed")
                self._mmap_obj = mmap.mmap(fd, map_size, access=access)
            else:
                map_len = self._file_size if not self._write_mode else 0
                self._mmap_obj = mmap.mmap(fd, map_len, access=access)
            return True
        except OSError:
            self._file = None
            self._unmap()
            return False

    def is_open(self) -> bool:
        return self._file is not None and not self._file.closed and self._mmap_obj is not None

    def close(self) -> bool:
        self._unmap()
        if self._file is not None:
            self._file.close()
            self._file = None
        self._win_file_handle = None
        self._win_mmap_handle = None
        self._pos = 0
        self._file_size = 0
        return True

    def get_char(self):
        if not self.is_open() or self._pos >= self._file_size:
            return -1
        c = self._mmap_obj[self._pos]
        self._pos += 1
        return c

    def put_char(self, ch: int):
        if not self.is_open() or not self._write_mode:
            return False
        if len(self._mmap_obj) == 0:
            self._mmap_obj.resize(4096)
        if self._pos >= len(self._mmap_obj):
            new_size = self._pos + 4096
            self._mmap_obj.resize(new_size)
        self._mmap_obj[self._pos] = ch
        self._pos += 1
        if self._pos > self._file_size:
            self._file_size = self._pos
        return True

    def seekg(self, off: int, whence: int = 0):
        if not self.is_open():
            return -1
        if whence == os.SEEK_SET:
            new_pos = off
        elif whence == os.SEEK_CUR:
            new_pos = self._pos + off
        elif whence == os.SEEK_END:
            new_pos = self._file_size + off
        else:
            return -1
        new_pos = max(0, new_pos)
        self._pos = new_pos
        return self._pos

    def seekp(self, off: int, whence: int = 0):
        return self.seekg(off, whence)

    def tellg(self):
        if not self.is_open():
            return -1
        return self._pos

    def tellp(self):
        return self.tellg()

    def flush(self):
        if self.is_open() and self._write_mode:
            self._mmap_obj.flush()
            self._file.truncate(self._file_size)
            self._file.flush()

class ifstream(istream):
    def __init__(self, path: str = "", mode = None):
        super().__init__()
        self._fb = filebuf()
        self._get_char = self._fb.get_char
        if path:
            if mode is None:
                self.open(path)
            else:
                self.open(path, mode)

    def open(self, path: str, mode = None):
        self.clear()
        if mode is None:
            mask = ios_in
        else:
            mask = mode | ios_in
        if not self._fb.open(path, mask):
            self.setstate(ios_base_failbit)

    def close(self):
        self._fb.close()

    def is_open(self):
        return self._fb.is_open()
    def __del__(self):
        self.close()

    def __enter__(self):
        return self
    def __exit__(self, *args):
        self.close()

class ofstream(ostream):
    def __init__(self, path: str = "", mode = None):
        super().__init__()
        self._fb = filebuf()
        if path:
            if mode is None:
                self.open(path)
            else:
                self.open(path, mode)

    def open(self, path: str, mode = None):
        if mode is None:
            mask = ios_out | ios_trunc
        else:
            mask = mode | ios_out
        if not self._fb.open(path, mask):
            pass

    def close(self):
        self._fb.flush()
        self._fb.close()

    def is_open(self):
        return self._fb.is_open()

    def __lshift__(self, data):
        if isinstance(data, Manipulator):
            data.apply(self)
            return self
        text = self._format_num(data)
        for ch in text:
            self._fb.put_char(ord(ch))
        return self

    def flush(self):
        self._fb.flush()
    def __del__(self):
        self.close()

    def __enter__(self):
        return self
    def __exit__(self, *args):
        self.close()

class fstream(istream, ostream):
    def __init__(self, path: str = "", mode = None):
        istream.__init__(self)
        ostream.__init__(self)
        self._fb = filebuf()
        self._get_char = self._fb.get_char
        if path:
            if mode is None:
                self.open(path)
            else:
                self.open(path, mode)

    def open(self, path: str, mode = None):
        self.clear()
        if mode is None:
            mask = ios_in | ios_out
        else:
            mask = mode
        if not self._fb.open(path, mask):
            self.setstate(ios_base_failbit)

    def close(self):
        self._fb.flush()
        self._fb.close()

    def is_open(self):
        return self._fb.is_open()

    def __lshift__(self, data):
        if isinstance(data, Manipulator):
            data.apply(self)
            return self
        text = self._format_num(data)
        for ch in text:
            self._fb.put_char(ord(ch))
        return self

    def flush(self):
        self._fb.flush()
    def __del__(self):
        self.close()

    def __enter__(self):
        return self
    def __exit__(self, *args):
        self.close()

InPutObject = istream
OutPutObject = ostream
cin = InPutObject()
cout = OutPutObject()