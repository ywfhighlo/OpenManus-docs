# tool/planning.py
# 规划工具模块
# 设计说明：
# 1. 提供任务规划和管理功能
# 2. 支持计划的创建、更新和跟踪
# 3. 实现步骤状态管理
# 4. 多计划并行处理

from typing import Dict, List, Literal, Optional

from app.exceptions import ToolError
from app.tool.base import BaseTool, ToolResult


_PLANNING_TOOL_DESCRIPTION = """
A planning tool that allows the agent to create and manage plans for solving complex tasks.
The tool provides functionality for creating plans, updating plan steps, and tracking progress.
"""


class PlanningTool(BaseTool):
    """
    A planning tool that allows the agent to create and manage plans for solving complex tasks.
    The tool provides functionality for creating plans, updating plan steps, and tracking progress.
    
    规划工具类
    功能特性：
    1. 计划管理：创建、更新、列表、获取、删除计划
    2. 步骤跟踪：记录步骤状态和进度
    3. 多计划支持：可同时管理多个计划
    4. 活动计划：支持设置当前活动计划
    """

    name: str = "planning"
    description: str = _PLANNING_TOOL_DESCRIPTION
    # 工具参数定义
    # 包括：
    # - command: 执行的命令类型
    # - plan_id: 计划唯一标识
    # - title: 计划标题
    # - steps: 计划步骤列表
    # - step_index: 步骤索引
    # - step_status: 步骤状态
    # - step_notes: 步骤注释
    parameters: dict = {
        "type": "object",
        "properties": {
            "command": {
                "description": "The command to execute. Available commands: create, update, list, get, set_active, mark_step, delete.",
                "enum": [
                    "create",
                    "update",
                    "list",
                    "get",
                    "set_active",
                    "mark_step",
                    "delete",
                ],
                "type": "string",
            },
            "plan_id": {
                "description": "Unique identifier for the plan. Required for create, update, set_active, and delete commands. Optional for get and mark_step (uses active plan if not specified).",
                "type": "string",
            },
            "title": {
                "description": "Title for the plan. Required for create command, optional for update command.",
                "type": "string",
            },
            "steps": {
                "description": "List of plan steps. Required for create command, optional for update command.",
                "type": "array",
                "items": {"type": "string"},
            },
            "step_index": {
                "description": "Index of the step to update (0-based). Required for mark_step command.",
                "type": "integer",
            },
            "step_status": {
                "description": "Status to set for a step. Used with mark_step command.",
                "enum": ["not_started", "in_progress", "completed", "blocked"],
                "type": "string",
            },
            "step_notes": {
                "description": "Additional notes for a step. Optional for mark_step command.",
                "type": "string",
            },
        },
        "required": ["command"],
        "additionalProperties": False,
    }

    # 实例属性
    # - plans: 存储所有计划的字典
    # - _current_plan_id: 当前活动计划的ID
    plans: dict = {}  # Dictionary to store plans by plan_id
    _current_plan_id: Optional[str] = None  # Track the current active plan

    async def execute(
        self,
        *,
        command: Literal[
            "create", "update", "list", "get", "set_active", "mark_step", "delete"
        ],
        plan_id: Optional[str] = None,
        title: Optional[str] = None,
        steps: Optional[List[str]] = None,
        step_index: Optional[int] = None,
        step_status: Optional[
            Literal["not_started", "in_progress", "completed", "blocked"]
        ] = None,
        step_notes: Optional[str] = None,
        **kwargs,
    ):
        """
        Execute the planning tool with the given command and parameters.

        Parameters:
        - command: The operation to perform
        - plan_id: Unique identifier for the plan
        - title: Title for the plan (used with create command)
        - steps: List of steps for the plan (used with create command)
        - step_index: Index of the step to update (used with mark_step command)
        - step_status: Status to set for a step (used with mark_step command)
        - step_notes: Additional notes for a step (used with mark_step command)
        
        执行规划工具命令
        
        功能：
        1. 命令分发：根据不同命令调用相应的处理方法
        2. 参数验证：确保必要参数的存在和有效性
        3. 错误处理：统一的错误返回机制
        """

        if command == "create":
            return self._create_plan(plan_id, title, steps)
        elif command == "update":
            return self._update_plan(plan_id, title, steps)
        elif command == "list":
            return self._list_plans()
        elif command == "get":
            return self._get_plan(plan_id)
        elif command == "set_active":
            return self._set_active_plan(plan_id)
        elif command == "mark_step":
            return self._mark_step(plan_id, step_index, step_status, step_notes)
        elif command == "delete":
            return self._delete_plan(plan_id)
        else:
            raise ToolError(
                f"Unrecognized command: {command}. Allowed commands are: create, update, list, get, set_active, mark_step, delete"
            )

    def _create_plan(
        self, plan_id: Optional[str], title: Optional[str], steps: Optional[List[str]]
    ) -> ToolResult:
        """
        Create a new plan with the given ID, title, and steps.
        
        创建新计划
        
        功能：
        1. 参数验证：确保必要参数的完整性
        2. 重复检查：防止重复创建计划
        3. 初始化：设置步骤状态和注释
        4. 激活：将新计划设置为当前活动计划
        """
        if not plan_id:
            raise ToolError("Parameter `plan_id` is required for command: create")

        if plan_id in self.plans:
            raise ToolError(
                f"A plan with ID '{plan_id}' already exists. Use 'update' to modify existing plans."
            )

        if not title:
            raise ToolError("Parameter `title` is required for command: create")

        if (
            not steps
            or not isinstance(steps, list)
            or not all(isinstance(step, str) for step in steps)
        ):
            raise ToolError(
                "Parameter `steps` must be a non-empty list of strings for command: create"
            )

        # Create a new plan with initialized step statuses
        plan = {
            "plan_id": plan_id,
            "title": title,
            "steps": steps,
            "step_statuses": ["not_started"] * len(steps),
            "step_notes": [""] * len(steps),
        }

        self.plans[plan_id] = plan
        self._current_plan_id = plan_id  # Set as active plan

        return ToolResult(
            output=f"Plan created successfully with ID: {plan_id}\n\n{self._format_plan(plan)}"
        )

    def _update_plan(
        self, plan_id: Optional[str], title: Optional[str], steps: Optional[List[str]]
    ) -> ToolResult:
        """
        Update an existing plan with new title or steps.
        
        更新现有计划
        
        功能：
        1. 参数验证：确保计划存在
        2. 标题更新：可选更新计划标题
        3. 步骤更新：保持现有步骤状态
        4. 状态维护：为新步骤初始化状态
        """
        if not plan_id:
            raise ToolError("Parameter `plan_id` is required for command: update")

        if plan_id not in self.plans:
            raise ToolError(f"No plan found with ID: {plan_id}")

        plan = self.plans[plan_id]

        if title:
            plan["title"] = title

        if steps:
            if not isinstance(steps, list) or not all(
                isinstance(step, str) for step in steps
            ):
                raise ToolError(
                    "Parameter `steps` must be a list of strings for command: update"
                )

            # Preserve existing step statuses for unchanged steps
            old_steps = plan["steps"]
            old_statuses = plan["step_statuses"]
            old_notes = plan["step_notes"]

            # Create new step statuses and notes
            new_statuses = []
            new_notes = []

            for i, step in enumerate(steps):
                # If the step exists at the same position in old steps, preserve status and notes
                if i < len(old_steps) and step == old_steps[i]:
                    new_statuses.append(old_statuses[i])
                    new_notes.append(old_notes[i])
                else:
                    new_statuses.append("not_started")
                    new_notes.append("")

            plan["steps"] = steps
            plan["step_statuses"] = new_statuses
            plan["step_notes"] = new_notes

        return ToolResult(
            output=f"Plan updated successfully: {plan_id}\n\n{self._format_plan(plan)}"
        )

    def _list_plans(self) -> ToolResult:
        """
        List all available plans.
        
        列出所有计划
        
        功能：
        1. 空检查：处理无计划情况
        2. 状态显示：显示每个计划的完成进度
        3. 当前计划：标记当前活动计划
        """
        if not self.plans:
            return ToolResult(
                output="No plans available. Create a plan with the 'create' command."
            )

        output = "Available plans:\n"
        for plan_id, plan in self.plans.items():
            current_marker = " (active)" if plan_id == self._current_plan_id else ""
            completed = sum(
                1 for status in plan["step_statuses"] if status == "completed"
            )
            total = len(plan["steps"])
            progress = f"{completed}/{total} steps completed"
            output += f"• {plan_id}{current_marker}: {plan['title']} - {progress}\n"

        return ToolResult(output=output)

    def _get_plan(self, plan_id: Optional[str]) -> ToolResult:
        """
        Get details of a specific plan.
        
        获取计划详情
        
        功能：
        1. ID处理：支持使用当前活动计划
        2. 存在性检查：确保计划存在
        3. 格式化输出：显示完整计划信息
        """
        if not plan_id:
            # If no plan_id is provided, use the current active plan
            if not self._current_plan_id:
                raise ToolError(
                    "No active plan. Please specify a plan_id or set an active plan."
                )
            plan_id = self._current_plan_id

        if plan_id not in self.plans:
            raise ToolError(f"No plan found with ID: {plan_id}")

        plan = self.plans[plan_id]
        return ToolResult(output=self._format_plan(plan))

    def _set_active_plan(self, plan_id: Optional[str]) -> ToolResult:
        """
        Set a plan as the active plan.
        
        设置活动计划
        
        功能：
        1. 参数验证：确保提供了计划ID
        2. 存在性检查：确保计划存在
        3. 状态更新：更新当前活动计划
        """
        if not plan_id:
            raise ToolError("Parameter `plan_id` is required for command: set_active")

        if plan_id not in self.plans:
            raise ToolError(f"No plan found with ID: {plan_id}")

        self._current_plan_id = plan_id
        return ToolResult(output=f"Plan '{plan_id}' is now active.")

    def _mark_step(
        self,
        plan_id: Optional[str],
        step_index: Optional[int],
        step_status: Optional[str],
        step_notes: Optional[str],
    ) -> ToolResult:
        """
        Mark a step with a status and optional notes.
        
        标记步骤状态
        
        功能：
        1. 计划选择：支持指定计划或使用当前活动计划
        2. 索引验证：确保步骤索引有效
        3. 状态更新：更新步骤状态和注释
        4. 进度跟踪：记录步骤完成情况
        """
        if not step_index:
            raise ToolError("Parameter `step_index` is required for command: mark_step")

        if not step_status:
            raise ToolError("Parameter `step_status` is required for command: mark_step")

        # Use current plan if no plan_id provided
        if not plan_id:
            if not self._current_plan_id:
                raise ToolError(
                    "No active plan. Please specify a plan_id or set an active plan."
                )
            plan_id = self._current_plan_id

        if plan_id not in self.plans:
            raise ToolError(f"No plan found with ID: {plan_id}")

        plan = self.plans[plan_id]

        if step_index < 0 or step_index >= len(plan["steps"]):
            raise ToolError(
                f"Invalid step_index: {step_index}. Must be between 0 and {len(plan['steps']) - 1}"
            )

        # Update step status and notes
        plan["step_statuses"][step_index] = step_status
        if step_notes:
            plan["step_notes"][step_index] = step_notes

        return ToolResult(
            output=f"Updated step {step_index} in plan '{plan_id}'\n\n{self._format_plan(plan)}"
        )

    def _delete_plan(self, plan_id: Optional[str]) -> ToolResult:
        """
        Delete a plan.
        
        删除计划
        
        功能：
        1. 参数验证：确保提供了计划ID
        2. 存在性检查：确保计划存在
        3. 活动计划处理：清除活动计划（如果被删除的是活动计划）
        """
        if not plan_id:
            raise ToolError("Parameter `plan_id` is required for command: delete")

        if plan_id not in self.plans:
            raise ToolError(f"No plan found with ID: {plan_id}")

        del self.plans[plan_id]

        # Clear current plan if we just deleted it
        if self._current_plan_id == plan_id:
            self._current_plan_id = None

        return ToolResult(output=f"Plan '{plan_id}' deleted successfully.")

    def _format_plan(self, plan: Dict) -> str:
        """
        Format a plan for display.
        
        格式化计划显示
        
        功能：
        1. 标题显示：显示计划ID和标题
        2. 步骤列表：显示所有步骤及其状态
        3. 注释展示：显示步骤相关注释
        4. 进度统计：显示计划完成进度
        """
        output = [f"Plan: {plan['plan_id']} - {plan['title']}"]
        output.append("\nSteps:")
        for i, (step, status, notes) in enumerate(
            zip(plan["steps"], plan["step_statuses"], plan["step_notes"])
        ):
            status_marker = {
                "not_started": "[ ]",
                "in_progress": "[→]",
                "completed": "[✓]",
                "blocked": "[!]",
            }.get(status, "[-]")
            
            step_line = f"{i}. {status_marker} {step}"
            if notes:
                step_line += f"\n   Notes: {notes}"
            output.append(step_line)

        # Add progress summary
        completed = sum(1 for status in plan["step_statuses"] if status == "completed")
        total = len(plan["steps"])
        output.append(f"\nProgress: {completed}/{total} steps completed")

        return "\n".join(output)
