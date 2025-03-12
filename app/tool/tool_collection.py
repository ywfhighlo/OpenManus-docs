# 工具集合管理模块
# 设计说明：
# 1. 提供工具集合的统一管理接口
# 2. 支持工具的动态添加和获取
# 3. 实现工具的批量执行功能

"""Collection classes for managing multiple tools."""
from typing import Any, Dict, List

from app.exceptions import ToolError
from app.tool.base import BaseTool, ToolFailure, ToolResult


# 工具集合类
# 功能特性：
# 1. 工具注册与管理
# 2. 工具查找与获取
# 3. 单个/批量工具执行
# 4. 参数格式转换
class ToolCollection:
    """A collection of defined tools."""

    def __init__(self, *tools: BaseTool):
        # 初始化工具列表和映射表
        self.tools = tools
        self.tool_map = {tool.name: tool for tool in tools}

    def __iter__(self):
        return iter(self.tools)

    def to_params(self) -> List[Dict[str, Any]]:
        """转换所有工具为函数调用格式"""
        return [tool.to_param() for tool in self.tools]

    async def execute(
        self, *, name: str, tool_input: Dict[str, Any] = None
    ) -> ToolResult:
        """执行单个工具
        参数：
            name: 工具名称
            tool_input: 工具输入参数
        返回：
            工具执行结果
        """
        tool = self.tool_map.get(name)
        if not tool:
            return ToolFailure(error=f"Tool {name} is invalid")
        try:
            result = await tool(**tool_input)
            return result
        except ToolError as e:
            return ToolFailure(error=e.message)

    async def execute_all(self) -> List[ToolResult]:
        """按顺序执行所有工具
        返回：
            所有工具的执行结果列表
        """
        results = []
        for tool in self.tools:
            try:
                result = await tool()
                results.append(result)
            except ToolError as e:
                results.append(ToolFailure(error=e.message))
        return results

    def get_tool(self, name: str) -> BaseTool:
        """根据名称获取工具实例"""
        return self.tool_map.get(name)

    def add_tool(self, tool: BaseTool):
        """添加单个工具到集合"""
        self.tools += (tool,)
        self.tool_map[tool.name] = tool
        return self

    def add_tools(self, *tools: BaseTool):
        """批量添加工具到集合"""
        for tool in tools:
            self.add_tool(tool)
        return self
