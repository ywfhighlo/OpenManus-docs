# 软件工程代理模块
# 实现专门用于编程和代码操作的代理，拥有执行命令、编辑文件等能力
from typing import List

from pydantic import Field

from app.agent.toolcall import ToolCallAgent
from app.prompt.swe import NEXT_STEP_TEMPLATE, SYSTEM_PROMPT
from app.tool import Bash, StrReplaceEditor, Terminate, ToolCollection


# 软件工程代理，继承自ToolCallAgent，提供编码和开发任务辅助
class SWEAgent(ToolCallAgent):
    """An agent that implements the SWEAgent paradigm for executing code and natural conversations."""

    name: str = "swe"
    description: str = "an autonomous AI programmer that interacts directly with the computer to solve tasks."

    system_prompt: str = SYSTEM_PROMPT
    next_step_prompt: str = NEXT_STEP_TEMPLATE

    # 可用工具集合，包括命令行、文本编辑和终止操作
    available_tools: ToolCollection = ToolCollection(
        Bash(), StrReplaceEditor(), Terminate()
    )
    special_tool_names: List[str] = Field(default_factory=lambda: [Terminate().name])

    max_steps: int = 30

    # Bash工具实例和工作目录记录
    bash: Bash = Field(default_factory=Bash)
    working_dir: str = "."

    # 重写think方法：在调用父类思考逻辑前，先通过`pwd`命令获取并更新当前工作目录，
    # 并将其注入到下一步的提示模板中。
    async def think(self) -> bool:
        """Process current state and decide next action"""
        # Update working directory
        result = await self.bash.execute("pwd")
        self.working_dir = result.output
        self.next_step_prompt = self.next_step_prompt.format(
            current_dir=self.working_dir
        )

        return await super().think()
