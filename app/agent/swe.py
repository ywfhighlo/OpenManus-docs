# 软件工程专用Agent模块
# 设计说明：
# 1. 专业能力：实现面向软件工程的智能助手
# 2. 系统交互：直接与计算机系统交互，执行代码和命令
# 3. 工程实践：遵循软件工程最佳实践和设计模式
# 4. 工具集成：提供完整的开发工具链支持
# 5. 环境感知：实时追踪并维护工作环境上下文

from typing import List

from pydantic import Field

from app.agent.toolcall import ToolCallAgent
from app.prompt.swe import NEXT_STEP_TEMPLATE, SYSTEM_PROMPT
from app.tool import Bash, StrReplaceEditor, Terminate, ToolCollection


class SWEAgent(ToolCallAgent):
    """
    An agent that implements the SWEAgent paradigm for executing code and natural conversations.
    
    软件工程专用Agent
    
    核心特性：
    1. 专业能力：具备软件开发和工程实践的专业知识
    2. 工具链集成：提供完整的开发工具支持
    3. 环境感知：实时追踪工作目录和项目状态
    4. 代码处理：支持代码编写、修改和版本控制
    5. 命令执行：直接执行系统命令和开发工具
    """

    name: str = "swe"
    description: str = "an autonomous AI programmer that interacts directly with the computer to solve tasks."

    # 提示词配置
    # 设计说明：
    # 1. 系统提示词：定义Agent的软件工程专业知识和行为准则
    # 2. 步骤提示词：包含工作目录信息的动态模板
    # 3. 上下文感知：提示词会根据当前环境动态更新
    system_prompt: str = SYSTEM_PROMPT
    next_step_prompt: str = NEXT_STEP_TEMPLATE

    # 工具配置
    # 核心工具集：
    # 1. Bash: 执行系统命令和开发工具
    # 2. StrReplaceEditor: 代码编辑和文本处理
    # 3. Terminate: 任务控制和终止机制
    #
    # 工具选择原则：
    # 1. 开发必要：满足基本的开发工作需求
    # 2. 安全可控：限制潜在的危险操作
    # 3. 效率优先：优化常见开发任务的执行
    available_tools: ToolCollection = ToolCollection(
        Bash(), StrReplaceEditor(), Terminate()
    )
    special_tool_names: List[str] = Field(default_factory=lambda: [Terminate().name])

    # 执行控制
    # 设计说明：
    # 1. 步数限制：考虑开发任务的复杂性
    # 2. 超时保护：防止长时间阻塞
    # 3. 资源控制：确保执行效率
    max_steps: int = 30

    # 环境配置
    # 设计说明：
    # 1. 命令行工具：统一的命令执行接口
    # 2. 工作目录：实时追踪的环境上下文
    # 3. 状态维护：确保操作的连续性
    bash: Bash = Field(default_factory=Bash)
    working_dir: str = "."

    async def think(self) -> bool:
        """
        Process current state and decide next action
        
        思考阶段实现
        
        执行流程：
        1. 环境更新：获取最新的工作目录
        2. 提示更新：将环境信息注入提示模板
        3. 决策制定：调用父类的思考逻辑
        4. 状态维护：确保环境信息的一致性
        
        返回值：
        - True: 需要执行行动
        - False: 不需要执行行动
        """
        # Update working directory
        self.working_dir = await self.bash.execute("pwd")
        self.next_step_prompt = self.next_step_prompt.format(
            current_dir=self.working_dir
        )

        return await super().think()
