import importlib.util, sys, types
from pathlib import Path

candidates = set()
seen = set()
def init():
    global candidates,seen
    for root in sys.path:
        if not root:
            continue
        rp = Path(root)
        if not rp.is_dir():
            continue
        try:
            for entry in rp.iterdir():
                stem = entry.stem
                if stem in seen or stem.startswith("_") or not stem.isidentifier():
                    continue
                seen.add(stem)
                if (entry.is_file() and entry.suffix in {".py", ".pyd", ".so"}) or (entry.is_dir() and (entry / "__init__.py").exists()):
                    try:
                        if importlib.util.find_spec(stem):
                            candidates.add(stem)
                    except Exception:
                        continue
        except PermissionError:
            continue
    candidates.update(b for b in sys.builtin_module_names if b.isidentifier())
init()
class LazyImport(types.ModuleType):
    __slots__ = ("_name")
    def __init__(self,name):
        super().__init__(name)
        self._name = name
    def __getattr__(self,attr):
        return getattr(__import__(self._name),attr)
    def __setattr__(self,attr,obj):
        if attr == "_name":
            super().__setattr__(attr,obj)
            return
        setattr(__import__(self._name),attr,obj)
globals().update({name : LazyImport(name) for name in candidates})