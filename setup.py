# 项目安装配置模块
# 设计说明：
# 1. 包管理：使用setuptools进行包管理
# 2. 版本控制：明确的版本号管理
# 3. 依赖管理：详细的依赖包配置
# 4. 元数据管理：完整的项目信息
# 5. 入口配置：命令行工具入口设置

from setuptools import find_packages, setup


# 读取README文件
# - 使用UTF-8编码确保正确读取中文
# - 用作包的详细描述
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# 项目配置
# 核心配置项：
# 1. 基本信息：
#    - 项目名称：openmanus
#    - 版本号：0.1.0
#    - 作者信息
#    - 项目描述
# 2. 文档配置：
#    - README作为长描述
#    - Markdown格式支持
# 3. 代码配置：
#    - 自动发现包
#    - Python版本要求
# 4. 分发信息：
#    - MIT许可证
#    - 支持多平台
setup(
    # 项目标识
    name="openmanus",
    version="0.1.0",
    author="mannaandpoem and OpenManus Team",
    author_email="mannaandpoem@gmail.com",
    description="A versatile agent that can solve various tasks using multiple tools",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/mannaandpoem/OpenManus",
    
    # 包配置
    packages=find_packages(),
    
    # 依赖配置
    # 核心依赖说明：
    # 1. 基础框架：
    #    - pydantic: 数据验证
    #    - openai: AI模型接口
    # 2. 工具支持：
    #    - browsergym: 浏览器模拟
    #    - html2text: HTML处理
    #    - googlesearch-python: 搜索功能
    # 3. 功能增强：
    #    - tenacity: 重试机制
    #    - loguru: 日志系统
    #    - aiofiles: 异步文件操作
    # 4. 界面支持：
    #    - uvicorn: Web服务器
    #    - colorama: 终端颜色
    install_requires=[
        "pydantic~=2.10.4",
        "openai~=1.58.1",
        "tenacity~=9.0.0",
        "pyyaml~=6.0.2",
        "loguru~=0.7.3",
        "numpy",
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
        "pydantic_core~=2.27.2",
        "colorama~=0.4.6",
    ],
    
    # 分类标签
    # - 指定Python版本
    # - 开源许可证
    # - 运行平台
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.12",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    
    # 运行环境
    # - 要求Python 3.12或更高版本
    python_requires=">=3.12",
    
    # 命令行工具
    # - 配置openmanus命令
    # - 指向main.py的main函数
    entry_points={
        "console_scripts": [
            "openmanus=main:main",
        ],
    },
)
