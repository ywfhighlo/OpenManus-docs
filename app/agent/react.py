# ReAct模式实现模块
# 设计说明：
# 1. 思考-行动模式：实现ReAct（Reasoning and Acting）范式
# 2. 抽象接口：定义统一的思考和行动接口
# 3. 状态管理：继承BaseAgent的状态管理能力
# 4. 异步支持：全异步设计提升性能
# 5. 扩展性强：支持多种具体实现策略

from abc import ABC, abstractmethod
from typing import Optional

from pydantic import Field

from app.agent.base import BaseAgent
from app.llm import LLM
from app.schema import AgentState, Memory


class ReActAgent(BaseAgent, ABC):
    """
    ReAct模式Agent基类
    
    核心特性：
    1. 双阶段执行：将Agent行为分解为思考和行动两个阶段
    2. 抽象设计：提供统一接口，支持不同的实现策略
    3. 状态管理：继承BaseAgent的状态转换机制
    4. 内存系统：维护对话历史和执行上下文
    5. 异步执行：支持复杂的推理和行动过程
    """

    name: str
    description: Optional[str] = None

    # 提示词配置
    # 设计说明：
    # 1. 系统提示词：定义Agent的基本行为准则
    # 2. 步骤提示词：指导每一步的决策过程
    # 3. 可选性：允许子类根据需要设置提示词
    system_prompt: Optional[str] = None
    next_step_prompt: Optional[str] = None

    # 核心组件
    # 设计说明：
    # 1. 语言模型：处理自然语言的核心组件
    # 2. 记忆系统：存储和管理对话历史
    # 3. 状态管理：控制Agent的执行状态
    llm: Optional[LLM] = Field(default_factory=LLM)
    memory: Memory = Field(default_factory=Memory)
    state: AgentState = AgentState.IDLE

    # 执行控制参数
    # 设计说明：
    # 1. 步数限制：防止无限循环执行
    # 2. 进度追踪：记录当前执行步骤
    # 3. 可配置性：支持子类调整限制
    max_steps: int = 10
    current_step: int = 0

    @abstractmethod
    async def think(self) -> bool:
        """
        Process current state and decide next action
        
        思考阶段抽象方法
        
        功能要求：
        1. 状态分析：处理当前状态信息
        2. 决策制定：确定下一步行动
        3. 结果指示：返回是否需要执行行动
        4. 异步处理：支持复杂的推理过程
        
        返回值：
        - True: 需要执行行动
        - False: 不需要执行行动
        """

    @abstractmethod
    async def act(self) -> str:
        """
        Execute decided actions
        
        行动阶段抽象方法
        
        功能要求：
        1. 行动执行：实现具体的行动逻辑
        2. 结果生成：返回执行的结果描述
        3. 异步支持：处理耗时的操作
        4. 错误处理：妥善处理执行异常
        
        返回值：
        - 字符串形式的执行结果描述
        """

    async def step(self) -> str:
        """
        Execute a single step: think and act.
        
        单步执行实现
        
        执行流程：
        1. 思考阶段：调用think()方法进行决策
        2. 判断阶段：根据思考结果决定是否行动
        3. 行动阶段：如需要则执行act()方法
        4. 结果返回：提供执行的结果描述
        
        返回值：
        - 执行结果的文本描述
        - 如果不需要行动，返回思考完成的提示
        """
        should_act = await self.think()
        if not should_act:
            return "Thinking complete - no action needed"
        return await self.act()
