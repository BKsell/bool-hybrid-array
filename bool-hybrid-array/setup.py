from setuptools import setup, find_packages, Extension
import os,sys,subprocess,shutil,atexit
try:
    from Cython.Build import cythonize
    import numpy as np
    include_dirs = [np.get_include()]

    source_files = [
        "bool_hybrid_array/core.py",
        "bool_hybrid_array/int_array/core.py",
        "bool_hybrid_array/float_array/core.py"
    ]
    pyx_files = []
    for idx, py_src in enumerate(source_files):
        if idx == 1: 
            pyx_files.append(py_src)
            continue
        pyx_src = py_src[:-3] + ".pyx"
        shutil.copy2(py_src, pyx_src)
        pyx_files.append(pyx_src)
        atexit.register(lambda f=pyx_src: os.path.exists(f) and os.remove(f))
    source_files = pyx_files
    exts = []
    for src in source_files:
        mod_path, _ = os.path.splitext(src)
        mod_name = mod_path.replace("/", ".")
        if sys.platform == "win32":
            c_args = [
                "/O2", "/fp:fast", "/GL", "/GT", "/Oi", "/Ot", "/Qpar",
                "/Ob3", "/GF", "/Gy", "/Gw", "/Gv", "/Qvec"
            ]
            link_args = ["/LTCG", "/OPT:REF", "/OPT:ICF"]
        elif sys.platform in {"linux", "darwin"}:
            c_args = [
                "-O3", "-march=native", "-mtune=native", "-ffast-math", "-fno-math-errno",
                "-funroll-loops", "-funroll-all-loops", "-fomit-frame-pointer",
                "-ftree-vectorize", "-fvect-cost-model=unlimited", "-finline-functions",
                "-finline-limit=10000", "-fno-stack-protector", "-fmerge-all-constants"
            ]
            link_args = ["-flto=full", "-Wl,--gc-sections"]
        else:
            c_args = ["-O3", "-ffast-math", "-funroll-loops"]
            link_args = []
        exts.append(Extension(
            mod_name,
            sources=[src],
            extra_compile_args=c_args,
            extra_link_args=link_args
        ))

    ext_modules = cythonize(
        exts,
        compiler_directives={
            "language_level": "3",
            "boundscheck": False,
            "wraparound": False,
            "cdivision": True,
            "nonecheck": True,
            "initialized_check": True,
            "overflowcheck": True,
            "fastmath": True,
            "infer_types": True,
            "annotation_typing": True,
            "optimize.inline": True,
            "optimize.unroll": True,
            "optimize.eliminate_dead_code": True,
            "optimize.aggressive_bounds": True,
            "profile": False,
            "linetrace": False,
            "docstrings": False,
            "emit_code_comments": False,
            "c_api_binop_methods": False,
            "annotate": False
        },
        compiler_directives_path=None,
        annotate=False
    )

except:
    ext_modules = []
    include_dirs = []
finally:
    def get_long_description():
        readme_path = os.path.join(os.path.dirname(__file__), 'README.md')
        if os.path.exists(readme_path):
            with open(readme_path, encoding='utf-8') as f:
                return f.read()
        return "一个高效的布尔数组（密集+稀疏混合存储，节省内存）"
    if sys.implementation.name == "pypy":
                if not hasattr(sys, "pypy_version_info") or sys.pypy_version_info[:3] < (7, 3, 10):
                    pypy_ver = ".".join(map(str, sys.pypy_version_info)) if hasattr(sys, "pypy_version_info") else "未知"
                    sys.exit(f"\033[31m❌ 错误：bool-hybrid-array 要求 PyPy≥7.3.10，当前版本 {pypy_ver}\033[0m")
    setup(
        license="MIT; Supplementary binding terms contained in NOTICE file",
        license_files=["LICENSE", "NOTICE"],
        name="bool-hybrid-array",
        version="9.11.41",
        author="蔡靖杰",
        extras_require={"int_array":[],"numba_opt": ["numba>=0.55.0"],"cython_opt":["cython>=3.2.4"],"cycy opt":["cycy-runtime>=0.2.5"]},
        author_email="1289270215@qq.com",
        description="一个高效的布尔数组（密集+稀疏混合存储，节省内存）",
        long_description=get_long_description(),
        long_description_content_type="text/markdown",
        packages=set(find_packages()+["bool_hybrid_array.int_array","bool_hybrid_array.float_array"]),
        python_requires=">=3.8",
        install_requires=['numpy>=1.19.0'],
        classifiers=[
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
            "Programming Language :: Python :: 3 :: Only",
            'Programming Language :: Python :: Implementation :: CPython',
            'Programming Language :: Python :: Implementation :: PyPy', 
            "License :: OSI Approved :: MIT License",
            "Operating System :: OS Independent",
        ],
        keywords="boolean array, compact storage",
        package_data={"": ["README.md", "LICENSE","NOTICE",'temp.py', 'temp.cmd','BHA_Opener.7z'],"bool_hybrid_array":["*.py","*.pyd","*.c","*"],r"bool_hybrid_array\__pycache__":['*.pyc'],r"bool_hybrid_array\int_array":["*.py","*.pyd","*.c","*"],r"bool_hybrid_array\float_array":["*.py","*.pyd","*.c","*"]},
        include_package_data=True,
        url="https://github.com/BKsell/bool-hybrid-array",
        project_urls={
            "GitHub 主站": "https://github.com/BKsell/bool-hybrid-array.git",
            "GitHub 中文镜像": "https://www.github-zh.com/projects/1083175506-bool-hybrid-array",
            "Gitee 站": "https://gitee.com/BKsell/bool-hybrid-array.git",
            "Issue 反馈（GitHub主站）": "https://github.com/BKsell/bool-hybrid-array.git/issues",
            "lssue 反馈（Gitee站）": "https://gitee.com/BKsell/bool-hybrid-array.git/issues"
        },
        ext_modules = ext_modules,
        include_dirs = include_dirs,
    )
