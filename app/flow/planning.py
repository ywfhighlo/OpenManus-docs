# 规划流程模块
# 设计说明：
# 1. 流程管理：实现基于规划的任务执行流程
# 2. 多Agent协作：支持多个Agent的协同工作
# 3. 状态追踪：完整的计划状态管理机制
# 4. 错误处理：健壮的异常处理和恢复机制
# 5. 工具集成：与规划工具的深度集成

import json
import time
from typing import Dict, List, Optional, Union

from pydantic import Field

from app.agent.base import BaseAgent
from app.flow.base import BaseFlow, PlanStepStatus
from app.llm import LLM
from app.logger import logger
from app.schema import AgentState, Message
from app.tool import PlanningTool

# 规划流程实现
# 核心设计理念：
# 1. 任务分解：将复杂任务分解为可执行的步骤
# 2. 多Agent协作：根据步骤类型选择合适的执行者
# 3. 状态管理：实时追踪和更新计划状态
# 4. 错误处理：完整的异常捕获和恢复机制
class PlanningFlow(BaseFlow):
    """
    A flow that manages planning and execution of tasks using agents.
    
    规划流程类
    
    核心功能：
    1. 计划管理：创建和维护任务执行计划
    2. 执行控制：协调多个Agent的任务执行
    3. 状态追踪：监控和更新计划执行状态
    4. 错误处理：处理执行过程中的异常情况
    5. 结果收集：汇总和返回执行结果
    """

    # 核心组件
    # 设计说明：
    # 1. llm：语言模型组件
    #    - 用于计划生成和理解
    #    - 支持动态调整和配置
    # 2. planning_tool：规划工具
    #    - 管理计划的创建和更新
    #    - 提供计划操作接口
    # 3. executor_keys：执行者列表
    #    - 支持多Agent协作
    #    - 灵活的执行者选择
    # 4. active_plan_id：计划标识
    #    - 唯一标识当前活动计划
    #    - 基于时间戳生成
    # 5. current_step_index：步骤索引
    #    - 追踪当前执行位置
    #    - 支持断点续执行
    llm: LLM = Field(default_factory=lambda: LLM())
    planning_tool: PlanningTool = Field(default_factory=PlanningTool)
    executor_keys: List[str] = Field(default_factory=list)
    active_plan_id: str = Field(default_factory=lambda: f"plan_{int(time.time())}")
    current_step_index: Optional[int] = None

    # 初始化方法
    # 实现流程：
    # 1. 处理执行者配置
    # 2. 设置计划ID
    # 3. 初始化规划工具
    # 4. 配置默认执行者
    def __init__(
        self, agents: Union[BaseAgent, List[BaseAgent], Dict[str, BaseAgent]], **data
    ):
        """
        Initialize the planning flow with agents and configuration.
        
        初始化方法
        
        实现流程：
        1. 执行者配置：
           - 处理executors参数
           - 设置执行者列表
        2. 计划配置：
           - 设置计划ID
           - 初始化计划状态
        3. 工具初始化：
           - 配置规划工具
           - 设置默认参数
        4. 基类初始化：
           - 调用父类构造函数
           - 传递处理后的参数
        """
        # Set executor keys before super().__init__
        if "executors" in data:
            data["executor_keys"] = data.pop("executors")

        # Set plan ID if provided
        if "plan_id" in data:
            data["active_plan_id"] = data.pop("plan_id")

        # Initialize the planning tool if not provided
        if "planning_tool" not in data:
            planning_tool = PlanningTool()
            data["planning_tool"] = planning_tool

        # Call parent's init with the processed data
        super().__init__(agents, **data)

        # Set executor_keys to all agent keys if not specified
        if not self.executor_keys:
            self.executor_keys = list(self.agents.keys())

    # 执行者选择
    # 选择策略：
    # 1. 优先根据步骤类型匹配专门的Agent
    # 2. 如果没有匹配的专门Agent，使用默认执行者
    # 3. 最后回退到主Agent
    def get_executor(self, step_type: Optional[str] = None) -> BaseAgent:
        """
        Get an appropriate executor agent for the current step.
        Can be extended to select agents based on step type/requirements.
        
        执行者选择方法
        
        选择策略：
        1. 类型匹配：
           - 优先根据步骤类型选择专门的Agent
           - 支持特定任务的专业处理
        2. 默认选择：
           - 使用配置的默认执行者
           - 确保执行者可用性
        3. 兜底机制：
           - 最后使用主Agent
           - 保证执行的连续性
        """
        # If step type is provided and matches an agent key, use that agent
        if step_type and step_type in self.agents:
            return self.agents[step_type]

        # Otherwise use the first available executor or fall back to primary agent
        for key in self.executor_keys:
            if key in self.agents:
                return self.agents[key]

        # Fallback to primary agent
        return self.primary_agent

    # 主执行流程
    # 执行步骤：
    # 1. 验证主Agent可用性
    # 2. 创建初始计划（如果有输入）
    # 3. 循环执行计划步骤
    # 4. 处理执行结果和状态更新
    # 5. 错误处理和日志记录
    async def execute(self, input_text: str) -> str:
        """
        Execute the planning flow with agents.
        
        主执行方法
        
        执行流程：
        1. 初始化：
           - 验证主Agent可用性
           - 创建初始计划
        2. 执行循环：
           - 获取当前步骤
           - 选择合适的执行者
           - 执行步骤并收集结果
        3. 状态管理：
           - 更新步骤状态
           - 检查终止条件
        4. 错误处理：
           - 捕获和处理异常
           - 记录错误信息
        5. 结果返回：
           - 汇总执行结果
           - 格式化输出
        """
        try:
            if not self.primary_agent:
                raise ValueError("No primary agent available")

            # Create initial plan if input provided
            if input_text:
                await self._create_initial_plan(input_text)

                # Verify plan was created successfully
                if self.active_plan_id not in self.planning_tool.plans:
                    logger.error(
                        f"Plan creation failed. Plan ID {self.active_plan_id} not found in planning tool."
                    )
                    return f"Failed to create plan for: {input_text}"

            result = ""
            while True:
                # Get current step to execute
                self.current_step_index, step_info = await self._get_current_step_info()

                # Exit if no more steps or plan completed
                if self.current_step_index is None:
                    result += await self._finalize_plan()
                    break

                # Execute current step with appropriate agent
                step_type = step_info.get("type") if step_info else None
                executor = self.get_executor(step_type)
                step_result = await self._execute_step(executor, step_info)
                result += step_result + "\n"

                # Check if agent wants to terminate
                if hasattr(executor, "state") and executor.state == AgentState.FINISHED:
                    break

            return result
        except Exception as e:
            logger.error(f"Error in PlanningFlow: {str(e)}")
            return f"Execution failed: {str(e)}"

    # 初始计划创建
    # 实现流程：
    # 1. 构建系统和用户提示词
    # 2. 调用LLM生成计划
    # 3. 处理工具调用结果
    # 4. 创建默认计划（如果生成失败）
    async def _create_initial_plan(self, request: str) -> None:
        """
        Create an initial plan based on the request using the flow's LLM and PlanningTool.
        
        初始计划创建
        
        实现流程：
        1. 提示构建：
           - 创建系统提示
           - 构建用户请求
        2. LLM调用：
           - 配置工具参数
           - 获取规划结果
        3. 结果处理：
           - 解析工具调用
           - 执行规划命令
        4. 兜底处理：
           - 创建默认计划
           - 记录警告信息
        """
        logger.info(f"Creating initial plan with ID: {self.active_plan_id}")

        # Create a system message for plan creation
        system_message = Message.system_message(
            "You are a planning assistant. Create a concise, actionable plan with clear steps. "
            "Focus on key milestones rather than detailed sub-steps. "
            "Optimize for clarity and efficiency."
        )

        # Create a user message with the request
        user_message = Message.user_message(
            f"Create a reasonable plan with clear steps to accomplish the task: {request}"
        )

        # Call LLM with PlanningTool
        response = await self.llm.ask_tool(
            messages=[user_message],
            system_msgs=[system_message],
            tools=[self.planning_tool.to_param()],
            tool_choice="required",
        )

        # Process tool calls if present
        if response.tool_calls:
            for tool_call in response.tool_calls:
                if tool_call.function.name == "planning":
                    # Parse the arguments
                    args = tool_call.function.arguments
                    if isinstance(args, str):
                        try:
                            args = json.loads(args)
                        except json.JSONDecodeError:
                            logger.error(f"Failed to parse tool arguments: {args}")
                            continue

                    # Ensure plan_id is set correctly and execute the tool
                    args["plan_id"] = self.active_plan_id

                    # Execute the tool via ToolCollection instead of directly
                    result = await self.planning_tool.execute(**args)

                    logger.info(f"Plan creation result: {str(result)}")
                    return

        # If execution reached here, create a default plan
        logger.warning("Creating default plan")

        # Create default plan using the ToolCollection
        await self.planning_tool.execute(
            **{
                "command": "create",
                "plan_id": self.active_plan_id,
                "title": f"Plan for: {request[:50]}{'...' if len(request) > 50 else ''}",
                "steps": ["Analyze request", "Execute task", "Verify results"],
            }
        )

    # 获取当前步骤信息
    # 实现细节：
    # 1. 验证计划存在性
    # 2. 获取计划数据和状态
    # 3. 查找第一个未完成的步骤
    # 4. 解析步骤类型和信息
    # 5. 更新步骤状态
    async def _get_current_step_info(self) -> tuple[Optional[int], Optional[dict]]:
        """
        Parse the current plan to identify the first non-completed step's index and info.
        Returns (None, None) if no active step is found.
        
        步骤信息获取
        
        实现细节：
        1. 计划验证：
           - 检查计划ID有效性
           - 验证计划数据存在
        2. 数据解析：
           - 获取步骤列表
           - 读取状态信息
        3. 步骤查找：
           - 定位未完成步骤
           - 提取步骤类型
        4. 状态更新：
           - 标记步骤进行中
           - 更新执行状态
        5. 结果返回：
           - 返回步骤索引和信息
           - 处理异常情况
        """
        if (
            not self.active_plan_id
            or self.active_plan_id not in self.planning_tool.plans
        ):
            logger.error(f"Plan with ID {self.active_plan_id} not found")
            return None, None

        try:
            # Direct access to plan data from planning tool storage
            plan_data = self.planning_tool.plans[self.active_plan_id]
            steps = plan_data.get("steps", [])
            step_statuses = plan_data.get("step_statuses", [])

            # Find first non-completed step
            for i, step in enumerate(steps):
                if i >= len(step_statuses):
                    status = PlanStepStatus.NOT_STARTED.value
                else:
                    status = step_statuses[i]

                if status in PlanStepStatus.get_active_statuses():
                    # Extract step type/category if available
                    step_info = {"text": step}

                    # Try to extract step type from the text (e.g., [SEARCH] or [CODE])
                    import re

                    type_match = re.search(r"\[([A-Z_]+)\]", step)
                    if type_match:
                        step_info["type"] = type_match.group(1).lower()

                    # Mark current step as in_progress
                    try:
                        await self.planning_tool.execute(
                            command="mark_step",
                            plan_id=self.active_plan_id,
                            step_index=i,
                            step_status=PlanStepStatus.IN_PROGRESS.value,
                        )
                    except Exception as e:
                        logger.warning(f"Error marking step as in_progress: {e}")
                        # Update step status directly if needed
                        if i < len(step_statuses):
                            step_statuses[i] = PlanStepStatus.IN_PROGRESS.value
                        else:
                            while len(step_statuses) < i:
                                step_statuses.append(PlanStepStatus.NOT_STARTED.value)
                            step_statuses.append(PlanStepStatus.IN_PROGRESS.value)

                        plan_data["step_statuses"] = step_statuses

                    return i, step_info

            return None, None  # No active step found

        except Exception as e:
            logger.warning(f"Error finding current step index: {e}")
            return None, None

    # 步骤执行
    # 实现流程：
    # 1. 准备执行上下文
    # 2. 构建步骤提示词
    # 3. 调用执行者Agent
    # 4. 处理执行结果
    async def _execute_step(self, executor: BaseAgent, step_info: dict) -> str:
        """
        Execute a single step using the provided executor agent.
        
        步骤执行方法
        
        执行流程：
        1. 参数准备：
           - 验证执行者可用性
           - 解析步骤信息
        2. 执行控制：
           - 调用执行者的run方法
           - 处理执行结果
        3. 状态更新：
           - 标记步骤完成
           - 更新执行记录
        4. 结果处理：
           - 格式化执行结果
           - 记录执行日志
        """
        # Prepare context for the agent with current plan status
        plan_status = await self._get_plan_text()
        step_text = step_info.get("text", f"Step {self.current_step_index}")

        # Create a prompt for the agent to execute the current step
        step_prompt = f"""
        CURRENT PLAN STATUS:
        {plan_status}

        YOUR CURRENT TASK:
        You are now working on step {self.current_step_index}: "{step_text}"

        Please execute this step using the appropriate tools. When you're done, provide a summary of what you accomplished.
        """

        # Use agent.run() to execute the step
        try:
            step_result = await executor.run(step_prompt)

            # Mark the step as completed after successful execution
            await self._mark_step_completed()

            return step_result
        except Exception as e:
            logger.error(f"Error executing step {self.current_step_index}: {e}")
            return f"Error executing step {self.current_step_index}: {str(e)}"

    async def _mark_step_completed(self) -> None:
        """
        Mark the current step as completed in the plan.
        
        步骤完成标记
        
        实现说明：
        1. 状态验证：
           - 检查步骤索引有效性
           - 验证计划状态
        2. 状态更新：
           - 调用规划工具
           - 设置完成标记
        3. 错误处理：
           - 捕获更新异常
           - 记录错误信息
        """
        if self.current_step_index is None:
            return

        try:
            # Mark the step as completed
            await self.planning_tool.execute(
                command="mark_step",
                plan_id=self.active_plan_id,
                step_index=self.current_step_index,
                step_status=PlanStepStatus.COMPLETED.value,
            )
            logger.info(
                f"Marked step {self.current_step_index} as completed in plan {self.active_plan_id}"
            )
        except Exception as e:
            logger.warning(f"Failed to update plan status: {e}")
            # Update step status directly in planning tool storage
            if self.active_plan_id in self.planning_tool.plans:
                plan_data = self.planning_tool.plans[self.active_plan_id]
                step_statuses = plan_data.get("step_statuses", [])

                # Ensure the step_statuses list is long enough
                while len(step_statuses) <= self.current_step_index:
                    step_statuses.append(PlanStepStatus.NOT_STARTED.value)

                # Update the status
                step_statuses[self.current_step_index] = PlanStepStatus.COMPLETED.value
                plan_data["step_statuses"] = step_statuses

    async def _get_plan_text(self) -> str:
        """
        Get the current plan's text representation.
        
        计划文本获取
        
        功能说明：
        1. 数据获取：
           - 访问计划存储
           - 读取计划数据
        2. 文本生成：
           - 格式化计划内容
           - 包含状态信息
        3. 错误处理：
           - 处理数据缺失
           - 返回默认信息
        """
        try:
            result = await self.planning_tool.execute(
                command="get", plan_id=self.active_plan_id
            )
            return result.output if hasattr(result, "output") else str(result)
        except Exception as e:
            logger.error(f"Error getting plan: {e}")
            return self._generate_plan_text_from_storage()

    def _generate_plan_text_from_storage(self) -> str:
        """
        Generate a text representation of the plan from storage data.
        
        计划文本生成
        
        实现细节：
        1. 数据验证：
           - 检查计划数据完整性
           - 验证必要字段
        2. 文本构建：
           - 格式化标题和描述
           - 生成步骤列表
        3. 状态标记：
           - 添加状态图标
           - 更新进度信息
        4. 格式控制：
           - 统一的文本格式
           - 清晰的层次结构
        """
        try:
            if self.active_plan_id not in self.planning_tool.plans:
                return f"Error: Plan with ID {self.active_plan_id} not found"

            plan_data = self.planning_tool.plans[self.active_plan_id]
            title = plan_data.get("title", "Untitled Plan")
            steps = plan_data.get("steps", [])
            step_statuses = plan_data.get("step_statuses", [])
            step_notes = plan_data.get("step_notes", [])

            # Ensure step_statuses and step_notes match the number of steps
            while len(step_statuses) < len(steps):
                step_statuses.append(PlanStepStatus.NOT_STARTED.value)
            while len(step_notes) < len(steps):
                step_notes.append("")

            # Count steps by status
            status_counts = {status: 0 for status in PlanStepStatus.get_all_statuses()}

            for status in step_statuses:
                if status in status_counts:
                    status_counts[status] += 1

            completed = status_counts[PlanStepStatus.COMPLETED.value]
            total = len(steps)
            progress = (completed / total) * 100 if total > 0 else 0

            plan_text = f"Plan: {title} (ID: {self.active_plan_id})\n"
            plan_text += "=" * len(plan_text) + "\n\n"

            plan_text += (
                f"Progress: {completed}/{total} steps completed ({progress:.1f}%)\n"
            )
            plan_text += f"Status: {status_counts[PlanStepStatus.COMPLETED.value]} completed, {status_counts[PlanStepStatus.IN_PROGRESS.value]} in progress, "
            plan_text += f"{status_counts[PlanStepStatus.BLOCKED.value]} blocked, {status_counts[PlanStepStatus.NOT_STARTED.value]} not started\n\n"
            plan_text += "Steps:\n"

            status_marks = PlanStepStatus.get_status_marks()

            for i, (step, status, notes) in enumerate(
                zip(steps, step_statuses, step_notes)
            ):
                # Use status marks to indicate step status
                status_mark = status_marks.get(
                    status, status_marks[PlanStepStatus.NOT_STARTED.value]
                )

                plan_text += f"{i}. {status_mark} {step}\n"
                if notes:
                    plan_text += f"   Notes: {notes}\n"

            return plan_text
        except Exception as e:
            logger.error(f"Error generating plan text from storage: {e}")
            return f"Error: Unable to retrieve plan with ID {self.active_plan_id}"

    async def _finalize_plan(self) -> str:
        """
        Finalize the plan and return completion status.
        
        计划完成处理
        
        处理流程：
        1. 状态确认：
           - 验证所有步骤完成
           - 检查执行结果
        2. 总结生成：
           - 汇总执行情况
           - 生成完成报告
        3. 资源清理：
           - 释放相关资源
           - 重置状态标记
        4. 结果返回：
           - 格式化最终结果
           - 包含完成状态
        """
        plan_text = await self._get_plan_text()

        # Create a summary using the flow's LLM directly
        try:
            system_message = Message.system_message(
                "You are a planning assistant. Your task is to summarize the completed plan."
            )

            user_message = Message.user_message(
                f"The plan has been completed. Here is the final plan status:\n\n{plan_text}\n\nPlease provide a summary of what was accomplished and any final thoughts."
            )

            response = await self.llm.ask(
                messages=[user_message], system_msgs=[system_message]
            )

            return f"Plan completed:\n\n{response}"
        except Exception as e:
            logger.error(f"Error finalizing plan with LLM: {e}")

            # Fallback to using an agent for the summary
            try:
                agent = self.primary_agent
                summary_prompt = f"""
                The plan has been completed. Here is the final plan status:

                {plan_text}

                Please provide a summary of what was accomplished and any final thoughts.
                """
                summary = await agent.run(summary_prompt)
                return f"Plan completed:\n\n{summary}"
            except Exception as e2:
                logger.error(f"Error finalizing plan with agent: {e2}")
                return "Plan completed. Error generating summary."
