# ReAct代理模块
# 实现思考-行动循环模式的代理，将代理决策过程分为独立的思考和行动阶段
from abc import ABC, abstractmethod
from typing import Optional

from pydantic import Field

from app.agent.base import BaseAgent
from app.llm import LLM
from app.schema import AgentState, Memory


# 实现ReAct（思考-行动）模式的代理基类，子类需实现think和act方法
class ReActAgent(BaseAgent, ABC):
    name: str
    description: Optional[str] = None

    system_prompt: Optional[str] = None
    next_step_prompt: Optional[str] = None

    llm: Optional[LLM] = Field(default_factory=LLM)
    memory: Memory = Field(default_factory=Memory)
    state: AgentState = AgentState.IDLE

    max_steps: int = 10
    current_step: int = 0

    # 思考阶段：分析当前状态并决定下一步行动
    @abstractmethod
    async def think(self) -> bool:
        """Process current state and decide next action"""

    # 行动阶段：执行决定的行动
    @abstractmethod
    async def act(self) -> str:
        """Execute decided actions"""

    # 执行单个步骤，包括思考和行动两个阶段
    async def step(self) -> str:
        """Execute a single step: think and act."""
        should_act = await self.think()
        if not should_act:
            return "Thinking complete - no action needed"
        return await self.act()
