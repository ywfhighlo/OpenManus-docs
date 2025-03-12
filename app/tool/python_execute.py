# Python代码执行工具模块
# 设计说明：
# 1. 提供安全的Python代码执行环境
# 2. 支持超时控制
# 3. 限制全局变量访问
# 4. 捕获标准输出

import threading
from typing import Dict

from app.tool.base import BaseTool


# Python代码执行工具类
# 功能特性：
# 1. 安全执行：限制全局变量访问
# 2. 超时控制：防止无限循环
# 3. 输出捕获：重定向标准输出
# 4. 错误处理：统一的异常处理机制
class PythonExecute(BaseTool):
    """A tool for executing Python code with timeout and safety restrictions."""

    name: str = "python_execute"
    description: str = "Executes Python code string. Note: Only print outputs are visible, function return values are not captured. Use print statements to see results."
    # 工具参数定义
    # 必需参数：
    # - code: 要执行的Python代码字符串
    parameters: dict = {
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "The Python code to execute.",
            },
        },
        "required": ["code"],
    }

    async def execute(
        self,
        code: str,
        timeout: int = 5,
    ) -> Dict:
        """
        Executes the provided Python code with a timeout.

        Args:
            code (str): The Python code to execute.
            timeout (int): Execution timeout in seconds.

        Returns:
            Dict: Contains 'output' with execution output or error message and 'success' status.
        """
        result = {"observation": ""}

        # 代码执行函数
        # 实现：
        # 1. 创建安全的全局变量环境
        # 2. 重定向标准输出
        # 3. 执行代码并捕获结果
        # 4. 恢复标准输出
        def run_code():
            try:
                # 创建安全的全局变量环境
                safe_globals = {"__builtins__": dict(__builtins__)}

                import sys
                from io import StringIO

                # 重定向标准输出
                output_buffer = StringIO()
                sys.stdout = output_buffer

                # 执行代码
                exec(code, safe_globals, {})

                # 恢复标准输出
                sys.stdout = sys.__stdout__

                result["observation"] = output_buffer.getvalue()

            except Exception as e:
                result["observation"] = str(e)
                result["success"] = False

        # 在线程中执行代码并设置超时
        thread = threading.Thread(target=run_code)
        thread.start()
        thread.join(timeout)

        # 检查是否超时
        if thread.is_alive():
            return {
                "observation": f"Execution timeout after {timeout} seconds",
                "success": False,
            }

        return result
