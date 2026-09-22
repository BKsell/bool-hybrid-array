# cython: language_level=3,boundscheck=False,wraparound=False,cdivision=True,nonecheck=False,overflowcheck=False,initializedcheck=False,infer_types=True,annotation_typing=True,profile=False,linetrace=False,emit_code_comments=False,c_api_binop_methods=True

import math
from functools import cmp_to_key
from .core import BoolHybridArr

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
    if key is None:
        for i in range(lo + 1, hi):
            kv = arr[i]
            pos = lo
            hi2 = i
            while pos < hi2:
                mid = (pos + hi2) >> 1
                if kv < arr[mid]:
                    hi2 = mid
                else:
                    pos = mid + 1
            arr[pos + 1:i + 1] = arr[pos:i]
            arr[pos] = kv
    else:
        for i in range(lo + 1, hi):
            kv = arr[i]
            kkv = key(kv)
            pos = lo
            hi2 = i
            while pos < hi2:
                mid = (pos + hi2) >> 1
                if kkv < key(arr[mid]):
                    hi2 = mid
                else:
                    pos = mid + 1
            arr[pos + 1:i + 1] = arr[pos:i]
            arr[pos] = kv


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

    blocks = [(0, i) for i in range(K)] + [(1, j) for j in range(M)]
    blocks.sort(key=cmp_to_key(_block_cmp))

    from .int_array.core import IntHybridArray
    inv_bl = max(1, (total_blocks - 1).bit_length())
    inv_perm = IntHybridArray([0] * total_blocks, bit_length=inv_bl)
    for t in range(total_blocks):
        b = blocks[t]
        src = b[0]
        idx = b[1]
        inv_perm[t] = idx if src == 0 else K + idx

    visited = BoolHybridArr([False] * total_blocks)
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


def _twg_sort_impl(arr, key=None):
    n = len(arr)
    if n <= 1:
        return
    if n <= 32:
        _insertion_sort(arr, 0, n, key)
        return

    threshold = int(math.isqrt(n)) << 1
    grail_threshold = int((n << 1) / math.log2(n)) if n > 4 else n
    min_run = _min_run(n)

    run_stack = []
    pos = 0
    while pos < n:
        run_len = _count_run(arr, pos, n, key)
        if run_len < min_run:
            end = min(n, pos + min_run)
            _insertion_sort(arr, pos, end, key)
            run_len = end - pos
        run_stack.append((pos, run_len))
        pos += run_len
        _merge_collapse(arr, run_stack, threshold, grail_threshold, key)

    while len(run_stack) > 1:
        _merge_at(arr, run_stack, len(run_stack) - 2, threshold, grail_threshold, key)


def _merge_collapse(arr, run_stack, threshold, grail_threshold, key=None):
    while len(run_stack) >= 2:
        n = len(run_stack)
        if n >= 3:
            a_len = run_stack[n - 3][1]
            b_len = run_stack[n - 2][1]
            c_len = run_stack[n - 1][1]
            if a_len <= b_len + c_len or b_len <= c_len:
                idx = n - 3 if a_len < c_len else n - 2
                _merge_at(arr, run_stack, idx, threshold, grail_threshold, key)
                continue
        else:
            b_len = run_stack[n - 2][1]
            c_len = run_stack[n - 1][1]
            if b_len <= c_len:
                _merge_at(arr, run_stack, n - 2, threshold, grail_threshold, key)
                continue
        break


def _merge_at(arr, run_stack, idx, threshold, grail_threshold, key=None):
    a_start = run_stack[idx][0]
    a_len = run_stack[idx][1]
    b_len = run_stack[idx + 1][1]
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

    run_stack[idx] = (a_start, total)
    del run_stack[idx + 1]


def twg_sorted(seq, key=None, reverse=False):
    result = list(seq)
    twg_sort(result, key=key, reverse=reverse)
    return result
