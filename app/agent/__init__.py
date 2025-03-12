# Agent系统模块初始化
# 设计说明：
# 1. 模块导出：统一导出所有Agent类
# 2. 依赖管理：处理模块间的依赖关系
# 3. 接口统一：提供统一的Agent访问接口
# 4. 版本控制：管理Agent系统的版本信息

# 基础组件导入
from app.agent.base import BaseAgent  # 基础Agent抽象类
from app.agent.planning import PlanningAgent  # 规划执行Agent
from app.agent.react import ReActAgent  # ReAct模式Agent
from app.agent.swe import SWEAgent  # 软件工程专用Agent
from app.agent.toolcall import ToolCallAgent  # 工具调用Agent

# 模块导出配置
# 说明：
# 1. BaseAgent: Agent系统的核心抽象基类
# 2. PlanningAgent: 实现任务规划和执行管理
# 3. ReActAgent: 实现思考-行动循环模式
# 4. SWEAgent: 专门用于软件工程任务
# 5. ToolCallAgent: 提供工具调用和管理功能
__all__ = [
    "BaseAgent",
    "PlanningAgent",
    "ReActAgent",
    "SWEAgent",
    "ToolCallAgent",
]
