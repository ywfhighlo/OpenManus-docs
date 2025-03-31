# 自定义异常模块
# 定义项目中使用的特定异常类型

# 工具执行错误异常
class ToolError(Exception):
    """Raised when a tool encounters an error."""

    def __init__(self, message):
        self.message = message


# OpenManus项目的基础异常类
class OpenManusError(Exception):
    """Base exception for all OpenManus errors"""


# Token数量超出限制异常
class TokenLimitExceeded(OpenManusError):
    """Exception raised when the token limit is exceeded"""
