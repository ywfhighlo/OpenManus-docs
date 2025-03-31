# 谷歌搜索引擎模块
# 提供谷歌网络搜索功能实现
from googlesearch import search

from app.tool.search.base import WebSearchEngine


# 谷歌搜索引擎实现类
class GoogleSearchEngine(WebSearchEngine):
    def perform_search(self, query, num_results=10, *args, **kwargs):
        """Google search engine."""
        return search(query, num_results=num_results)
