# 项目安装配置脚本
# 用于配置OpenManus项目的安装信息、依赖项和入口点
from setuptools import find_packages, setup


# 读取README作为长描述
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    # 项目基本信息
    name="openmanus",
    version="0.1.0",
    author="mannaandpoem and OpenManus Team",
    author_email="mannaandpoem@gmail.com",
    description="A versatile agent that can solve various tasks using multiple tools",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/mannaandpoem/OpenManus",

    # 包发现和依赖项配置
    packages=find_packages(),
    install_requires=[
        # 核心依赖
        "pydantic~=2.10.4",
        "openai>=1.58.1,<1.67.0",
        "tenacity~=9.0.0",
        "pyyaml~=6.0.2",
        "loguru~=0.7.3",
        "numpy",

        # 功能相关依赖
        "datasets~=3.2.0",
        "html2text~=2024.2.26",
        "gymnasium~=1.0.0",
        "pillow~=10.4.0",
        "browsergym~=0.13.3",
        "uvicorn~=0.34.0",
        "unidiff~=0.7.5",
        "browser-use~=0.1.40",
        "googlesearch-python~=1.3.0",
        "aiofiles~=24.1.0",
        "pydantic_core>=2.27.2,<2.28.0",
        "colorama~=0.4.6",
    ],

    # 分类信息
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.12",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],

    # Python版本要求
    python_requires=">=3.12",

    # 命令行入口点
    entry_points={
        "console_scripts": [
            "openmanus=main:main",
        ],
    },
)
