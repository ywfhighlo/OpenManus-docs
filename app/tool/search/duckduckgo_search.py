# DuckDuckGo搜索引擎模块
# 提供DuckDuckGo网络搜索功能实现
from duckduckgo_search import DDGS

from app.tool.search.base import WebSearchEngine


# DuckDuckGo搜索引擎实现类
class DuckDuckGoSearchEngine(WebSearchEngine):
    async def perform_search(self, query, num_results=10, *args, **kwargs):
        """DuckDuckGo search engine."""
        return DDGS.text(query, num_results=num_results)
