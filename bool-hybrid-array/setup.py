from setuptools import setup, find_packages
import os
def get_long_description():
    readme_path = os.path.join(os.path.dirname(__file__), 'README.md')
    if os.path.exists(readme_path):
        with open(readme_path, encoding='utf-8') as f:
            return f.read()
    return "一个高效的布尔数组（密集+稀疏混合存储，节省内存）"
setup(
    name="bool-hybrid-array",
    version="9.9.3",
    author="蔡靖杰",
    author_email="1289270215@qq.com",
    description="一个高效的布尔数组（密集+稀疏混合存储，节省内存）",
    long_description=get_long_description(),
    long_description_content_type="text/markdown",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=['numpy>=1.19.0'],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    keywords="boolean array, compact storage",
    package_data={"": ["README.md", "LICENSE",'temp.py', 'temp.cmd','测试代码.py']},
    include_package_data=True,
)