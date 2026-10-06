# cython: language_level=3,boundscheck=False,wraparound=False,cdivision=True,nonecheck=False,overflowcheck=False,initializedcheck=False,infer_types=True,annotation_typing=True,profile=False,linetrace=False,emit_code_comments=False,c_api_binop_methods=True

import math
from functools import cmp_to_key
from .core import BoolHybridArr, FalsesArray

_SMALL_MERGE_CAP = 512
_MIN_BLOCK = 16


def _le(x, y, key):
    return key(x) <= key(y) if key else x <= y


def _lt(x, y, key):
    return key(x) < key(y) if key else x < y


def _bisect_left(arr, x, lo, hi, key=None):
    if key is None:
        while lo < hi:
            mid = (lo + hi) >> 1
            if arr[mid] < x:
                lo = mid + 1
            else:
                hi = mid
        return lo
    kx = key(x)
    while hi - lo > 4:
        if not (key(arr[lo]) < kx):
            return lo
        if key(arr[hi - 1]) < kx:
            return hi
        mid = (lo + hi) >> 1
        if key(arr[mid]) < kx:
            lo = mid + 1
        else:
            hi = mid
    while lo < hi and key(arr[lo]) < kx:
        lo += 1
    return lo


def _bisect_right(arr, x, lo, hi, key=None):
    if key is None:
        while lo < hi:
            mid = (lo + hi) >> 1
            if x < arr[mid]:
                hi = mid
            else:
                lo = mid + 1
        return lo
    kx = key(x)
    while hi - lo > 4:
        if kx < key(arr[lo]):
            return lo
        if not (kx < key(arr[hi - 1])):
            return hi
        mid = (lo + hi) >> 1
        if kx < key(arr[mid]):
            hi = mid
        else:
            lo = mid + 1
    while lo < hi and not (kx < key(arr[lo])):
        lo += 1
    return lo


def _reverse(arr, l, r):
    r -= 1
    sw = getattr(arr, 'swap', None)
    if sw is not None:
        while l < r:
            sw(l, r)
            l += 1
            r -= 1
        return
    while l < r:
        arr[l], arr[r] = arr[r], arr[l]
        l += 1
        r -= 1


def _buffer_merge(arr, lo, mid, hi, key=None):
    a_len = mid - lo
    b_len = hi - mid
    if a_len == 0 or b_len == 0:
        return

    if a_len <= b_len:
        buf = arr[lo:mid]
        i = j = 0
        k = lo
        pj = mid
        if key is None:
            while i < a_len and j < b_len:
                if buf[i] <= arr[pj]:
                    arr[k] = buf[i]; i += 1
                else:
                    arr[k] = arr[pj]; pj += 1; j += 1
                k += 1
        else:
            while i < a_len and j < b_len:
                aj = arr[pj]
                if key(buf[i]) <= key(aj):
                    arr[k] = buf[i]; i += 1
                else:
                    arr[k] = aj; pj += 1; j += 1
                k += 1
        if i < a_len:
            arr[k:k + a_len - i] = buf[i:]
    else:
        buf = arr[mid:hi]
        i = a_len - 1
        j = b_len - 1
        k = hi - 1
        pi = lo + i
        if key is None:
            while i >= 0 and j >= 0:
                if arr[pi] <= buf[j]:
                    arr[k] = buf[j]; j -= 1
                else:
                    arr[k] = arr[pi]; pi -= 1; i -= 1
                k -= 1
        else:
            while i >= 0 and j >= 0:
                ai = arr[pi]
                if key(ai) <= key(buf[j]):
                    arr[k] = buf[j]; j -= 1
                else:
                    arr[k] = ai; pi -= 1; i -= 1
                k -= 1
        if j >= 0:
            arr[k - j:k + 1] = buf[:j + 1]


def _insertion_sort(arr, lo, hi, key=None):
    n2 = hi - lo
    if n2 <= 1:
        return
    # 块局部化：拷到小临时数组排完写回——大数组上的 move/swap 每次 O(size) 全量
    # 大整数重组；临时数组只有 n2 个元素，局部移动 O(n2) 便宜得多。
    tmp = arr[lo:hi]
    if key is None:
        for i in range(1, n2):
            kv = tmp[i]
            pos = 0
            hi2 = i
            while pos < hi2:
                mid = (pos + hi2) >> 1
                if kv < tmp[mid]:
                    hi2 = mid
                else:
                    pos = mid + 1
            if pos < i:
                mv = getattr(tmp, 'move', None)
                if mv is not None:
                    mv(pos, i - pos, pos + 1)
                else:
                    tmp[pos + 1:i + 1] = tmp[pos:i]
                    tmp[pos] = kv
    else:
        for i in range(1, n2):
            kv = tmp[i]
            kkv = key(kv)
            pos = 0
            hi2 = i
            while pos < hi2:
                mid = (pos + hi2) >> 1
                if kkv < key(tmp[mid]):
                    hi2 = mid
                else:
                    pos = mid + 1
            if pos < i:
                mv = getattr(tmp, 'move', None)
                if mv is not None:
                    mv(pos, i - pos, pos + 1)
                else:
                    tmp[pos + 1:i + 1] = tmp[pos:i]
                    tmp[pos] = kv
    arr[lo:hi] = tmp


def _block_merge(arr, lo, mid, hi, use_grail=True, key=None):
    lo = _bisect_right(arr, arr[mid], lo, mid, key)
    hi = _bisect_left(arr, arr[mid - 1], mid, hi, key)
    if lo >= mid or mid >= hi:
        return

    n = hi - lo
    a_len = mid - lo
    b_len = hi - mid

    if n <= _SMALL_MERGE_CAP or a_len <= _MIN_BLOCK or b_len <= _MIN_BLOCK:
        _buffer_merge(arr, lo, mid, hi, key)
        return

    s = max(_MIN_BLOCK, int(math.isqrt(n)))

    rem = a_len % s
    buf_size = s + rem if rem else s
    if buf_size > a_len:
        buf_size = a_len

    buf = arr[lo:lo + buf_size]

    body_start = lo + buf_size
    a_body = a_len - buf_size
    K = a_body // s
    b_trim = b_len % s
    b_body_len = b_len - b_trim
    M = b_body_len // s
    b_body_end = mid + b_body_len
    total_blocks = K + M

    if total_blocks <= 1 or K == 0:
        arr[lo:lo + buf_size] = buf
        _buffer_merge(arr, lo, mid, hi, key)
        return

    workspace = arr[lo:lo + s]

    def _block_cmp(t1, t2):
        s1 = t1[0]; idx1 = t1[1]
        s2 = t2[0]; idx2 = t2[1]
        st1 = body_start + idx1 * s if s1 == 0 else mid + idx1 * s
        st2 = body_start + idx2 * s if s2 == 0 else mid + idx2 * s
        f1 = key(arr[st1]) if key else arr[st1]
        l1 = key(arr[st1 + s - 1]) if key else arr[st1 + s - 1]
        f2 = key(arr[st2]) if key else arr[st2]
        l2 = key(arr[st2 + s - 1]) if key else arr[st2 + s - 1]
        if s1 == 1 and s2 == 0 and l1 >= f2:
            return 1
        if s1 == 0 and s2 == 1 and l2 >= f1:
            return -1
        if f1 != f2:
            return -1 if f1 < f2 else 1
        if s1 != s2:
            return -1 if s1 < s2 else 1
        return -1 if idx1 < idx2 else (1 if idx1 > idx2 else 0)

    blocks = [(0, i) for i in range(K)]
    blocks.extend((1, j) for j in range(M))
    blocks.sort(key=cmp_to_key(_block_cmp))

    from .int_array.core import IntHybridArray
    inv_bl = max(1, (total_blocks - 1).bit_length())
    inv_perm = IntHybridArray([0], bit_length=inv_bl, hash_=False) * total_blocks
    for t in range(total_blocks):
        b = blocks[t]
        src = b[0]
        idx = b[1]
        inv_perm[t] = idx if src == 0 else K + idx

    visited = FalsesArray(total_blocks, hash_=False)
    for t in range(total_blocks):
        if visited[t] or inv_perm[t] == t:
            visited[t] = True
            continue
        t_start = body_start + t * s
        workspace[:s] = arr[t_start:t_start + s]
        cur = t
        while True:
            nxt = inv_perm[cur]
            visited[cur] = True
            if nxt == t:
                break
            nxt_start = body_start + nxt * s
            cur_start = body_start + cur * s
            arr[cur_start:cur_start + s] = arr[nxt_start:nxt_start + s]
            cur = nxt
        cur_start = body_start + cur * s
        arr[cur_start:cur_start + s] = workspace[:s]

    prefix_end = body_start + s
    if key is None:
        bstart = body_start + s
        for _ in range(1, total_blocks):
            if arr[prefix_end - 1] <= arr[bstart]:
                prefix_end = bstart + s
                bstart += s
                continue
            bv = arr[bstart]
            ls = body_start
            le2 = prefix_end
            while ls < le2:
                mid = (ls + le2) >> 1
                if bv < arr[mid]:
                    le2 = mid
                else:
                    ls = mid + 1
            overlap_start = ls
            workspace[:s] = arr[bstart:bstart + s]
            i = bstart - 1
            j = s - 1
            k = bstart + s - 1
            while i >= overlap_start and j >= 0:
                if arr[i] <= workspace[j]:
                    arr[k] = workspace[j]; j -= 1
                else:
                    arr[k] = arr[i]; i -= 1
                k -= 1
            if j >= 0:
                arr[overlap_start:overlap_start + j + 1] = workspace[:j + 1]
            prefix_end = bstart + s
            bstart += s
    else:
        bstart = body_start + s
        for _ in range(1, total_blocks):
            cb = key(arr[bstart])
            if key(arr[prefix_end - 1]) <= cb:
                prefix_end = bstart + s
                bstart += s
                continue
            overlap_start = _bisect_right(arr, arr[bstart], body_start, prefix_end, key)
            workspace[:s] = arr[bstart:bstart + s]
            i = bstart - 1
            j = s - 1
            k = bstart + s - 1
            while i >= overlap_start and j >= 0:
                if key(arr[i]) <= key(workspace[j]):
                    arr[k] = workspace[j]; j -= 1
                else:
                    arr[k] = arr[i]; i -= 1
                k -= 1
            if j >= 0:
                arr[overlap_start:overlap_start + j + 1] = workspace[:j + 1]
            prefix_end = bstart + s
            bstart += s

    if b_trim > 0:
        _buffer_merge(arr, body_start, b_body_end, hi, key)
    prefix_end = hi

    arr[lo:lo + buf_size] = buf
    _buffer_merge(arr, lo, body_start, prefix_end, key)


def _count_run(arr, lo, hi, key=None):
    if lo + 1 >= hi:
        return 1
    if key is None:
        if arr[lo] <= arr[lo + 1]:
            i = lo + 2
            while i < hi and arr[i - 1] <= arr[i]:
                i += 1
            return i - lo
        i = lo + 2
        while i < hi and arr[i] < arr[i - 1]:
            i += 1
        _reverse(arr, lo, i)
        return i - lo
    if _le(arr[lo], arr[lo + 1], key):
        i = lo + 2
        while i < hi and _le(arr[i - 1], arr[i], key):
            i += 1
        return i - lo
    else:
        i = lo + 2
        while i < hi and _lt(arr[i], arr[i - 1], key):
            i += 1
        _reverse(arr, lo, i)
        return i - lo


def _min_run(n):
    r = 0
    while n >= 64:
        r |= n & 1
        n >>= 1
    return n + r


def twg_sort(arr, key=None, reverse=False):
    n = len(arr)
    if n <= 1:
        return
    _twg_sort_impl(arr, key)
    if reverse:
        _stable_reverse(arr, 0, n, key)


def _stable_reverse(arr, lo, hi, key=None):
    _reverse(arr, lo, hi)
    i = lo
    while i < hi:
        j = i + 1
        vi = key(arr[i]) if key else arr[i]
        while j < hi:
            vj = key(arr[j]) if key else arr[j]
            if not (not (vi < vj) and not (vj < vi)):
                break
            j += 1
        if j - i > 1:
            _reverse(arr, i, j)
        i = j


def _powersort_power(pos1, len1, pos2, len2, n):
    """PowerSort 节点幂：相邻 run1=[pos1,pos1+len1) 与 run2=[pos2,pos2+len2) 边界的幂。

    幂 = 两个 run 中点归一化分数 (mid/n) 的二进制前导相同位数。
    用整数移位计算（CPython listobject.c / power-sort.github.io 的做法）：
        a = 2*pos1 + len1 = 2*mid1
        b = a + len1 + len2 = 2*mid2
    每次循环比较 a/n 与 b/n 的下一位；a>=n 时同步减 n，b>=n 说明两位不同，返回。
    幂越大 => 越晚合并（该边界在虚拟完美二叉树中越深）。
    """
    a = 2 * pos1 + len1
    b = a + len1 + len2
    p = 0
    while True:
        p += 1
        if a >= n:
            a -= n
            b -= n
        elif b >= n:
            break
        a <<= 1
        b <<= 1
    return p


def _twg_sort_impl(arr, key=None):
    n = len(arr)
    if n <= 1:
        return
    if n <= 32:
        _insertion_sort(arr, 0, n, key)
        return

    threshold = int(math.isqrt(n)) << 2
    grail_threshold = int((n << 1) / math.log2(n)) if n > 4 else n
    min_run = _min_run(n)

    # 惰性导入，避免循环：int_array/float_array 都会 from ..twg_sort import twg_sort，
    # 而 struct_array 又依赖 int_array/float_array。函数内 import 时包已加载完毕，无环。
    from .struct_array.core import StructHybridArray, BHA_Struct
    if _twg_sort_impl._Run is None:
        class _Run(BHA_Struct):
            __BHAStructAttrs__ = {"pos": int, "length": int, "power": int}
        _twg_sort_impl._Run = _Run
    _Run = _twg_sort_impl._Run

    # 栈项列存: pos/length/power 各占一个 IntHybridArray 列（PowerSort 幂记在右侧 run 上）。
    run_stack = StructHybridArray(_Run, 0, hash_=False)
    rs_attrs = run_stack.attrs
    pos = 0

    def _next_run(start):
        rl = _count_run(arr, start, n, key)
        if rl < min_run:
            end = min(n, start + min_run)
            _insertion_sort(arr, start, end, key)
            rl = end - start
        return rl

    # 第一个 run 直接入栈（幂 0：无左边界）
    run_len = _next_run(pos)
    run_stack.append({'pos': pos, 'length': run_len, 'power': 0})
    pos += run_len

    while pos < n:
        ti = len(run_stack) - 1
        tpos = rs_attrs['pos'][ti]
        tlen = rs_attrs['length'][ti]
        tpow = rs_attrs['power'][ti]
        run_len = _next_run(pos)
        # 新边界（栈顶 run 与新 run 之间）的节点幂
        p = _powersort_power(tpos, tlen, pos, run_len, n)
        # PowerSort 栈不等式：新幂不大于栈顶已记录的幂，就闭合（合并）栈顶两项
        while p <= tpow:
            _merge_at(arr, run_stack, len(run_stack) - 2, threshold, grail_threshold, key)
            ti = len(run_stack) - 1
            tpos = rs_attrs['pos'][ti]
            tlen = rs_attrs['length'][ti]
            tpow = rs_attrs['power'][ti]
        run_stack.append({'pos': pos, 'length': run_len, 'power': p})
        pos += run_len

    # 扫描结束：把栈里剩余 run 全部向右级联合并
    while len(run_stack) > 1:
        _merge_at(arr, run_stack, len(run_stack) - 2, threshold, grail_threshold, key)

_twg_sort_impl._Run = None


def _merge_at(arr, run_stack, idx, threshold, grail_threshold, key=None):
    a_start = run_stack.attrs['pos'][idx]
    a_len = run_stack.attrs['length'][idx]
    b_len = run_stack.attrs['length'][idx + 1]  # noqa
    mid = a_start + a_len
    hi = mid + b_len
    total = a_len + b_len

    lo2 = _bisect_right(arr, arr[mid], a_start, mid, key)
    hi2 = _bisect_left(arr, arr[mid - 1], mid, hi, key)
    if lo2 < mid and mid < hi2:
        if total <= threshold:
            _buffer_merge(arr, lo2, mid, hi2, key)
        elif total <= grail_threshold:
            _block_merge(arr, lo2, mid, hi2, use_grail=False, key=key)
        else:
            _block_merge(arr, lo2, mid, hi2, use_grail=True, key=key)

    # 合并后的 run 占据 idx 位置；其左边界幂即原 idx 项的 power（保持不动）。
    run_stack.attrs['pos'][idx] = a_start
    run_stack.attrs['length'][idx] = total
    del run_stack[idx + 1]


def twg_sorted(seq, key=None, reverse=False):
    result = list(seq)
    twg_sort(result, key=key, reverse=reverse)
    return result
