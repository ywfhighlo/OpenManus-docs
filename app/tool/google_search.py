# Google搜索工具模块
# 设计说明：
# 1. 提供异步Google搜索功能
# 2. 支持自定义结果数量
# 3. 使用线程池避免阻塞
# 4. 返回匹配URL列表

import asyncio
from typing import List

from googlesearch import search

from app.tool.base import BaseTool


# Google搜索工具类
# 功能特性：
# 1. 支持自定义搜索查询
# 2. 可配置返回结果数量
# 3. 异步执行避免阻塞
# 4. 统一的URL列表返回
class GoogleSearch(BaseTool):
    name: str = "google_search"
    description: str = """Perform a Google search and return a list of relevant links.
Use this tool when you need to find information on the web, get up-to-date data, or research specific topics.
The tool returns a list of URLs that match the search query.
"""
    # 工具参数定义
    # 必需参数：
    # - query: 搜索查询字符串
    # 可选参数：
    # - num_results: 返回结果数量（默认10个）
    parameters: dict = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "(required) The search query to submit to Google.",
            },
            "num_results": {
                "type": "integer",
                "description": "(optional) The number of search results to return. Default is 10.",
                "default": 10,
            },
        },
        "required": ["query"],
    }

    async def execute(self, query: str, num_results: int = 10) -> List[str]:
        """
        Execute a Google search and return a list of URLs.

        Args:
            query (str): The search query to submit to Google.
            num_results (int, optional): The number of search results to return. Default is 10.

        Returns:
            List[str]: A list of URLs matching the search query.
        """
        # 在线程池中执行搜索以避免阻塞
        loop = asyncio.get_event_loop()
        links = await loop.run_in_executor(
            None, lambda: list(search(query, num_results=num_results))
        )

        return links
