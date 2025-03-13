from typing import Any

from pydantic import Field

from app.agent.toolcall import ToolCallAgent
from app.prompt.manus import NEXT_STEP_PROMPT, SYSTEM_PROMPT
from app.tool import Terminate, ToolCollection
from app.tool.browser_use_tool import BrowserUseTool
from app.tool.file_saver import FileSaver
from app.tool.google_search import GoogleSearch
from app.tool.python_execute import PythonExecute


class Manus(ToolCallAgent):
    """
    A versatile general-purpose agent that uses planning to solve various tasks.

    This agent extends PlanningAgent with a comprehensive set of tools and capabilities,
    including Python execution, web browsing, file operations, and information retrieval
    to handle a wide range of user requests.
    
    通用智能体实现
    
    核心特性：
    1. 多工具支持：集成多种工具，提供全面的任务处理能力
    2. 规划能力：继承自PlanningAgent，支持任务分解和规划
    3. 工具调用：基于ToolCallAgent实现工具的统一调用
    4. 扩展性强：支持动态添加和配置新工具
    5. 安全可控：内置执行限制和终止机制
    """

    name: str = "Manus"
    description: str = (
        "A versatile agent that can solve various tasks using multiple tools"
    )

    # 提示词配置
    # 设计说明：
    # 1. 系统提示词：定义Agent的基本角色和行为准则
    # 2. 步骤提示词：指导Agent进行任务规划和执行
    # 3. 继承自模板：使用预定义的提示词模板确保一致性
    system_prompt: str = SYSTEM_PROMPT
    next_step_prompt: str = NEXT_STEP_PROMPT

    max_observe: int = 2000
    max_steps: int = 20

    # Add general-purpose tools to the tool collection
    available_tools: ToolCollection = Field(
        default_factory=lambda: ToolCollection(
            PythonExecute(), GoogleSearch(), BrowserUseTool(), FileSaver(), Terminate()
        )
    )

    async def _handle_special_tool(self, name: str, result: Any, **kwargs):
        await self.available_tools.get_tool(BrowserUseTool().name).cleanup()
        await super()._handle_special_tool(name, result, **kwargs)
