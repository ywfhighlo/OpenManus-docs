# 任务终止工具模块
# 设计说明：
# 1. 提供任务终止机制
# 2. 支持成功/失败状态
# 3. 统一的终止流程

from app.tool.base import BaseTool


# 终止工具描述
# 说明：当任务完成或无法继续时终止交互
_TERMINATE_DESCRIPTION = """Terminate the interaction when the request is met OR if the assistant cannot proceed further with the task."""


# 终止工具类
# 功能特性：
# 1. 支持任务状态标记
# 2. 提供清晰的终止信息
# 3. 统一的终止接口
class Terminate(BaseTool):
    name: str = "terminate"
    description: str = _TERMINATE_DESCRIPTION
    # 工具参数定义
    # 必需参数：
    # - status: 终止状态（success/failure）
    parameters: dict = {
        "type": "object",
        "properties": {
            "status": {
                "type": "string",
                "description": "The finish status of the interaction.",
                "enum": ["success", "failure"],
            }
        },
        "required": ["status"],
    }

    async def execute(self, status: str) -> str:
        """Finish the current execution"""
        return f"The interaction has been completed with status: {status}"
