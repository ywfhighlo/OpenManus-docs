# Agent系统基础模块
# 设计说明：
# 1. 基类定义：提供Agent系统的核心抽象接口
# 2. 状态管理：实现有限状态机模式
# 3. 内存系统：管理对话历史和上下文
# 4. 执行控制：支持异步操作和步骤执行
# 5. 错误处理：提供完整的异常处理机制

from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from typing import List, Optional

from pydantic import BaseModel, Field, model_validator

from app.llm import LLM
from app.logger import logger
from app.schema import AgentState, Memory, Message, ROLE_TYPE


class BaseAgent(BaseModel, ABC):
    """
    Abstract base class for managing agent state and execution.

    Provides foundational functionality for state transitions, memory management,
    and a step-based execution loop. Subclasses must implement the `step` method.
    
    Agent基础抽象类
    
    核心功能：
    1. 状态转换：管理Agent的生命周期状态
    2. 内存管理：维护对话历史和上下文信息
    3. 步骤执行：提供基于步骤的执行循环框架
    4. 错误处理：实现异常捕获和状态恢复机制
    5. 消息处理：统一的消息创建和存储接口
    """

    # Core attributes
    # 核心属性定义：
    # - name: Agent的唯一标识符，用于配置和日志
    # - description: 可选的描述信息，用于文档和调试
    name: str = Field(..., description="Unique name of the agent")
    description: Optional[str] = Field(None, description="Optional agent description")

    # Prompts
    # 提示词系统设计：
    # - system_prompt: 定义Agent的角色和全局行为准则
    # - next_step_prompt: 控制Agent的决策流程和行动方向
    system_prompt: Optional[str] = Field(
        None, description="System-level instruction prompt"
    )
    next_step_prompt: Optional[str] = Field(
        None, description="Prompt for determining next action"
    )

    # Dependencies
    # 核心依赖组件：
    # - llm: 语言模型接口，支持不同模型的无缝切换
    # - memory: 记忆存储，维护对话历史和上下文
    # - state: 状态管理，控制Agent的生命周期
    llm: LLM = Field(default_factory=LLM, description="Language model instance")
    memory: Memory = Field(default_factory=Memory, description="Agent's memory store")
    state: AgentState = Field(
        default=AgentState.IDLE, description="Current agent state"
    )

    # Execution control
    # 执行控制参数：
    # - max_steps: 防止无限循环的安全机制
    # - current_step: 追踪执行进度
    # - duplicate_threshold: 检测重复响应的阈值，用于发现Agent卡住的情况
    max_steps: int = Field(default=10, description="Maximum steps before termination")
    current_step: int = Field(default=0, description="Current step in execution")
    duplicate_threshold: int = 2

    class Config:
        """
        配置类
        
        设置：
        1. 允许任意类型：支持复杂对象的序列化
        2. 允许额外字段：为子类提供扩展性
        """
        arbitrary_types_allowed = True
        extra = "allow"  # Allow extra fields for flexibility in subclasses

    @model_validator(mode="after")
    def initialize_agent(self) -> "BaseAgent":
        """
        Initialize agent with default settings if not provided.
        
        Agent初始化验证器
        
        功能：
        1. 配置验证：确保必要组件已正确初始化
        2. 默认值设置：提供组件的默认实现
        3. 实例关联：建立组件间的关联关系
        """
        if self.llm is None or not isinstance(self.llm, LLM):
            self.llm = LLM(config_name=self.name.lower())
        if not isinstance(self.memory, Memory):
            self.memory = Memory()
        return self

    @asynccontextmanager
    async def state_context(self, new_state: AgentState):
        """
        Context manager for safe agent state transitions.

        Args:
            new_state: The state to transition to during the context.

        Yields:
            None: Allows execution within the new state.

        Raises:
            ValueError: If the new_state is invalid.
            
        状态上下文管理器
        
        实现原理：
        1. 状态保护：使用上下文管理器确保状态转换的安全性
        2. 异常处理：捕获执行异常并转换到错误状态
        3. 状态恢复：确保在退出时恢复到之前的状态
        4. 原子性：保证状态转换操作的原子性
        """
        if not isinstance(new_state, AgentState):
            raise ValueError(f"Invalid state: {new_state}")

        previous_state = self.state
        self.state = new_state
        try:
            yield
        except Exception as e:
            self.state = AgentState.ERROR  # Transition to ERROR on failure
            raise e
        finally:
            self.state = previous_state  # Revert to previous state

    def update_memory(
        self,
        role: ROLE_TYPE, # type: ignore
        content: str,
        **kwargs,
    ) -> None:
        """
        Add a message to the agent's memory.

        Args:
            role: The role of the message sender (user, system, assistant, tool).
            content: The message content.
            **kwargs: Additional arguments (e.g., tool_call_id for tool messages).

        Raises:
            ValueError: If the role is unsupported.
            
        内存更新机制
        
        实现特性：
        1. 工厂模式：使用消息工厂创建不同类型的消息
        2. 角色验证：确保消息角色的有效性
        3. 灵活扩展：支持额外参数的传递
        4. 类型安全：确保消息格式的一致性
        """
        message_map = {
            "user": Message.user_message,
            "system": Message.system_message,
            "assistant": Message.assistant_message,
            "tool": lambda content, **kw: Message.tool_message(content, **kw),
        }

        if role not in message_map:
            raise ValueError(f"Unsupported message role: {role}")

        msg_factory = message_map[role]
        msg = msg_factory(content, **kwargs) if role == "tool" else msg_factory(content)
        self.memory.add_message(msg)

    async def run(self, request: Optional[str] = None) -> str:
        """
        Execute the agent's main loop asynchronously.

        Args:
            request: Optional initial user request to process.

        Returns:
            A string summarizing the execution results.

        Raises:
            RuntimeError: If the agent is not in IDLE state at start.
            
        主执行循环
        
        执行流程：
        1. 初始化：处理可选的用户请求
        2. 状态管理：使用上下文管理器控制执行状态
        3. 步骤执行：在最大步数内循环执行step()
        4. 监控检查：检测是否陷入重复状态
        5. 结果收集：记录每个步骤的执行结果
        """
        if self.state != AgentState.IDLE:
            raise RuntimeError(f"Cannot run agent from state: {self.state}")

        if request:
            self.update_memory("user", request)

        results: List[str] = []
        async with self.state_context(AgentState.RUNNING):
            while (
                self.current_step < self.max_steps and self.state != AgentState.FINISHED
            ):
                self.current_step += 1
                logger.info(f"Executing step {self.current_step}/{self.max_steps}")
                step_result = await self.step()

                # Check for stuck state
                if self.is_stuck():
                    self.handle_stuck_state()

                results.append(f"Step {self.current_step}: {step_result}")

            if self.current_step >= self.max_steps:
                self.current_step = 0
                self.state = AgentState.IDLE
                results.append(f"Terminated: Reached max steps ({self.max_steps})")

        return "\n".join(results) if results else "No steps executed"

    @abstractmethod
    async def step(self) -> str:
        """
        Execute a single step in the agent's workflow.

        Must be implemented by subclasses to define specific behavior.
        
        抽象步骤方法
        
        设计要求：
        1. 子类实现：必须由具体的Agent类实现
        2. 异步支持：支持异步操作的执行
        3. 结果返回：提供步骤执行的结果描述
        4. 状态更新：负责更新Agent的内部状态
        """

    def handle_stuck_state(self):
        """
        Handle stuck state by adding a prompt to change strategy
        
        卡住状态处理
        
        处理策略：
        1. 状态检测：识别Agent是否陷入重复状态
        2. 提示调整：添加提示以改变执行策略
        3. 记录日志：记录卡住状态的相关信息
        4. 恢复机制：尝试从卡住状态中恢复
        """
        logger.warning("Agent appears to be stuck in a loop, adding prompt to change strategy")
        self.update_memory(
            "system",
            "You seem to be stuck in a loop. Please try a different approach.",
        )

    def is_stuck(self) -> bool:
        """
        Check if the agent is stuck in a loop
        
        循环检测
        
        实现原理：
        1. 历史分析：检查最近的执行历史
        2. 阈值判断：使用duplicate_threshold判断重复次数
        3. 模式识别：识别重复的执行模式
        4. 性能优化：高效的重复检测算法
        """
        if len(self.memory.messages) < self.duplicate_threshold:
            return False

        # Get the last N messages where N is the duplicate threshold
        recent_messages = self.memory.messages[-self.duplicate_threshold:]
        
        # Check if all recent messages are identical
        return all(
            msg.content == recent_messages[0].content
            for msg in recent_messages[1:]
        )

    @property
    def messages(self) -> List[Message]:
        """
        Retrieve a list of messages from the agent's memory.
        
        消息访问器
        
        功能：提供对内存消息的只读访问
        """
        return self.memory.messages

    @messages.setter
    def messages(self, value: List[Message]):
        """
        Set the list of messages in the agent's memory.
        
        消息设置器
        
        功能：提供对内存消息的写入接口
        """
        self.memory.messages = value
