# cython: language_level=3,boundscheck=False,wraparound=False,cdivision=True,nonecheck=False,overflowcheck=False,initializedcheck=False,profile=False,linetrace=False,emit_code_comments=False

import math
import heapq
import unicodedata
from bisect import bisect_right
from collections import Counter



_USEFUL_CTRL : tuple = ('\t', '\n', '\r', '\b', '\x1b', '\f', '\v')
_HALF_ASCII : tuple = tuple(chr(c) for c in range(0x20, 0x7F))
_PUNCT : tuple = ('。', '，', '、', '？', '！', '：', '；', '"', '“', '”',
          '‘', '’', '（', '）', '【', '】', '《', '》', '—', '…',
          '·', '～', '「', '」', '『', '』')

_ALPHA_LOWER : tuple = tuple('etaoinshrdlucmwfgypbvkjxqz')
_ALPHA_UPPER : tuple = tuple('ETAOINSHRDLUCUMWFGYPBVKJXQZ')
_DIGITS : tuple = tuple('1234567890')
_ASCII_SYM : tuple = (',', '.', '?', '!', ';', ':', "'", '"', '-', '_',
              '(', ')', '[', ']', '{', '}', '/', '\\', '@', '#',
              '$', '%', '^', '&', '*', '+', '=', '<', '>', '|',
              '~', '`')
_BASIC : tuple = ((' ',) + _ALPHA_LOWER + _ALPHA_UPPER + _DIGITS
          + _ASCII_SYM + _USEFUL_CTRL + _PUNCT)


def _gb2312_hanzi():
    for b1 in range(0xB0, 0xF8):
        for b2 in range(0xA1, 0x100):
            try:
                ch:str = bytes([b1, b2]).decode('gb2312')
                if len(ch) == 1 and unicodedata.category(ch) == 'Lo':
                    yield ch
            except Exception:
                pass


def _gbk_ext_hanzi(seen: set):
    for b1 in range(0x81, 0x100):
        for b2 in range(0x40, 0x100):
            if b2 == 0x7F:
                continue
            try:
                ch:str = bytes([b1, b2]).decode('gbk')
                if (len(ch) == 1 and unicodedata.category(ch) == 'Lo'
                        and ch not in seen):
                    yield ch
            except Exception:
                pass


def _gbk_syms(seen: set):
    for b1 in range(0xA1, 0xAA):
        for b2 in range(0xA1, 0x100):
            try:
                ch = bytes([b1, b2]).decode('gbk')
                if ch not in seen and unicodedata.category(ch) != 'Cc':
                    yield ch
            except Exception:
                pass


def _is_private(cp:int) :
    if 0xE000 <= cp <= 0xF8FF:
        return True                      # BMP 私有区
    if 0xF0000 <= cp <= 0xFFFFD:
        return True                      # 平面15 私有区
    if 0x100000 <= cp <= 0x10FFFD:
        return True                      # 平面16 私有区
    return False


def _fill_unicode(out: list, seen: set, target: int) :
    for cp in range(0, 0x110000):
        try:
            if 0xD800 <= cp <= 0xDFFF:
                continue                  # 代理区
            if _is_private(cp):
                continue                  # 私有区
            ch = chr(cp)
            if ch in seen:
                continue
            cat = unicodedata.category(ch)
            if cat == 'Cc' and ch not in _USEFUL_CTRL:
                continue                  # 无用控制字符（\0、DEL 等）
            seen.add(ch)
            out.append(ch)
            if len(out) >= target:
                return
        except Exception:
            pass


def _build_charlist(target:int):
    out = []
    seen = set()

    def add(ch:str):
        if ch not in seen:
            seen.add(ch)
            out.append(ch)

    for ch in _BASIC:
        add(ch)                     # 128
    for ch in _gb2312_hanzi():
        add(ch)                     # +6763 = 6891
    for ch in _gbk_ext_hanzi(seen):
        add(ch)                     # +14139 = 21030
    for ch in _gbk_syms(seen):
        add(ch)                     # +889 = 21919
    _fill_unicode(out, seen, target)
    return out


CHARLIST : list = _build_charlist(0x110000)

CHAR_TO_CODE = {}
for _i, _c in enumerate(CHARLIST):
    CHAR_TO_CODE[_c] = _i

_N : int = len(CHARLIST)



_WID : tuple = ((0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 6),
        (6, 10), (7, 12), (8, 15), (9, 20))

_MARK_TO_W : dict = {m: w for m, w in _WID}



_W : tuple = (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 20)

_STARTS : dict = {}
_cum:int = 0
for _w in _W:
    _STARTS[_w] = _cum
    _cum += (1 << _w)


def _bucket_w(idx:int) :
    for w in _W:
        if idx - _STARTS[w] < (1 << w):
            return w
    return 20



def _read_bits(data: bytes, bitpos: int, width: int):
    v = 0
    for _ in range(width):
        v = (v << 1) | ((data[bitpos >> 3] >> (7 - (bitpos & 7))) & 1)
        bitpos += 1
    return v, bitpos



def _tans_build(counts: dict, m: int, tl: int):
    L = 1 << tl
    total = sum(counts.values())
    freqs = [0] * m
    rem = []
    for s in range(m):
        c = counts.get(s, 0)
        f = (c * L) // total
        freqs[s] = f if f >= 1 else 1
        rem.append(((c * L) % total, f, s))
    diff = L - sum(freqs)
    if diff > 0:
        for _, f, s in sorted(rem, key=lambda x: x[0], reverse=True):
            if diff <= 0:
                break
            if f:
                freqs[s] += 1
                diff -= 1
        if diff > 0:
            big = max(range(m), key=freqs.__getitem__)
            freqs[big] += diff
    elif diff < 0:
        need = -diff
        for s in sorted(range(m), key=freqs.__getitem__, reverse=True):
            if need <= 0:
                break
            room = freqs[s] - 1
            cut = room if room < need else need
            freqs[s] -= cut
            need -= cut
    cums = [0] * m
    acc = 0
    for s in range(m):
        cums[s] = acc
        acc += freqs[s]
    return freqs, cums


def _pick_tl(counts: dict, m: int, total: int):
    base = (m - 1).bit_length() + (3 if m <= 128 else 2 if m <= 512 else 1)
    if base < 9:
        base = 9
    need = (m - 1).bit_length()
    if base < need:
        base = need
    best_tl = base
    best = None
    for k in range(6):
        tl = base + k
        freqs, _ = _tans_build(counts, m, tl)
        bits = 136
        for s in range(m):
            f = freqs[s]
            bits += (f.bit_length() * 2) - 1
            c = counts.get(s, 0)
            if c:
                bits += c * (tl - (f.bit_length() - 1))
        if best is None or bits < best:
            best = bits
            best_tl = tl
    return best_tl


def _fix_lens(freqs: list):
    m = len(freqs)
    if m == 1:
        return [1]
    nodes = [[0, -1, -1] for _ in range(m)]
    heap = []
    for s in range(m):
        f = freqs[s]
        nodes[s][0] = f if f > 0 else 1
        heap.append((nodes[s][0], s, s))
    heapq.heapify(heap)
    tie = m
    while len(heap) > 1:
        f1, _, n1 = heapq.heappop(heap)
        f2, _, n2 = heapq.heappop(heap)
        nodes.append([f1 + f2, n1, n2])
        heapq.heappush(heap, (f1 + f2, tie, len(nodes) - 1))
        tie += 1
    root = heap[0][2]
    lens = [0] * m
    stack = [(root, 0)]
    while stack:
        nd, d = stack.pop()
        l, r = nodes[nd][1], nodes[nd][2]
        if l == -1:
            lens[nd] = d if d > 0 else 1
        else:
            stack.append((l, d + 1))
            stack.append((r, d + 1))
    return lens


def _canon_codes(lens: list):
    m = len(lens)
    maxlen = max(lens)
    count = [0] * (maxlen + 1)
    for s in range(m):
        count[lens[s]] += 1
    pbase = [0] * (maxlen + 1)
    code = 0
    for l in range(1, maxlen + 1):
        pbase[l] = code
        code = (code + count[l]) << 1
    porder = [[] for _ in range(maxlen + 1)]
    canon = [0] * m
    for s in sorted(range(m), key=lambda s: (lens[s], s)):
        l = lens[s]
        canon[s] = pbase[l] + len(porder[l])
        porder[l].append(s)
    return canon, maxlen, pbase, porder


def _fixed_encode(seqs: list, lens: list, canon: list):
    bw = _BitWriter()
    nbits:int = 0
    for s in seqs:
        w = lens[s]
        bw.write(canon[s], w)
        nbits += w
    data, _ = bw.get_bitstream()
    return data, nbits


def _fixed_decode(data: bytes, lens: list, maxlen: int, pbase: list, porder: list, n: int):
    out = []
    pos = 0
    for _ in range(n):
        c = 0
        for length in range(1, maxlen + 1):
            c = (c << 1) | ((data[pos >> 3] >> (7 - (pos & 7))) & 1)
            pos += 1
            lst = porder[length]
            k = c - pbase[length]
            if lst and 0 <= k < len(lst):
                out.append(lst[k])
                break
    return out


class _BitWriter:
    __slots__ = ('buf', 'cur', 'curb', 'nbit')
    def __init__(self):
        self.buf = bytearray()
        self.cur = 0
        self.curb = 0
        self.nbit = 0
    def write(self, value, width: int):
        self.cur = (self.cur << width) | (value & ((1 << width) - 1))
        self.curb += width
        self.nbit += width
        while self.curb >= 8:
            self.buf.append((self.cur >> (self.curb - 8)) & 255)
            self.curb -= 8
        if self.curb:
            self.cur &= (1 << self.curb) - 1
    def finish(self) -> bytes:
        if self.curb:
            self.buf.append((self.cur << (8 - self.curb)) & 255)
        return bytes(self.buf)
    def get_bitstream(self):
        data = bytes(self.buf)
        if self.curb:
            data += bytes([(self.cur << (8 - self.curb)) & 255])
            return data, len(data) * 8 - (8 - self.curb)
        return data, len(data) * 8


class _BitReader:
    def __init__(self, data: bytes):
        self.data = data
        self.pos = 0
        self.nbit = 0
        self.cur = 0
    def read(self, width: int) -> int:
        while self.nbit < width:
            self.cur = (self.cur << 8) | self.data[self.pos]
            self.pos += 1
            self.nbit += 8
        self.nbit -= width
        return (self.cur >> self.nbit) & ((1 << width) - 1)


_LZ4_WINDOW:int = 65536             # LZ4 匹配窗口（字节数）
_LZ4_MIN:int = 4                    # LZ4 最小匹配长度


def _write_len(bw: _BitWriter, v: int):
    if v < 15:
        bw.write(v, 4)
    else:
        bw.write(15, 4)
        extra = v - 15
        while extra >= 255:
            bw.write(255, 8)
            extra -= 255
        bw.write(extra, 8)


def _read_len(br: _BitReader) :
    v = br.read(4)
    if v == 15:
        while True:
            b = br.read(8)
            v += b
            if b != 255:
                break
    return v


def _lz4_seq_bits(bw: _BitWriter, bits: int, total: int, lit_start: int, lit_end: int, offset: int, mlen: int):
    litlen = lit_end - lit_start
    has = mlen >= _LZ4_MIN
    bw.write(1 if has else 0, 1)
    _write_len(bw, litlen)
    if litlen:
        seg = (bits >> (total - lit_end)) & ((1 << litlen) - 1)
        bw.write(seg, litlen)
    if has:
        bl_off = offset.bit_length()
        bw.write(bl_off - 1, 5)
        bw.write(offset, bl_off)
        _write_len(bw, mlen - _LZ4_MIN)


def _lz4_pack(data: bytes, nbits: int) :
    total:int = nbits
    bits = int.from_bytes(data, 'big') >> (len(data) * 8 - total)
    bw = _BitWriter()
    bw.write(total, 32)
    htab = {}
    K = 32
    MASK = (1 << K) - 1
    i:int = 0
    lit_start:int = 0
    key = 0
    for k in range(min(K, total)):
        key = (key << 1) | ((data[k >> 3] >> (7 - (k & 7))) & 1)
    while i < total:
        best_len = 0
        best_off = 0
        if i + K <= total:
            lst = htab.get(key)
            if lst is not None:
                bpos = bits & ((1 << (total - i)) - 1)
                for pos in lst:
                    if i - pos > _LZ4_WINDOW:
                        continue
                    d = (bits & ((1 << (total - pos)) - 1)) ^ (bpos << (i - pos))
                    if d == 0:
                        ln = total - i
                    else:
                        ln = (total - pos) - d.bit_length()
                        if ln > total - i:
                            ln = total - i
                    if ln > best_len:
                        best_len = ln
                        best_off = i - pos
        if best_len >= _LZ4_MIN:
            _lz4_seq_bits(bw, bits, total, lit_start, i, best_off, best_len)
            for j in range(i, i + best_len):
                if j + K <= total:
                    lst = htab.get(key)
                    if lst is None:
                        htab[key] = [j]
                    else:
                        while lst and j - lst[0] > _LZ4_WINDOW:
                            lst.pop(0)
                        if len(lst) >= 128:
                            lst.pop(0)
                        lst.append(j)
                if j + K < total:
                    key = ((key << 1) | ((data[(j + K) >> 3] >> (7 - ((j + K) & 7))) & 1)) & MASK
            i += best_len
            lit_start = i
        else:
            if i + K <= total:
                lst = htab.get(key)
                if lst is None:
                    htab[key] = [i]
                else:
                    while lst and i - lst[0] > _LZ4_WINDOW:
                        lst.pop(0)
                    if len(lst) >= 128:
                        lst.pop(0)
                    lst.append(i)
                i += 1
                if i + K <= total:
                    key = ((key << 1) | ((data[(i + K - 1) >> 3] >> (7 - ((i + K - 1) & 7))) & 1)) & MASK
            else:
                i += 1
    if lit_start < total:
        _lz4_seq_bits(bw, bits, total, lit_start, total, 0, 0)
    else:
        bw.write(0, 1)
        bw.write(0, 4)
    return bw.finish()


def _lz4_unpack(data: bytes) :
    br = _BitReader(data)
    total = br.read(32)
    out = bytearray()
    res = bytearray()
    cur = 0
    cb = 0
    while len(out) < total:
        has = br.read(1)
        litlen = _read_len(br)
        if litlen:
            v = br.read(litlen)
            for k in range(litlen):
                b = (v >> (litlen - 1 - k)) & 1
                out.append(b)
                cur = (cur << 1) | b
                cb += 1
                if cb == 8:
                    res.append(cur)
                    cur = 0
                    cb = 0
        if not has:
            break
        bl_off = br.read(5) + 1
        offset = br.read(bl_off)
        ml = _read_len(br) + _LZ4_MIN
        if offset >= ml:
            lo = len(out) - offset
            seg = out[lo:lo + ml]
        else:
            base = out[-offset:]
            seg = bytearray(base)
            while len(seg) < ml:
                seg += base[:ml - len(seg)]
        for b in seg:
            out.append(b)
            cur = (cur << 1) | b
            cb += 1
            if cb == 8:
                res.append(cur)
                cur = 0
                cb = 0
    if cb:
        res.append(cur << (8 - cb))
    return bytes(res)


def encode(text:str) :
    if not text:
        return b''
    codes = []
    for ch in text:
        code = CHAR_TO_CODE.get(ch)
        if code is None:
            raise ValueError('字符 U+%04X 不在 CJX 字符集' % ord(ch)) from None
        codes.append(code)
    freq = Counter(codes)
    appeared = sorted(freq)                  # 出现过的 index，升序 = 全局统一序号
    m = len(appeared)
    seqmap = {c: k for k, c in enumerate(appeared)}
    freq_seq = {seqmap[c]: v for c, v in freq.items()}
    seqs = [seqmap[c] for c in codes]
    if m <= 256:
        tl = 0
        freqs = []
        lens = _fix_lens([freq_seq.get(s, 0) for s in range(m)])
    else:
        tl = _pick_tl(freq_seq, m, len(seqs))
        freqs, cums = _tans_build(freq_seq, m, tl)
        lens = _fix_lens(freqs)
    canon, maxlen, pbase, porder = _canon_codes(lens)
    ans_data, ans_nbits = _fixed_encode(seqs, lens, canon)   # 正文：每符号固定码字（同符号任何位置比特一致）
    x0 = 0

    def write_head(bw):
        bw.write(len(text), 32)              # 头部：原文本字符数
        buckets = {w: [] for w in _W}
        for v in appeared:
            buckets[_bucket_w(v)].append(v)
        for w in _W:                         # 字典（桶表，分档法存储，固定 16 段）
            lst = buckets[w]
            bw.write(len(lst), 20)           # 每档 [20bit 长度] + 值序列位平面（w 个平面，每平面 len 位）
            st = _STARTS[w]
            bit = 0
            while bit < w:
                for v in lst:
                    bw.write((v - st) >> bit & 1, 1)
                bit += 1
        if tl:
            bw.write(tl, 8)                  # ANS 表：tableLog + 终止状态 + 位流长度 + 归一化频率
            bw.write(x0, 32)
            bw.write(ans_nbits, 32)
            for s in range(m):
                f = freqs[s]
                k = f.bit_length()
                bw.write(0, k - 1)
                bw.write(1, 1)
                bw.write(f - (1 << (k - 1)), k - 1)
        else:
            bw.write(maxlen | 128, 8)        # 码长表：最大码长 + 每符号码长
            bw.write(x0, 32)
            bw.write(ans_nbits, 32)
            lw = maxlen.bit_length()
            for s in range(m):
                bw.write(lens[s], lw)

    head = _BitWriter()
    write_head(head)
    head_bits = head.nbit                    # 头部数据 bit 数（不含流头 N）
    bw = _BitWriter()
    bw.write(head_bits, 32)                  # 流头：头部数据 bit 数（不含流头本身）
    write_head(bw)
    data, nbits = bw.get_bitstream()
    inner = data + ans_data
    return _lz4_pack(inner, len(inner) * 8)   # 位粒度 LZ4（窗口/匹配/字面量均按 bit）



def decode(data:bytes) :
    if not data:
        return ''
    inner = _lz4_unpack(data)                # 外层 LZ4 解压，还原原流程字节流
    bitpos = 0
    head_bits, bitpos = _read_bits(inner, bitpos, 32)   # 流头：头部数据 bit 数（不含流头本身）
    orig_len, bitpos = _read_bits(inner, bitpos, 32)   # 原文本字符数
    appeared = []                                     # 重建字典：全部出现 index
    for w in _W:
        cnt, bitpos = _read_bits(inner, bitpos, 20)
        st = _STARTS[w]
        offs = [0] * cnt
        bit = 0
        while bit < w:
            i = 0
            while i < cnt:
                b, bitpos = _read_bits(inner, bitpos, 1)
                offs[i] |= b << bit
                i += 1
            bit += 1
        for off in offs:
            appeared.append(st + off)
    appeared.sort()
    m = len(appeared)
    tag, bitpos = _read_bits(inner, bitpos, 8)
    x0, bitpos = _read_bits(inner, bitpos, 32)
    ans_nbits, bitpos = _read_bits(inner, bitpos, 32)
    if tag & 128:
        maxlen = tag & 127
        lw = maxlen.bit_length()
        lens = [0] * m
        for s in range(m):
            lens[s], bitpos = _read_bits(inner, bitpos, lw)
        if max(lens) != maxlen:
            raise ValueError('CJX 码长表校验失败')
    else:
        tl = tag
        freqs = [0] * m
        for s in range(m):
            k = 1
            b, bitpos = _read_bits(inner, bitpos, 1)
            while not b:
                k += 1
                b, bitpos = _read_bits(inner, bitpos, 1)
            tail, bitpos = _read_bits(inner, bitpos, k - 1)
            freqs[s] = (1 << (k - 1)) | tail
        if sum(freqs) != (1 << tl):
            raise ValueError('CJX 频率表校验失败')
        lens = _fix_lens(freqs)
    canon, maxlen, pbase, porder = _canon_codes(lens)
    ans_data = inner[(bitpos + 7) >> 3:]
    seqs = _fixed_decode(ans_data, lens, maxlen, pbase, porder, orig_len)   # 正文：逐符号固定码字解码
    codes = [appeared[s] for s in seqs]
    return ''.join(CHARLIST[i] for i in codes)



def stats():
    segs = {}
    for w in _W:
        st = _STARTS[w]
        segs[str(w)] = max(0, min(_N, st + (1 << w)) - min(_N, st))
    segs['total'] = _N
    return segs


if __name__ == '__main__':
    import unicodedata
    s = stats()
    print('CJX 字符集统计（单文件自生成，%d 码位）:' % s['total'])
    print('  Unicode 数据版本: %s' % unicodedata.unidata_version)
    for k in _W:
        print('  %sbit 档容量 : %d' % (k, s[str(k)]))
