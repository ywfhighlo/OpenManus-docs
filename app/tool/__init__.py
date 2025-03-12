# 工具系统模块初始化
# 设计说明：
# 1. 导出所有工具类
# 2. 提供统一的工具访问接口
# 3. 管理工具依赖关系

# 基础组件导入
from app.tool.base import BaseTool  # 工具基类
from app.tool.bash import Bash  # Bash命令执行工具
from app.tool.create_chat_completion import CreateChatCompletion  # 聊天补全工具
from app.tool.planning import PlanningTool  # 规划工具
from app.tool.str_replace_editor import StrReplaceEditor  # 字符串替换编辑器
from app.tool.terminate import Terminate  # 终止工具
from app.tool.tool_collection import ToolCollection  # 工具集合管理器


# 导出工具列表
# 包含：
# - BaseTool: 工具基类
# - Bash: 命令执行工具
# - Terminate: 终止工具
# - StrReplaceEditor: 字符串编辑工具
# - ToolCollection: 工具集合
# - CreateChatCompletion: 聊天补全工具
# - PlanningTool: 规划工具
__all__ = [
    "BaseTool",
    "Bash",
    "Terminate",
    "StrReplaceEditor",
    "ToolCollection",
    "CreateChatCompletion",
    "PlanningTool",
]
