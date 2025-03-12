# 文件保存工具模块
# 设计说明：
# 1. 提供异步文件保存功能
# 2. 支持文件写入和追加模式
# 3. 自动创建目标目录
# 4. 统一的错误处理机制

import os

import aiofiles

from app.tool.base import BaseTool


# 文件保存工具类
# 功能特性：
# 1. 支持文本内容保存
# 2. 自动创建目标目录
# 3. 可选的写入模式（写入/追加）
# 4. 异步IO操作
class FileSaver(BaseTool):
    name: str = "file_saver"
    description: str = """Save content to a local file at a specified path.
Use this tool when you need to save text, code, or generated content to a file on the local filesystem.
The tool accepts content and a file path, and saves the content to that location.
"""
    # 工具参数定义
    # 必需参数：
    # - content: 要保存的内容
    # - file_path: 保存路径
    # 可选参数：
    # - mode: 文件打开模式（w:写入/a:追加）
    parameters: dict = {
        "type": "object",
        "properties": {
            "content": {
                "type": "string",
                "description": "(required) The content to save to the file.",
            },
            "file_path": {
                "type": "string",
                "description": "(required) The path where the file should be saved, including filename and extension.",
            },
            "mode": {
                "type": "string",
                "description": "(optional) The file opening mode. Default is 'w' for write. Use 'a' for append.",
                "enum": ["w", "a"],
                "default": "w",
            },
        },
        "required": ["content", "file_path"],
    }

    async def execute(self, content: str, file_path: str, mode: str = "w") -> str:
        """
        Save content to a file at the specified path.

        Args:
            content (str): The content to save to the file.
            file_path (str): The path where the file should be saved.
            mode (str, optional): The file opening mode. Default is 'w' for write. Use 'a' for append.

        Returns:
            str: A message indicating the result of the operation.
        """
        try:
            # 确保目标目录存在
            directory = os.path.dirname(file_path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory)

            # 异步写入文件内容
            async with aiofiles.open(file_path, mode, encoding="utf-8") as file:
                await file.write(content)

            return f"Content successfully saved to {file_path}"
        except Exception as e:
            return f"Error saving file: {str(e)}"
