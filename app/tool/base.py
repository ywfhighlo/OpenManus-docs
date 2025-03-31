# 工具基础模块
# 定义工具的抽象基类和结果类，提供统一的工具调用和结果处理机制
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


# 工具基类，所有具体工具都继承自此类
class BaseTool(ABC, BaseModel):
    name: str
    description: str
    parameters: Optional[dict] = None

    class Config:
        arbitrary_types_allowed = True

    # 允许工具实例直接作为函数调用
    async def __call__(self, **kwargs) -> Any:
        """Execute the tool with given parameters."""
        return await self.execute(**kwargs)

    # 抽象方法，具体工具必须实现此方法
    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        """Execute the tool with given parameters."""

    # 转换为API函数调用格式
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


# 工具执行结果模型，表示工具调用的输出
class ToolResult(BaseModel):
    """Represents the result of a tool execution."""

    output: Any = Field(default=None)
    error: Optional[str] = Field(default=None)
    base64_image: Optional[str] = Field(default=None)
    system: Optional[str] = Field(default=None)

    class Config:
        arbitrary_types_allowed = True

    # 检查结果是否有任何内容
    def __bool__(self):
        return any(getattr(self, field) for field in self.__fields__)

    # 合并两个工具结果
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
            base64_image=combine_fields(self.base64_image, other.base64_image, False),
            system=combine_fields(self.system, other.system),
        )

    # 转换为字符串，优先显示错误信息
    def __str__(self):
        return f"Error: {self.error}" if self.error else self.output

    # 创建一个字段更新后的新结果对象
    def replace(self, **kwargs):
        """Returns a new ToolResult with the given fields replaced."""
        # return self.copy(update=kwargs)
        return type(self)(**{**self.dict(), **kwargs})


# 命令行输出结果，可格式化为终端友好的显示
class CLIResult(ToolResult):
    """A ToolResult that can be rendered as a CLI output."""


# 工具执行失败结果，专门表示错误情况
class ToolFailure(ToolResult):
    """A ToolResult that represents a failure."""
