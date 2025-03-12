# 日志系统模块
# 设计说明：
# 1. 提供统一的日志记录接口
# 2. 支持控制台和文件双重输出
# 3. 实现可配置的日志级别
# 4. 支持自定义日志文件命名
# 5. 基于loguru实现高性能日志处理

import sys
from datetime import datetime

from loguru import logger as _logger

from app.config import PROJECT_ROOT


# 默认控制台输出级别
_print_level = "INFO"


def define_log_level(print_level="INFO", logfile_level="DEBUG", name: str = None):
    """
    Adjust the log level to above level
    
    配置日志系统
    
    功能：
    1. 日志级别：分别配置控制台和文件的日志级别
    2. 输出管理：支持同时输出到控制台和文件
    3. 文件命名：支持自定义日志文件名前缀
    4. 时间戳：自动添加时间戳到日志文件名
    
    参数：
    - print_level: 控制台输出的日志级别
    - logfile_level: 文件输出的日志级别
    - name: 可选的日志文件名前缀
    """
    global _print_level
    _print_level = print_level

    # 生成带时间戳的日志文件名
    current_date = datetime.now()
    formatted_date = current_date.strftime("%Y%m%d%H%M%S")
    log_name = (
        f"{name}_{formatted_date}" if name else formatted_date
    )  # name a log with prefix name

    # 重置并配置日志处理器
    _logger.remove()
    _logger.add(sys.stderr, level=print_level)
    _logger.add(PROJECT_ROOT / f"logs/{log_name}.log", level=logfile_level)
    return _logger


# 创建全局日志实例
logger = define_log_level()


if __name__ == "__main__":
    # 日志使用示例
    logger.info("Starting application")
    logger.debug("Debug message")
    logger.warning("Warning message")
    logger.error("Error message")
    logger.critical("Critical message")

    # 异常处理示例
    try:
        raise ValueError("Test error")
    except Exception as e:
        logger.exception(f"An error occurred: {e}")
