# 工具系统基础组件
# 设计说明：
# 1. 定义了工具系统的核心抽象类和接口
# 2. 实现了工具执行结果的数据模型
# 3. 提供了工具结果的组合和处理机制

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


# 基础工具抽象类
# 功能：
# 1. 定义工具的基本属性（名称、描述、参数）
# 2. 提供统一的执行接口
# 3. 支持函数调用格式转换
class BaseTool(ABC, BaseModel):
    name: str
    description: str
    parameters: Optional[dict] = None

    class Config:
        arbitrary_types_allowed = True

    async def __call__(self, **kwargs) -> Any:
        """Execute the tool with given parameters."""
        return await self.execute(**kwargs)

    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        """Execute the tool with given parameters."""

    def to_param(self) -> Dict:
        """Convert tool to function call format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


# 工具执行结果模型
# 功能：
# 1. 统一的结果表示（输出、错误、系统信息）
# 2. 支持结果组合和运算
# 3. 提供结果替换和更新机制
class ToolResult(BaseModel):
    """Represents the result of a tool execution."""

    output: Any = Field(default=None)
    error: Optional[str] = Field(default=None)
    system: Optional[str] = Field(default=None)

    class Config:
        arbitrary_types_allowed = True

    def __bool__(self):
        return any(getattr(self, field) for field in self.__fields__)

    def __add__(self, other: "ToolResult"):
        def combine_fields(
            field: Optional[str], other_field: Optional[str], concatenate: bool = True
        ):
            if field and other_field:
                if concatenate:
                    return field + other_field
                raise ValueError("Cannot combine tool results")
            return field or other_field

        return ToolResult(
            output=combine_fields(self.output, other.output),
            error=combine_fields(self.error, other.error),
            system=combine_fields(self.system, other.system),
        )

    def __str__(self):
        return f"Error: {self.error}" if self.error else self.output

    def replace(self, **kwargs):
        """Returns a new ToolResult with the given fields replaced."""
        # return self.copy(update=kwargs)
        return type(self)(**{**self.dict(), **kwargs})


# 命令行工具结果
# 说明：专门用于CLI输出的结果类型
class CLIResult(ToolResult):
    """A ToolResult that can be rendered as a CLI output."""


# 工具执行失败结果
# 说明：表示工具执行失败的专用结果类型
class ToolFailure(ToolResult):
    """A ToolResult that represents a failure."""


# Agent感知工具基类
# 说明：支持与Agent交互的工具基类
class AgentAwareTool:
    agent: Optional = None
