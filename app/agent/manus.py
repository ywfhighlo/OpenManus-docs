# Manus Agent模块
# 设计说明：
# 1. 通用智能体：实现多功能、可扩展的Agent系统
# 2. 工具集成：提供丰富的工具支持，包括代码执行、网络访问等
# 3. 任务处理：支持复杂任务的规划和执行
# 4. 安全控制：实现执行限制和终止机制
# 5. 状态管理：继承基类的状态管理能力

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

    # 工具集配置
    # 核心工具组合：
    # 1. PythonExecute: 执行Python代码，支持本地计算
    # 2. GoogleSearch: 获取网络信息，扩展知识范围
    # 3. BrowserUseTool: 模拟浏览器操作，支持复杂网页交互
    # 4. FileSaver: 文件操作，持久化数据存储
    # 5. Terminate: 安全终止机制，防止无限执行
    #
    # 工具选择原则：
    # 1. 功能互补：每个工具负责特定领域的任务
    # 2. 安全可控：所有工具都有明确的权限和限制
    # 3. 易于扩展：支持通过ToolCollection动态添加工具
    available_tools: ToolCollection = Field(
        default_factory=lambda: ToolCollection(
            PythonExecute(), GoogleSearch(), BrowserUseTool(), FileSaver(), Terminate()
        )
    )

    # 执行控制参数
    # 设计考虑：
    # 1. 步数限制：设置为20步，平衡执行效率和任务复杂度
    # 2. 超时保护：防止任务无限执行
    # 3. 资源控制：确保单个任务不会占用过多资源
    max_steps: int = 20
