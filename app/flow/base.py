# 流程控制基础模块
# 设计说明：
# 1. 流程抽象：定义流程控制的核心接口和基类
# 2. 状态管理：实现完整的流程状态管理机制
# 3. Agent协作：支持多Agent的协同工作模式
# 4. 扩展支持：提供灵活的流程类型扩展机制
# 5. 工具集成：统一的工具集成和管理接口

from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, List, Optional, Union

from pydantic import BaseModel

from app.agent.base import BaseAgent


class FlowType(str, Enum):
    """
    Flow type enumeration
    
    流程类型枚举
    
    设计说明：
    1. 类型定义：使用字符串枚举确保序列化友好
    2. 当前支持：规划流程（PLANNING）类型
    3. 扩展性：预留其他流程类型的扩展空间
    4. 序列化：支持JSON序列化和反序列化
    """
    PLANNING = "planning"  # 规划流程类型


class BaseFlow(BaseModel, ABC):
    """
    Base class for execution flows supporting multiple agents
    
    流程控制基类
    
    核心功能：
    1. 多Agent管理：支持多个Agent的注册和协作
    2. 状态维护：管理流程的执行状态和进度
    3. 工具集成：统一的工具访问和调用接口
    4. 执行控制：异步执行和结果处理机制
    5. 扩展支持：提供子类实现的抽象接口
    """

    # 核心属性
    # 设计说明：
    # 1. agents: 
    #    - Agent注册表，支持命名访问
    #    - 维护Agent间的依赖关系
    #    - 支持动态添加和移除
    # 2. tools:
    #    - 可选的工具列表配置
    #    - 支持全局工具共享
    #    - 运行时工具注册
    # 3. primary_agent_key:
    #    - 主Agent的标识符
    #    - 控制执行流程的主体
    #    - 支持动态切换
    agents: Dict[str, BaseAgent]
    tools: Optional[List] = None
    primary_agent_key: Optional[str] = None

    class Config:
        """
        配置类
        
        设置说明：
        1. 类型支持：允许任意类型，支持复杂对象
        2. 扩展性：为子类预留扩展空间
        3. 序列化：确保所有属性可序列化
        """
        arbitrary_types_allowed = True

    def __init__(
        self, agents: Union[BaseAgent, List[BaseAgent], Dict[str, BaseAgent]], **data
    ):
        """
        Initialize flow with agents and additional data
        
        初始化方法
        
        实现说明：
        1. 多模式支持：
           - 单Agent模式：自动设置为default
           - 列表模式：自动编号为agent_0, agent_1...
           - 字典模式：使用提供的键值对
        2. 主Agent设置：
           - 优先使用指定的primary_agent_key
           - 默认使用第一个Agent作为主Agent
        3. 状态初始化：
           - 设置初始的Agent字典
           - 处理额外的配置参数
        """
        # Handle different ways of providing agents
        if isinstance(agents, BaseAgent):
            agents_dict = {"default": agents}
        elif isinstance(agents, list):
            agents_dict = {f"agent_{i}": agent for i, agent in enumerate(agents)}
        else:
            agents_dict = agents

        # If primary agent not specified, use first agent
        primary_key = data.get("primary_agent_key")
        if not primary_key and agents_dict:
            primary_key = next(iter(agents_dict))
            data["primary_agent_key"] = primary_key

        # Set the agents dictionary
        data["agents"] = agents_dict

        # Initialize using BaseModel's init
        super().__init__(**data)

    @property
    def primary_agent(self) -> Optional[BaseAgent]:
        """
        Get the primary agent for the flow
        
        主Agent访问器
        
        功能说明：
        1. 便捷访问：提供主Agent的直接访问方式
        2. 空值处理：返回Optional表示可能不存在
        3. 只读属性：防止意外修改主Agent
        4. 实时获取：每次访问都获取最新的Agent
        """
        return self.agents.get(self.primary_agent_key)

    def get_agent(self, key: str) -> Optional[BaseAgent]:
        """
        Get a specific agent by key
        
        Agent获取方法
        
        功能说明：
        1. 安全访问：不存在时返回None
        2. 键值验证：通过key精确定位Agent
        3. 类型保证：返回BaseAgent类型
        4. 运行时访问：支持动态Agent查找
        """
        return self.agents.get(key)

    def add_agent(self, key: str, agent: BaseAgent) -> None:
        """
        Add a new agent to the flow
        
        Agent添加方法
        
        功能说明：
        1. 动态注册：运行时添加新Agent
        2. 键值唯一：使用key作为唯一标识
        3. 类型检查：确保agent是BaseAgent实例
        4. 状态更新：自动更新Agent注册表
        """
        self.agents[key] = agent

    @abstractmethod
    async def execute(self, input_text: str) -> str:
        """
        Execute the flow with given input
        
        流程执行接口
        
        设计要求：
        1. 异步执行：支持长时间运行的任务
        2. 输入处理：统一的文本输入接口
        3. 结果返回：标准化的字符串输出
        4. 错误处理：完善的异常捕获机制
        """


class PlanStepStatus(str, Enum):
    """
    Enum class defining possible statuses of a plan step
    
    计划步骤状态枚举
    
    设计说明：
    1. 状态定义：完整覆盖所有可能的步骤状态
    2. 可视化：为每个状态提供直观的标记符号
    3. 分组管理：支持状态的分类和过滤
    4. 序列化：使用字符串值确保兼容性
    """

    NOT_STARTED = "not_started"  # 未开始：步骤尚未启动
    IN_PROGRESS = "in_progress"  # 进行中：步骤正在执行
    COMPLETED = "completed"      # 已完成：步骤已成功完成
    BLOCKED = "blocked"          # 被阻塞：步骤执行受阻

    @classmethod
    def get_all_statuses(cls) -> list[str]:
        """
        Return a list of all possible step status values
        
        获取所有状态值
        
        功能说明：
        1. 状态枚举：返回所有可能的状态值
        2. 值提取：获取状态的字符串表示
        3. 列表格式：返回字符串列表
        4. 动态更新：反映枚举的最新定义
        """
        return [status.value for status in cls]

    @classmethod
    def get_active_statuses(cls) -> list[str]:
        """
        Return a list of values representing active statuses (not started or in progress)
        
        获取活动状态值
        
        功能说明：
        1. 活动状态：未开始或进行中的状态
        2. 状态过滤：只返回活动相关的状态
        3. 值提取：获取状态的字符串表示
        4. 使用场景：用于查找需要处理的步骤
        """
        return [cls.NOT_STARTED.value, cls.IN_PROGRESS.value]

    @classmethod
    def get_status_marks(cls) -> Dict[str, str]:
        """
        Return a mapping of statuses to their marker symbols
        
        获取状态标记映射
        
        功能说明：
        1. 可视化：为每个状态提供直观的标记
        2. 映射关系：状态值到标记符号的对应
        3. 标记设计：使用Unicode字符增强可读性
        4. 使用场景：用于计划的可视化展示
        """
        return {
            cls.COMPLETED.value: "[✓]",    # 完成标记：表示步骤已完成
            cls.IN_PROGRESS.value: "[→]",  # 进行中标记：表示步骤正在执行
            cls.BLOCKED.value: "[!]",      # 阻塞标记：表示步骤被阻塞
            cls.NOT_STARTED.value: "[ ]",  # 未开始标记：表示步骤尚未启动
        }
