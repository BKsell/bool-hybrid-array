from setuptools import setup, find_packages, Extension
import os,sys,shutil,atexit
import traceback

os.chdir(os.path.dirname(os.path.abspath(__file__)))

try:
    import numpy as np
    include_dirs = [np.get_include()]

    source_files = [
        "bool_hybrid_array/core.py"
    ]

    pyx_files = []
    for idx, py_src in enumerate(source_files):
        pyx_src = py_src[:-3] + ".pyx"
        shutil.copy2(py_src, pyx_src)
        pyx_files.append(pyx_src)
        atexit.register(lambda f=pyx_src: os.path.exists(f) and os.remove(f))

    source_files = pyx_files
    exts = []

    if sys.platform == "win32":
        c_args = [
            "/O2","/Ob3",
        ]
        link_args = ["/OPT:REF", "/OPT:ICF"]
    else:
        import platform
        arch = platform.machine().lower()
        c_args = [
            "-O3"
        ]
        link_args = ["-flto=full", "-Wl,--gc-sections"]

        if arch in ("x86_64", "amd64"):
            c_args.append("-march=x86-64-v2")
        elif arch.startswith("arm") or arch == "aarch64":
            c_args.append("-march=armv8-a")

    for src in source_files:
        mod_path, _ = os.path.splitext(src)
        mod_name = mod_path.replace("/", ".")
        exts.append(Extension(
            mod_name,
            sources=[src],
            extra_compile_args=c_args,
            extra_link_args=link_args,
            include_dirs=include_dirs
        ))

    from Cython.Build import cythonize
    ext_modules = cythonize(
        exts,
        annotate=False
    )

except BaseException as e:
    ext_modules = []
    include_dirs = []
    traceback.print_exception(type(e), e, e.__traceback__)

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
        license="Apache-2.0",
        license_files=["LICENSE", "NOTICE"],
        name="bool-hybrid-array",
        version="9.12.6",
        author="蔡靖杰",
        extras_require={
            "int_array": [],
            "numba_opt": ["numba>=0.55.0"],
            "cython_opt": ["cython>=3.2.4"],
            "cycy opt": ["cycy-runtime>=0.2.5"]
        },
        author_email="1289270215@qq.com",
        description="一个高效的布尔数组（密集+稀疏混合存储，节省内存）",
        long_description=get_long_description(),
        long_description_content_type="text/markdown",
        packages=find_packages(),
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
            "License :: OSI Approved :: Apache-2.0 License",
            "Operating System :: OS Independent",
        ],
        keywords="boolean array, compact storage",
        package_data={
            "": ["README.md", "LICENSE", "NOTICE", 'temp.py', 'temp.cmd', 'BHA_Opener.7z'],
            "bool_hybrid_array": ["*.py", "*.pyd", "*.c", "*"],
            r"bool_hybrid_array\__pycache__": ['*.pyc'],
            r"bool_hybrid_array\int_array": ["*.py", "*.pyd", "*.c", "*"],
            r"bool_hybrid_array\float_array": ["*.py", "*.pyd", "*.c", "*"]
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