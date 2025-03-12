# 数据模型定义模块
# 设计说明：
# 1. 定义系统核心数据结构
# 2. 实现消息和工具调用模型
# 3. 提供类型安全的数据验证
# 4. 支持消息历史管理
# 5. 基于Pydantic实现模型验证

from enum import Enum
from typing import Any, List, Literal, Optional, Union

from pydantic import BaseModel, Field


class AgentState(str, Enum):
    """
    Agent execution states
    
    Agent执行状态枚举
    
    状态说明：
    - IDLE: 空闲状态，等待任务
    - RUNNING: 运行状态，正在执行任务
    - FINISHED: 完成状态，任务执行完毕
    - ERROR: 错误状态，执行出现异常
    """

    IDLE = "IDLE"
    RUNNING = "RUNNING"
    FINISHED = "FINISHED"
    ERROR = "ERROR"


class Function(BaseModel):
    """
    函数调用模型
    
    功能：
    1. 定义函数名称和参数
    2. 用于工具调用的函数描述
    """
    name: str
    arguments: str


class ToolCall(BaseModel):
    """
    Represents a tool/function call in a message
    
    工具调用模型
    
    功能：
    1. 工具标识：唯一ID和类型
    2. 函数封装：包含具体的函数调用信息
    3. 支持序列化：便于消息传递
    """

    id: str
    type: str = "function"
    function: Function


class Message(BaseModel):
    """
    Represents a chat message in the conversation
    
    消息模型
    
    功能特性：
    1. 角色定义：支持system/user/assistant/tool
    2. 内容管理：支持文本内容和工具调用
    3. 工具集成：支持工具调用相关字段
    4. 运算符重载：支持消息列表操作
    5. 格式转换：支持字典格式转换
    """

    role: Literal["system", "user", "assistant", "tool"] = Field(...)
    content: Optional[str] = Field(default=None)
    tool_calls: Optional[List[ToolCall]] = Field(default=None)
    name: Optional[str] = Field(default=None)
    tool_call_id: Optional[str] = Field(default=None)

    def __add__(self, other) -> List["Message"]:
        """
        支持 Message + list 或 Message + Message 的操作
        
        功能：
        1. 消息合并：支持消息与列表的合并
        2. 类型检查：确保操作数类型正确
        """
        if isinstance(other, list):
            return [self] + other
        elif isinstance(other, Message):
            return [self, other]
        else:
            raise TypeError(
                f"unsupported operand type(s) for +: '{type(self).__name__}' and '{type(other).__name__}'"
            )

    def __radd__(self, other) -> List["Message"]:
        """
        支持 list + Message 的操作
        
        功能：
        1. 反向合并：支持列表与消息的合并
        2. 类型验证：确保操作数为列表类型
        """
        if isinstance(other, list):
            return other + [self]
        else:
            raise TypeError(
                f"unsupported operand type(s) for +: '{type(other).__name__}' and '{type(self).__name__}'"
            )

    def to_dict(self) -> dict:
        """
        Convert message to dictionary format
        
        消息转换为字典格式
        
        功能：
        1. 字段选择：仅包含非空字段
        2. 格式转换：工具调用的序列化
        3. 数据验证：确保输出格式正确
        """
        message = {"role": self.role}
        if self.content is not None:
            message["content"] = self.content
        if self.tool_calls is not None:
            message["tool_calls"] = [tool_call.dict() for tool_call in self.tool_calls]
        if self.name is not None:
            message["name"] = self.name
        if self.tool_call_id is not None:
            message["tool_call_id"] = self.tool_call_id
        return message

    @classmethod
    def user_message(cls, content: str) -> "Message":
        """
        Create a user message
        
        创建用户消息
        
        功能：快速创建用户角色的消息实例
        """
        return cls(role="user", content=content)

    @classmethod
    def system_message(cls, content: str) -> "Message":
        """
        Create a system message
        
        创建系统消息
        
        功能：快速创建系统角色的消息实例
        """
        return cls(role="system", content=content)

    @classmethod
    def assistant_message(cls, content: Optional[str] = None) -> "Message":
        """
        Create an assistant message
        
        创建助手消息
        
        功能：快速创建助手角色的消息实例
        """
        return cls(role="assistant", content=content)

    @classmethod
    def tool_message(cls, content: str, name, tool_call_id: str) -> "Message":
        """
        Create a tool message
        
        创建工具消息
        
        功能：
        1. 工具响应：创建工具执行结果消息
        2. 关联调用：通过ID关联对应的工具调用
        """
        return cls(role="tool", content=content, name=name, tool_call_id=tool_call_id)

    @classmethod
    def from_tool_calls(
        cls, tool_calls: List[Any], content: Union[str, List[str]] = "", **kwargs
    ):
        """
        Create ToolCallsMessage from raw tool calls.

        Args:
            tool_calls: Raw tool calls from LLM
            content: Optional message content
            
        工具调用消息创建
        
        功能：
        1. 调用转换：将原始工具调用转换为消息格式
        2. 格式规范：确保工具调用格式符合要求
        3. 内容整合：支持文本内容和工具调用的组合
        """
        formatted_calls = [
            {"id": call.id, "function": call.function.model_dump(), "type": "function"}
            for call in tool_calls
        ]
        return cls(
            role="assistant", content=content, tool_calls=formatted_calls, **kwargs
        )


class Memory(BaseModel):
    """
    消息历史管理
    
    功能特性：
    1. 消息存储：管理对话历史消息
    2. 容量控制：限制最大消息数量
    3. 批量操作：支持批量消息添加
    4. 查询功能：支持最近消息查询
    """
    messages: List[Message] = Field(default_factory=list)
    max_messages: int = Field(default=100)

    def add_message(self, message: Message) -> None:
        """
        Add a message to memory
        
        添加单条消息
        
        功能：
        1. 消息追加：添加新消息到历史
        2. 容量管理：确保不超过最大限制
        """
        self.messages.append(message)
        # Optional: Implement message limit
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages :]

    def add_messages(self, messages: List[Message]) -> None:
        """
        Add multiple messages to memory
        
        批量添加消息
        
        功能：支持多条消息同时添加到历史
        """
        self.messages.extend(messages)

    def clear(self) -> None:
        """
        Clear all messages
        
        清空消息历史
        
        功能：完全清除所有历史消息
        """
        self.messages.clear()

    def get_recent_messages(self, n: int) -> List[Message]:
        """
        Get n most recent messages
        
        获取最近消息
        
        功能：获取指定数量的最新消息
        """
        return self.messages[-n:]

    def to_dict_list(self) -> List[dict]:
        """
        Convert messages to list of dicts
        
        转换为字典列表
        
        功能：将所有消息转换为字典格式列表
        """
        return [msg.to_dict() for msg in self.messages]
