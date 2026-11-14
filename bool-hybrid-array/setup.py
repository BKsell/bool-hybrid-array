from setuptools import setup, find_packages, Extension
import os,sys,shutil,atexit,re
import traceback

os.chdir(os.path.dirname(os.path.abspath(__file__)))

try:
    import tokenize
    import ast
    from io import BytesIO
    import numpy as np
    include_dirs = [np.get_include()]

    source_files = (
        "bool_hybrid_array/core.py",
        "bool_hybrid_array/int_array/core.py",
         "bool_hybrid_array/float_array/core.py",
         "bool_hybrid_array/struct_array/core.py",
         "bool_hybrid_array/twg_sort.py",
         "bool_hybrid_array/cjx.py",
         "bool_hybrid_array/forest.py",
    )

    py_sources = list(source_files)
    pyx_files = []
    for idx, py_src in enumerate(py_sources):
        pyx_src = py_src[:-3] + ".pyx"
        shutil.copy2(py_src, pyx_src)
        pyx_files.append(pyx_src)
        atexit.register(lambda f=pyx_src: os.path.exists(f) and os.remove(f))
    _RET_SAFE = {'object', 'bytes', 'str', 'list', 'dict', 'set', 'tuple', 'frozenset',
                 'bytearray', 'memoryview'}
    def _splice(rows, edits):
        for r, c0, c1, repl in sorted(edits, reverse=True):
            line = rows[r - 1]
            rows[r - 1] = line[:c0] + repl + line[c1:]

    def _def_to_cpdef(text: str, cdef_names=None) -> str:
        cdef_names = cdef_names or set()
        bom = ''
        if text[:1] == '\ufeff':
            bom, text = text[:1], text[1:]
        rows = text.splitlines(keepends=True)
        tokens = list(tokenize.tokenize(BytesIO(text.encode('utf-8')).readline))
        edits = []
        depth = 0
        decorated = False
        prev_row = 0
        pending_class = None
        class_stack = []
        for i, tok in enumerate(tokens):
            ttype, tstr = tok[0], tok[1]
            if ttype == tokenize.INDENT:
                depth += 1
                if pending_class is not None:
                    class_stack.append((depth, pending_class, tok[3][1]))
                    pending_class = None
                continue
            if ttype == tokenize.DEDENT:
                if class_stack and class_stack[-1][0] == depth:
                    class_stack.pop()
                depth -= 1
                continue
            if ttype in (tokenize.NL, tokenize.NEWLINE,
                         tokenize.COMMENT, tokenize.ENCODING):
                continue
            if ttype == tokenize.NAME and tstr == 'class':
                if i + 1 < len(tokens) and tokens[i + 1][0] == tokenize.NAME:
                    pending_class = tokens[i + 1][1]
                decorated = False
                continue
            if tok[2][0] == prev_row:
                continue
            prev_row = tok[2][0]
            if depth == 0:
                if tok[2][1] != 0:
                    continue
            elif depth == 1 and class_stack:
                if class_stack[-1][2] != tok[2][1] or class_stack[-1][1] not in cdef_names:
                    decorated = False
                    continue
            else:
                decorated = False
                continue
            if ttype == tokenize.OP and tstr == '@':
                decorated = True
                continue
            if ttype == tokenize.NAME and tstr == 'def':
                if decorated:
                    decorated = False
                    continue
                if i and tokens[i - 1][1] == 'async':
                    continue
                if i + 2 >= len(tokens):
                    continue
                t1 = tokens[i + 1]
                t2 = tokens[i + 2]
                if not (t1[0] == tokenize.NAME and t2[0] == tokenize.OP and t2[1] == '('):
                    continue
                j = i + 2
                nest = 0
                varargs = False
                ann = []
                astart = None
                while j < len(tokens):
                    if tokens[j][0] == tokenize.OP:
                        tj = tokens[j][1]
                        if tj in ('*', '**') and nest == 1:
                            varargs = True
                        if tj in '([{':
                            nest += 1
                        elif tj in ')]}':
                            nest -= 1
                            if nest == 0:
                                if astart is not None:
                                    ann.append((astart, tokens[j]))
                                    astart = None
                                break
                        elif nest == 1:
                            if tj == ':' and j > 0 and tokens[j - 1][0] == tokenize.NAME:
                                astart = tokens[j]
                            elif tj in (',', '=') and astart is not None:
                                ann.append((astart, tokens[j]))
                                astart = None
                    j += 1
                ann_edits = []
                for a0, a1 in ann:
                    if a0[2][0] == a1[2][0]:
                        ann_edits.append((a0[2][0], a0[2][1], a1[2][1], ''))
                if t1[1].startswith('__') and t1[1].endswith('__'):
                    edits.extend(ann_edits)
                    continue
                if varargs:
                    edits.extend(ann_edits)
                    continue
                repl = 'cpdef'
                extras = list(ann_edits)
                if j + 1 < len(tokens) and tokens[j + 1][1] == '->':
                    aj = j + 1
                    cnest = 0
                    cend = None
                    for cj in range(aj + 1, len(tokens)):
                        ct, cs = tokens[cj][0], tokens[cj][1]
                        if ct == tokenize.OP:
                            if cs in '([{':
                                cnest += 1
                            elif cs in ')]}':
                                cnest -= 1
                            elif cs == ':' and cnest == 0:
                                cend = cj
                                break
                        elif ct == tokenize.NEWLINE:
                            break
                    if cend is None or tokens[aj][2][0] != tokens[cend][2][0]:
                        continue
                    mid = tokens[aj + 1:cend]
                    rtype = None
                    if len(mid) == 1 and mid[0][0] == tokenize.NAME and mid[0][1] in _RET_SAFE:
                        rtype = mid[0][1]
                    else:
                        rtype = 'object'
                    repl = 'cpdef ' + rtype
                    arow = tokens[aj][2][0]
                    ac0 = tokens[aj][2][1]
                    line_txt = rows[arow - 1]
                    if ac0 > 0 and line_txt[ac0 - 1] == ' ':
                        ac0 -= 1
                    extras.append((arow, ac0, tokens[cend][2][1], ''))
                block = 0
                nest_paren = 0
                is_generator = False
                for k in range(i + 2, len(tokens)):
                    kt, ks = tokens[k][0], tokens[k][1]
                    if kt == tokenize.INDENT:
                        block += 1
                    elif kt == tokenize.DEDENT:
                        block -= 1
                        if block <= 0:
                            break
                    elif kt == tokenize.OP:
                        if ks in '([{':
                            nest_paren += 1
                        elif ks in ')]}':
                            nest_paren -= 1
                    elif kt == tokenize.NAME and block > 0:
                        if ks in ('yield', 'lambda', 'def', 'class') or (ks == 'for' and nest_paren > 0):
                            is_generator = True
                            break
                if is_generator:
                    continue
                edits.append((tok[2][0], tok[2][1], tok[3][1], repl))
                edits.extend(extras)
                continue
            decorated = False
        for row, c0, c1, repl in sorted(edits, reverse=True):
            line = rows[row - 1]
            rows[row - 1] = line[:c0] + repl + line[c1:]
        return bom + ''.join(rows)

    import builtins as _builtins
    import collections.abc as _cab
    _SKIP_ABC_DUNDER = frozenset(('__subclasshook__', '__init_subclass__', '__class_getitem__',
                                  '__new__', '__init__', '__slots__', '__dict__', '__weakref__',
                                  '__module__', '__doc__', '__abstractmethods__'))
    _SKIP_FLAGS = 0x04 | 0x08
    _BLOCK_DEF = frozenset(('__new__', '__getattr__', '__setattr__', '__delattr__',
                            '__getattribute__'))

    _CDEF_HELPERS = '''
import collections.abc as _cabc_
_CDEF_MRO_KEEP = []

def _cdef_mro_patch(cls, base):
    import ctypes
    bm = getattr(base, '__mro__', None)
    if bm is None:
        base = getattr(base, '__origin__', base)
        bm = getattr(base, '__mro__', None)
    if bm is None:
        return cls
    old = [c for c in cls.__mro__[1:] if c is not object]
    abc = [c for c in bm if c is not object]
    rest = [c for c in old if c not in abc]
    mro = (cls,) + tuple(abc) + tuple(rest) + (object,)
    words = (ctypes.c_void_p * 64).from_address(id(cls))
    slot = None
    p = id(cls.__mro__)
    for i in range(3, 64):
        if words[i] == p:
            slot = i
            break
    if slot is None:
        raise RuntimeError('tp_mro slot not found for ' + cls.__name__)
    _CDEF_MRO_KEEP.append(mro)
    for t in mro + (mro,):
        ctypes.pythonapi.Py_IncRef(ctypes.py_object(t))
    words[slot] = id(mro)
    ctypes.pythonapi.PyType_Modified.argtypes = [ctypes.py_object]
    ctypes.pythonapi.PyType_Modified.restype = None
    ctypes.pythonapi.PyType_Modified(cls)
    base.register(type('_CDEF_Bump', (object,), {}))
    return cls

def _cdef_meta_retag(cls, meta):
    import ctypes
    p = ctypes.cast(id(cls), ctypes.POINTER(ctypes.c_void_p))
    ctypes.pythonapi.Py_IncRef(ctypes.py_object(meta))
    p[1] = id(meta)
    return cls

def _abc_impl_new():
    import abc
    return abc.ABCMeta('_CDEF_T', (object,), {}).__dict__['_abc_impl']

def _cdef_set_dict(obj, d):
    import ctypes
    api = ctypes.pythonapi
    api.PyObject_GenericSetDict.argtypes = [ctypes.py_object, ctypes.py_object, ctypes.c_void_p]
    api.PyObject_GenericSetDict.restype = ctypes.c_int
    if api.PyObject_GenericSetDict(obj, d, None) != 0:
        raise TypeError('cannot set __dict__')
    return d
'''

    def _base_kind(name, converted):
        if name in converted:
            return 'ext'
        base = getattr(_builtins, name, None)
        if isinstance(base, type) and getattr(base, '__module__', '') == 'builtins':
            return 'ext'
        last = name.split('.')[-1]
        if name.startswith('abc.'):
            return 'other'
        if (name == last or name.startswith('collections.abc.')) and last.isidentifier() \
                and getattr(_cab, last, None) is not None:
            return 'abc'
        return 'other'

    def _scan_bases(tokens, i):
        name = tokens[i + 1][1]
        bases = []
        meta = None
        mode = 'base'
        nest = 0
        lp = rp = None
        for j in range(i + 1, len(tokens)):
            tt, ts = tokens[j][0], tokens[j][1]
            prev = tokens[j - 1][1] if j > i + 1 else ''
            if tt == tokenize.OP:
                if ts == '(':
                    nest += 1
                    if nest == 1:
                        lp = tokens[j]
                elif ts == ')':
                    nest -= 1
                    if nest == 0:
                        rp = tokens[j]
                elif ts == ':' and nest == 0:
                    return name, bases, meta, j, lp, rp
                elif ts == ',' and nest == 1:
                    if bases and bases[-1][2] is None:
                        bases[-1][2] = tokens[j]
                    mode = 'base'
                elif ts == '=':
                    mode = 'meta_next'
            elif tt == tokenize.NAME and nest == 1:
                if mode == 'meta_next':
                    mode = 'meta'
                    meta = ts
                elif mode == 'meta':
                    if prev == '.':
                        meta = meta + '.' + ts
                elif prev == '.' and bases:
                    bases[-1][1] = bases[-1][1] + '.' + ts
                elif tokens[j + 1][1] == '=':
                    pass
                else:
                    bases.append([tokens[j], ts, None])
        return name, bases, meta, None, lp, rp

    def _body_start(tokens, cidx):
        k = cidx + 1
        while k < len(tokens) and tokens[k][0] in (tokenize.NL, tokenize.COMMENT, tokenize.NEWLINE):
            k += 1
        if k < len(tokens) and tokens[k][0] == tokenize.INDENT:
            k += 1
            while k < len(tokens) and tokens[k][0] in (tokenize.NL, tokenize.COMMENT):
                k += 1
        return k

    def _slot_names(seq):
        ops = [t[1] for t in seq if t[0] == tokenize.OP]
        if not any(o in ('(', '[') for o in ops) or '.' in ops:
            return []
        out = [t[1].strip('\'"') if t[0] == tokenize.STRING else t[1] for t in seq
               if t[0] == tokenize.STRING
               or (t[0] == tokenize.NAME and t[1] not in ('None', 'True', 'False'))]
        return out if out and all(v.isidentifier() for v in out) else []

    def _fix_dict(text: str):
        rows = text.splitlines(keepends=True)
        tokens = list(tokenize.tokenize(BytesIO(text.encode('utf-8')).readline))
        edits = []
        spans = []
        for i, t in enumerate(tokens):
            if t[0] != tokenize.NAME or i + 3 >= len(tokens):
                continue
            if tokens[i + 1][1] != '.' or tokens[i + 2][1] != '__dict__':
                continue
            if t[2][0] != tokens[i + 2][2][0]:
                continue
            if any(r == t[2][0] and c0 <= t[2][1] < c1 for r, c0, c1 in spans):
                continue
            if tokens[i + 3][0] == tokenize.OP and tokens[i + 3][1] == '=':
                row = t[2][0]
                if row <= len(rows):
                    line = rows[row - 1]
                    nl = '\r\n' if line.endswith('\r\n') else ('\n' if line.endswith('\n') else '')
                    body = line[:len(line) - len(nl)] if nl else line
                    rhs = body[tokens[i + 3][2][1] + 1:].strip()
                    single = False
                    no_nl = False
                    for m in range(i + 4, len(tokens)):
                        if tokens[m][0] == tokenize.NL:
                            no_nl = True
                            break
                        if tokens[m][0] in (tokenize.NEWLINE, tokenize.ENDMARKER):
                            single = tokens[m][2][0] == row
                            break
                    if single and not no_nl and rhs and '#' not in rhs \
                            and '"' not in rhs and "'" not in rhs:
                        rhs = re.sub(r'([A-Za-z_][A-Za-z0-9_]*)\s*\.\s*__dict__',
                                     r"object.__getattribute__(\1, '__dict__')", rhs)
                        edits.append((row, t[2][1], len(body),
                                      '_cdef_set_dict(' + t[1] + ', ' + rhs + ')'))
                        spans.append((row, t[2][1], len(body)))
                continue
            edits.append((t[2][0], t[2][1], tokens[i + 2][3][1],
                          'object.__getattribute__(' + t[1] + ", '__dict__')"))
        _splice(rows, edits)
        return ''.join(rows)

    _CONTAINER_HOOKS = {'__getitem__', '__setitem__', '__delitem__', '__contains__'}

    def _dedupe_methods(text: str):
        tree = ast.parse(text)
        rows = text.splitlines(keepends=True)
        drop = {}
        for cls in tree.body:
            if not isinstance(cls, ast.ClassDef):
                continue
            seen = {}
            for m in cls.body:
                if isinstance(m, ast.FunctionDef):
                    seen.setdefault(m.name, []).append(m)
            for lst in seen.values():
                for m in lst[:-1]:
                    start = min([d.lineno for d in m.decorator_list] + [m.lineno])
                    drop[start] = max(drop.get(start, 0), m.end_lineno)
        if not drop:
            return text
        out = []
        i = 1
        while i <= len(rows):
            end = drop.get(i)
            if end is not None:
                i = end + 1
                continue
            out.append(rows[i - 1])
            i += 1
        return ''.join(out)

    def _drop_slash(text: str):
        rows = text.splitlines(keepends=True)
        tokens = list(tokenize.tokenize(BytesIO(text.encode('utf-8')).readline))
        edits = []
        for k, t in enumerate(tokens):
            if t[0] != tokenize.OP or t[1] != '/' or k == 0 or k + 1 >= len(tokens):
                continue
            prev, nxt = tokens[k - 1], tokens[k + 1]
            if prev[1] != ',' or nxt[1] not in (',', ')'):
                continue
            if prev[2][0] != t[2][0] or t[2][0] != nxt[2][0]:
                continue
            edits.append((t[2][0], prev[2][1], t[3][1], ''))
        _splice(rows, edits)
        return ''.join(rows)

    def _base_expr(node):
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            sub = _base_expr(node.value)
            return None if sub is None else sub + '.' + node.attr
        return None

    def _unwrap_hook_defaults(text: str):
        tree = ast.parse(text)
        rows = text.splitlines(keepends=True)
        nl = '\r\n' if rows and rows[0].endswith('\r\n') else '\n'
        stubs = {}
        for cls in ast.walk(tree):
            if not isinstance(cls, ast.ClassDef):
                continue
            for m in cls.body:
                if not (isinstance(m, ast.FunctionDef) and m.name in _CONTAINER_HOOKS
                        and m.args.defaults):
                    continue
                names = [a.arg for a in m.args.posonlyargs + m.args.args]
                orig = rows[m.lineno - 1]
                line = orig
                for d in sorted(m.args.defaults, key=lambda x: x.col_offset, reverse=True):
                    s = line.rfind('=', 0, d.col_offset)
                    e = d.end_col_offset
                    while e < len(line) and line[e] in ' \t':
                        e += 1
                    line = line[:s].rstrip() + line[e:]
                rows[m.lineno - 1] = line
                arrow = orig.find('->')
                close = orig.rfind(')') if arrow < 0 else orig.rfind(')', 0, arrow)
                if close < 0:
                    continue
                head = orig[:len(orig) - len(orig.lstrip())]
                params = orig[orig.index('('):close + 1]
                if m.name == '__getitem__':
                    body = 'return self[' + names[1] + ']'
                elif m.name == '__delitem__':
                    body = 'del self[' + names[1] + ']'
                elif m.name == '__setitem__':
                    body = 'self[' + names[1] + '] = ' + names[2]
                else:
                    body = 'return ' + names[1] + ' in self'
                stub = '_bha_hook_' + m.name
        out = []
        for i, line in enumerate(rows, 1):
            out.append(line)
            out.extend(stubs.get(i, []))
        return ''.join(out)

    def _extract_nested(text: str):
        tree = ast.parse(text)
        rows = text.splitlines(keepends=True)
        nl = '\r\n' if rows and rows[0].endswith('\r\n') else '\n'
        ins_map = {}
        rep_map = {}
        for cls in tree.body:
            if not isinstance(cls, ast.ClassDef):
                continue
            host_row = min([d.lineno for d in cls.decorator_list] + [cls.lineno])
            for m in cls.body:
                if not isinstance(m, ast.ClassDef):
                    continue
                start = min([d.lineno for d in m.decorator_list] + [m.lineno])
                end = m.end_lineno
                head = rows[start - 1]
                indent = head[:len(head) - len(head.lstrip())]
                fname = '_bha_nest_' + cls.name + '_' + m.name
                seg = rows[start - 1:end]
                if seg and not seg[-1].endswith('\n'):
                    seg[-1] = seg[-1] + nl
                builder = ['def ' + fname + '():' + nl]
                base = min(len(r) - len(r.lstrip()) for r in seg if r.strip())
                for r in seg:
                    builder.append(('    ' + r[base:]) if r.strip() else r)
                builder.append('    ' + m.name + '.__qualname__ = ' + repr(cls.name + '.' + m.name) + nl)
                builder.append('    return ' + m.name + nl + nl)
                ins_map.setdefault(host_row, []).extend(builder)
                rep_map[start] = (end, [indent + m.name + ' = ' + fname + '()' + nl])
        if not rep_map:
            return text
        out = []
        i = 1
        while i <= len(rows):
            out.extend(ins_map.get(i, []))
            if i in rep_map:
                end, rep = rep_map[i]
                out.extend(rep)
                i = end + 1
                continue
            out.append(rows[i - 1])
            i += 1
        return ''.join(out)

    def _class_to_cdef(text: str, converted: set):
        field_map = {}
        cls_members = {}
        dict_classes = set()
        for node in ast.parse(text).body:
            if not isinstance(node, ast.ClassDef):
                continue
            reserved = set()
            init = set()
            for sub in ast.walk(node):
                if isinstance(sub, ast.Assign):
                    for tg in sub.targets:
                        if isinstance(tg, ast.Attribute) and tg.attr == '__dict__' \
                                and isinstance(tg.ctx, ast.Store):
                            dict_classes.add(node.name)
            for m in node.body:
                if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    reserved.add(m.name)
                    if m.name in ('__init__', '__cinit__'):
                        for sub in ast.walk(m):
                            if (isinstance(sub, ast.Attribute) and isinstance(sub.value, ast.Name)
                                    and sub.value.id == 'self' and isinstance(sub.ctx, ast.Store)):
                                init.add(sub.attr)
                elif isinstance(m, ast.Assign):
                    for t in m.targets:
                        if isinstance(t, ast.Name):
                            reserved.add(t.id)
            cls_members[node.name] = (init, reserved)
        bom = ''
        if text[:1] == '\ufeff':
            bom, text = text[:1], text[1:]
        rows = text.splitlines(keepends=True)
        nl = '\r\n' if rows and rows[0].endswith('\r\n') else '\n'
        tokens = list(tokenize.tokenize(BytesIO(text.encode('utf-8')).readline))
        marks = []
        blocks = []
        tails = []
        names = set()
        meta_names = set()
        for i, tok in enumerate(tokens):
            if tok[0] != tokenize.NAME or tok[1] != 'metaclass':
                continue
            j = i + 1
            if j < len(tokens) and tokens[j][1] == '=':
                j += 1
            if j < len(tokens) and tokens[j][0] == tokenize.NAME:
                meta_names.add(tokens[j][1])
        depth = 0
        for i, tok in enumerate(tokens):
            if tok[0] == tokenize.INDENT:
                depth += 1
                continue
            if tok[0] == tokenize.DEDENT:
                depth -= 1
                continue
            if depth != 0 or tok[0] != tokenize.NAME or tok[1] != 'class':
                continue
            if i + 1 >= len(tokens) or tokens[i + 1][0] != tokenize.NAME:
                continue
            name, bases, meta_name, cidx, lp, rp = _scan_bases(tokens, i)
            if cidx is None:
                continue
            kinds = [(b[1], _base_kind(b[1], converted | names)) for b in bases if b[1]]
            if any(kd == 'other' for _, kd in kinds):
                continue
            if name in meta_names or any(nm == 'type' for nm, _ in kinds):
                continue
            abc_bases = [nm for nm, kd in kinds if kd == 'abc']
            if len(abc_bases) > 1:
                continue
            keep = [nm for nm, kd in kinds if kd == 'ext']
            if lp is not None and lp[2][0] != rp[2][0]:
                continue
            k = _body_start(tokens, cidx)
            if k >= len(tokens):
                continue
            indent = tokens[k][2][1]
            ins_row = tokens[k][2][0]
            if tokens[k][0] == tokenize.STRING:
                m = k + 1
                while m < len(tokens) and tokens[m][0] != tokenize.NEWLINE:
                    m += 1
                if m < len(tokens):
                    ins_row = tokens[m][3][0] + 1
            blocking = False
            slot_span = None
            slot_names = []
            d2 = 1
            for m in range(k, len(tokens)):
                t = tokens[m]
                if t[0] == tokenize.INDENT:
                    d2 += 1
                elif t[0] == tokenize.DEDENT:
                    d2 -= 1
                    if d2 == 0:
                        break
                elif t[0] == tokenize.NAME and d2 == 1 and t[2][1] == indent:
                    if t[1] == 'class' or (t[1] == 'def' and m + 1 < len(tokens)
                                           and tokens[m + 1][1] in _BLOCK_DEF):
                        blocking = True
                        break
                    if t[1] == '__slots__' and slot_span is None:
                        e = m
                        while e < len(tokens) and tokens[e][0] != tokenize.NEWLINE:
                            e += 1
                        if e < len(tokens):
                            slot_span = (t[2][0], tokens[e][3][0])
                            slot_names = _slot_names(tokens[m + 1:e])
            if blocking:
                continue
            if slot_span is not None and not slot_names:
                continue
            init_set, reserved = cls_members.get(name, (set(), set()))
            marks.append((tok[2][0], tok[2][1], tok[2][1], 'cdef '))
            if lp is not None:
                body = '(' + ', '.join(keep) + ')' if keep else ''
                marks.append((lp[2][0], lp[2][1], rp[3][1], body))
            slot_set = set(slot_names)
            body_lines = [' ' * indent + 'cdef dict __dict__']
            parent_fields = set()
            for b in keep:
                parent_fields |= field_map.get(b, set())
            if '__weakref__' not in parent_fields:
                body_lines.append(' ' * indent + 'cdef object __weakref__')
            own = [] if name in dict_classes else [attr for attr in sorted(init_set)
                   if not attr.startswith('__') and attr not in reserved
                   and attr not in parent_fields and attr not in slot_set]
            for attr in own:
                body_lines.append(' ' * indent + 'cdef public object ' + attr)
            field_map[name] = parent_fields | set(own) | set(slot_names) | {'__weakref__'}
            if meta_name is not None and not abc_bases:
                body_lines.append(' ' * indent + '_abc_impl = _abc_impl_new()')
            blocks.append(('ins', ins_row, ins_row, body_lines))
            if slot_span is not None:
                blocks.append(('rep', slot_span[0], slot_span[1],
                               [' ' * indent + 'cdef public object ' + s for s in slot_names]))
            if abc_bases:
                _abc_cls = getattr(_cab, abc_bases[0].split('.')[-1], None)
                if _abc_cls is not None:
                    for _src in _abc_cls.__mro__:
                        if _src is object or getattr(_src, '__module__', '') == 'builtins':
                            continue
                        for _nm, _fn in list(vars(_src).items()):
                            if not (_nm.startswith('__') and _nm.endswith('__')):
                                continue
                            if _nm in _SKIP_ABC_DUNDER or _nm in reserved:
                                continue
                            if not callable(_fn) or getattr(_fn, '__isabstractmethod__', False):
                                continue
                            _code = getattr(_fn, '__code__', None)
                            if _code is None or _code.co_flags & _SKIP_FLAGS or _code.co_argcount < 1:
                                continue
                            if getattr(_fn, '__defaults__', None) or getattr(_fn, '__kwdefaults__', None):
                                continue
                            _params = _code.co_varnames[:_code.co_argcount]
                            body_lines.append(' ' * indent + 'def ' + _nm + '(' + ', '.join(_params) + '):')
                            body_lines.append(' ' * (indent + 4) + 'return _cabc_.' + _src.__name__ + '.' + _nm
                                              + '(' + ', '.join(_params) + ')')
                tails.append('_cdef_mro_patch(' + name + ', ' + abc_bases[0] + ')')
            if meta_name is not None and not abc_bases:
                tails.append('_cdef_meta_retag(' + name + ', ' + meta_name + ')')
            names.add(name)
        for r, c0, c1, repl in sorted(marks, reverse=True):
            line = rows[r - 1]
            rows[r - 1] = line[:c0] + repl + line[c1:]
        insert_map = {}
        replace_map = {}
        for kind, r1, r2, lines in blocks:
            if kind == 'ins':
                insert_map.setdefault(r1, []).extend(lines)
            else:
                replace_map[r1] = (r2, lines)
        out = []
        i = 1
        while i <= len(rows):
            if i in insert_map:
                out.extend(x + nl for x in insert_map[i])
            if i in replace_map:
                end, lines = replace_map[i]
                out.extend(x + nl for x in lines)
                i = end + 1
                continue
            out.append(rows[i - 1])
            i += 1
        return bom + ''.join(out), names, tails

    _NOMINMAX_SHIM = '''cdef extern from *:
    """
    #ifdef min
    #undef min
    #endif
    #ifdef max
    #undef max
    #endif
    """

'''

    def _rewrite_pyx(do_it: bool):
        converted = set()
        for py_src, pyx_src in zip(py_sources, pyx_files):
            shutil.copy2(py_src, pyx_src)
            if not do_it:
                continue
            raw = open(pyx_src, 'rb').read()
            text = raw.decode('utf-8')
            text = _dedupe_methods(text)
            text = _drop_slash(text)
            text = _extract_nested(text)
            text = _unwrap_hook_defaults(text)
            nxt, names, tails = _class_to_cdef(text, converted)
            nxt = _fix_dict(nxt)
            nxt = _def_to_cpdef(nxt, names)
            if tails:
                nxt = nxt.rstrip('\n') + '\n\n' + '\n'.join(tails) + '\n'
            head = _NOMINMAX_SHIM + _CDEF_HELPERS.strip('\n') + '\n\n'
            fi = nxt.find('\nfrom __future__ import')
            if fi < 0:
                nxt = head + nxt
            else:
                eol = nxt.find('\n', fi + 1)
                if eol < 0:
                    eol = len(nxt)
                nxt = nxt[:eol] + '\n' + head + nxt[eol:]
            converted |= names
            if nxt != text:
                open(pyx_src, 'wb').write(nxt.encode('utf-8'))

    source_files = pyx_files
    exts = []

    if sys.platform == "win32":
        c_args = [
            "/O2","/Ob3",
        ]
        link_args = ["/OPT:REF", "/OPT:ICF"]
    else:
        c_args = ["-O3"]
        link_args = []

    def _make_exts():
        return [Extension(
            os.path.splitext(src)[0].replace("/", "."),
            sources=[src],
            extra_compile_args=c_args,
            extra_link_args=link_args,
            include_dirs=include_dirs
        ) for src in source_files]

    from Cython.Build import cythonize
    _rewrite_pyx(True)
    try:
        ext_modules = cythonize(_make_exts())
    except BaseException:
        traceback.print_exception(*sys.exc_info())
        print("cpdef 改写版本编译失败，回退为纯 def 源码重建")
        _rewrite_pyx(False)
        ext_modules = cythonize(_make_exts())

except:
    ext_modules = []
    include_dirs = []
    traceback.print_exc()

finally:
    def get_long_description():
        readme_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'README.md')
        if os.path.exists(readme_path):
            with open(readme_path, encoding='utf-8') as f:
                return f.read()
        return "一个高效的布尔数组（密集+稀疏混合存储，节省内存）"

    if sys.implementation.name == "pypy":
        if not hasattr(sys, "pypy_version_info") or sys.pypy_version_info[:3] < (7, 3, 10):
            pypy_ver = ".".join(map(str, sys.pypy_version_info)) if hasattr(sys, "pypy_version_info") else "未知"
            sys.exit(f"\033[31m❌ 错误：bool-hybrid-array 要求 PyPy≥7.3.10，当前版本 {pypy_ver}\033[0m")

    setup(
        license="Apache-2.0 OR MulanPSL-2.0",
        license_files=["LICENSE", "NOTICE", "LICENSE-MulanPSL2"],
        name="bool-hybrid-array",
        version="9.13.12",
        author="蔡靖杰",
        extras_require={
            "numba_opt": ["numba>=0.55.0"],
            "cycy_opt": ["cycy-runtime>=0.2.5"]
        },
        author_email="1289270215@qq.com",
        description="一个高效的布尔数组（密集+稀疏混合存储，节省内存）",
        long_description=get_long_description(),
        long_description_content_type="text/markdown",
        packages=find_packages(),
        python_requires=">=3.8",
        install_requires=('numpy>=1.19.0',),
        classifiers=(
            "Programming Language :: Cython",
            "Programming Language :: Python",
            "Programming Language :: Python :: 3",
            'Programming Language :: Python :: 3.8',
            'Programming Language :: Python :: 3.9',
            'Programming Language :: Python :: 3.10',
            'Programming Language :: Python :: 3.11',
            'Programming Language :: Python :: 3.12',
            'Programming Language :: Python :: 3.13',
            'Programming Language :: Python :: 3.14',
            'Programming Language :: Python :: 3.15',
            "Programming Language :: Python :: 3 :: Only",
            'Programming Language :: Python :: Implementation :: CPython',
            'Programming Language :: Python :: Implementation :: PyPy',
            "License :: OSI Approved :: Apache Software License",
            "License :: OSI Approved :: Mulan Permissive Software License v2 (MulanPSL-2.0)",
            "Operating System :: OS Independent",
        ),
        keywords = (
        "boolean array",
        "compact storage",
        "bit array",
        "bit vector",
        "bitmap",
        "sparse boolean array",
        "hybrid bitmap",
        "roaring bitmap",
        "binary storage",
        "bool storage",
        "bit packing",
        "set operations",
        "logical operation",
        "fast boolean",
        "sparse bitmap",
        "array",
        ),
        package_data={
            "": ["README.md", "LICENSE", "NOTICE", "LICENSE-MulanPSL2" , 'BHA_Opener.7z',"setup.py","pyproject.toml"],
            "bool_hybrid_array": ["*.py"],
            "bool_hybrid_array/int_array": ["*.py"],
            "bool_hybrid_array/float_array": ["*.py"],
            "bool_hybrid_array/struct_array": ["*.py"],
        },
        include_package_data=True,
        url="https://github.com/BKsell/bool-hybrid-array",
        project_urls={
            "GitHub 主站": "https://github.com/BKsell/bool-hybrid-array.git",
            "GitHub 中文镜像": "https://www.github-zh.com/projects/1083175506-bool-hybrid-array",
            "Gitee 站": "https://gitee.com/BKsell/bool-hybrid-array.git",
            "GitCode 站": "https://atomgit.com/BKsell/bool-hybrid-array.git",
            "Issue 反馈（GitHub主站）": "https://github.com/BKsell/bool-hybrid-array.git/issues",
            "Issue 反馈（Gitee站）": "https://gitee.com/BKsell/bool-hybrid-array.git/issues"
        },
        ext_modules=ext_modules,
        include_dirs=include_dirs,
    )