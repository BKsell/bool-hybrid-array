from setuptools import setup, find_packages
import os,sys,subprocess
try:
    import Cython
    subprocess.run([sys.executable,"-m","cythonize","bool_hybrid_array/core.py"])
except:pass
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
    name="bool-hybrid-array",
    version="9.11.16",
    author="蔡靖杰",
    extras_require={"int_array":[],"numba_opt": ["numba>=0.55.0"],"cython_opt":["cython>=3.2.4"],"cycy opt":["cycy-runtime>=0.2.4"]},
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
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    keywords="boolean array, compact storage",
    package_data={"": ["README.md", "LICENSE",'temp.py', 'temp.cmd','BHA_Opener.zip'],"bool_hybrid_array":["*"],"bool_hybrid_array/__pycache__":['*.pyc']},
    include_package_data=True,
    url="https://github.com/BKsell/bool-hybrid-array",
    project_urls={
        "GitHub 主站": "https://github.com/BKsell/bool-hybrid-array",
        "GitHub 中文镜像": "https://www.github-zh.com/projects/1083175506-bool-hybrid-array",
        "Issue 反馈（主站）": "https://github.com/BKsell/bool-hybrid-array/issues",
    },
)