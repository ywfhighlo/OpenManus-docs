"""Collection classes for managing multiple tools."""
# 工具集合模块
# 提供管理多个工具的集合类，支持工具注册、检索和执行
from typing import Any, Dict, List

from app.exceptions import ToolError
from app.tool.base import BaseTool, ToolFailure, ToolResult


class ToolCollection:
    """A collection of defined tools."""

    class Config:
        arbitrary_types_allowed = True

    # 初始化工具集合，接收多个工具实例并构建名称映射
    def __init__(self, *tools: BaseTool):
        self.tools = tools
        self.tool_map = {tool.name: tool for tool in tools}

    # 支持迭代集合中的所有工具
    def __iter__(self):
        return iter(self.tools)

    # 将所有工具转换为API参数格式
    def to_params(self) -> List[Dict[str, Any]]:
        return [tool.to_param() for tool in self.tools]

    # 执行指定名称的工具，处理输入参数和错误
    async def execute(
        self, *, name: str, tool_input: Dict[str, Any] = None
    ) -> ToolResult:
        tool = self.tool_map.get(name)
        if not tool:
            return ToolFailure(error=f"Tool {name} is invalid")
        try:
            result = await tool(**tool_input)
            return result
        except ToolError as e:
            return ToolFailure(error=e.message)

    # 依次执行集合中的所有工具
    async def execute_all(self) -> List[ToolResult]:
        """Execute all tools in the collection sequentially."""
        results = []
        for tool in self.tools:
            try:
                result = await tool()
                results.append(result)
            except ToolError as e:
                results.append(ToolFailure(error=e.message))
        return results

    # 通过名称获取工具实例
    def get_tool(self, name: str) -> BaseTool:
        return self.tool_map.get(name)

    # 添加单个工具到集合
    def add_tool(self, tool: BaseTool):
        self.tools += (tool,)
        self.tool_map[tool.name] = tool
        return self

    # 批量添加多个工具到集合
    def add_tools(self, *tools: BaseTool):
        for tool in tools:
            self.add_tool(tool)
        return self
