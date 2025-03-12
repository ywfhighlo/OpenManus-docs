# 异常定义模块
# 设计说明：
# 1. 定义系统特定异常
# 2. 提供错误信息管理
# 3. 支持异常追踪和处理

class ToolError(Exception):
    """
    Raised when a tool encounters an error.
    
    工具错误异常
    
    功能：
    1. 错误标识：标识工具执行过程中的错误
    2. 消息管理：保存和传递错误信息
    3. 异常追踪：支持异常栈追踪
    """

    def __init__(self, message):
        """
        初始化工具错误异常
        
        参数：
        - message: 错误信息
        """
        self.message = message
