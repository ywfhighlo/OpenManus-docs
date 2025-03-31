# 百度搜索引擎模块
# 提供百度网络搜索功能实现
from baidusearch.baidusearch import search

from app.tool.search.base import WebSearchEngine


# 百度搜索引擎实现类
class BaiduSearchEngine(WebSearchEngine):
    def perform_search(self, query, num_results=10, *args, **kwargs):
        """Baidu search engine."""
        return search(query, num_results=num_results)
