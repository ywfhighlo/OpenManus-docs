# 规划Agent模块
# 设计说明：
# 1. 任务规划：实现任务分解和执行计划管理
# 2. 状态追踪：完整的计划执行状态监控系统
# 3. 进度管理：支持暂停、恢复和动态更新
# 4. 工具集成：与规划工具的深度集成
# 5. 错误处理：完善的异常处理和恢复机制

import time
from typing import Dict, List, Optional

from pydantic import Field, model_validator

from app.agent.toolcall import ToolCallAgent
from app.logger import logger
from app.prompt.planning import NEXT_STEP_PROMPT, PLANNING_SYSTEM_PROMPT
from app.schema import Message, TOOL_CHOICE_TYPE, ToolCall, ToolChoice
from app.tool import PlanningTool, Terminate, ToolCollection

# 规划Agent
# 核心设计理念：
# 1. 任务分解：将复杂任务分解为可执行的步骤
# 2. 状态追踪：实时监控每个步骤的执行状态
# 3. 进度管理：支持暂停、恢复和状态更新
# 4. 工具集成：与规划工具和终止工具的深度集成
class PlanningAgent(ToolCallAgent):
    """
    An agent that creates and manages plans to solve tasks.

    This agent uses a planning tool to create and manage structured plans,
    and tracks progress through individual steps until task completion.
    
    规划Agent实现
    
    核心功能：
    1. 计划创建：生成结构化的任务执行计划
    2. 进度追踪：实时监控每个步骤的执行状态
    3. 状态管理：维护计划和步骤的完整生命周期
    4. 工具协调：管理规划工具的调用和结果处理
    5. 异常处理：优雅处理执行过程中的各类异常
    """

    name: str = "planning"
    description: str = "An agent that creates and manages plans to solve tasks"

    # 提示词配置
    # 设计说明：
    # 1. 系统提示词：专门的规划系统行为指导
    # 2. 步骤提示词：包含计划状态的动态模板
    # 3. 上下文感知：根据计划状态动态调整提示
    system_prompt: str = PLANNING_SYSTEM_PROMPT
    next_step_prompt: str = NEXT_STEP_PROMPT

    # 工具配置
    # 核心工具集：
    # 1. PlanningTool: 计划管理的核心工具
    #    - 创建和更新计划
    #    - 管理步骤状态
    #    - 追踪执行进度
    # 2. Terminate: 执行控制工具
    #    - 终止计划执行
    #    - 清理资源
    available_tools: ToolCollection = Field(
        default_factory=lambda: ToolCollection(PlanningTool(), Terminate())
    )
    tool_choices: TOOL_CHOICE_TYPE = ToolChoice.AUTO # type: ignore
    special_tool_names: List[str] = Field(default_factory=lambda: [Terminate().name])

    # 状态追踪
    # 设计说明：
    # 1. 工具调用：
    #    - 记录当前执行的工具
    #    - 关联步骤和工具的执行
    # 2. 计划标识：
    #    - 唯一的计划ID
    #    - 支持多计划并行执行
    # 3. 执行追踪：
    #    - 详细的步骤执行状态
    #    - 工具调用结果记录
    # 4. 进度指示：
    #    - 当前执行的步骤索引
    #    - 支持断点续执行
    tool_calls: List[ToolCall] = Field(default_factory=list)
    active_plan_id: Optional[str] = Field(default=None)
    step_execution_tracker: Dict[str, Dict] = Field(default_factory=dict)
    current_step_index: Optional[int] = None

    # 执行控制
    # 设计说明：
    # 1. 步数限制：平衡执行效率和计划复杂度
    # 2. 超时保护：防止计划执行无限循环
    # 3. 资源控制：确保系统资源合理使用
    max_steps: int = 20

    # 初始化验证
    # 实现说明：
    # 1. 生成唯一的计划ID
    # 2. 确保PlanningTool可用
    # 3. 使用模型验证器确保初始化完整性
    @model_validator(mode="after")
    def initialize_plan_and_verify_tools(self) -> "PlanningAgent":
        """
        Initialize agent with default plan ID and validate required tools.
        
        初始化验证器
        
        功能说明：
        1. 计划初始化：生成基于时间戳的唯一计划ID
        2. 工具验证：确保必要的规划工具可用
        3. 状态检查：验证Agent的初始状态
        4. 配置确认：确保所有必要的配置已就绪
        """
        self.active_plan_id = f"plan_{int(time.time())}"

        if "planning" not in self.available_tools.tool_map:
            self.available_tools.add_tool(PlanningTool())

        return self

    # 思考阶段
    # 实现流程：
    # 1. 获取当前计划状态
    # 2. 更新提示词包含计划信息
    # 3. 获取当前步骤索引
    # 4. 调用父类思考逻辑
    # 5. 更新步骤执行追踪器
    async def think(self) -> bool:
        """
        Decide the next action based on plan status.
        
        思考阶段实现
        
        执行流程：
        1. 状态获取：读取当前计划状态
        2. 提示更新：将计划状态注入提示模板
        3. 步骤定位：确定当前执行的步骤
        4. 决策制定：调用父类思考逻辑
        5. 状态更新：更新步骤执行追踪器
        
        返回值：
        - True: 需要执行行动
        - False: 不需要执行行动
        """
        prompt = (
            f"CURRENT PLAN STATUS:\n{await self.get_plan()}\n\n{self.next_step_prompt}"
            if self.active_plan_id
            else self.next_step_prompt
        )
        self.messages.append(Message.user_message(prompt))

        # Get the current step index before thinking
        self.current_step_index = await self._get_current_step_index()

        result = await super().think()

        # After thinking, if we decided to execute a tool and it's not a planning tool or special tool,
        # associate it with the current step for tracking
        if result and self.tool_calls:
            latest_tool_call = self.tool_calls[0]  # Get the most recent tool call
            if (
                latest_tool_call.function.name != "planning"
                and latest_tool_call.function.name not in self.special_tool_names
                and self.current_step_index is not None
            ):
                self.step_execution_tracker[latest_tool_call.id] = {
                    "step_index": self.current_step_index,
                    "tool_name": latest_tool_call.function.name,
                    "status": "pending",  # Will be updated after execution
                }

        return result

    # 行动阶段
    # 实现流程：
    # 1. 执行父类的行动逻辑
    # 2. 更新工具执行状态
    # 3. 更新计划状态
    # 4. 返回执行结果
    async def act(self) -> str:
        """
        Execute a step and track its completion status.
        
        行动阶段实现
        
        执行流程：
        1. 工具执行：调用父类的行动逻辑
        2. 状态更新：更新工具执行状态
        3. 进度更新：更新计划执行进度
        4. 结果处理：处理和记录执行结果
        
        返回值：
        - 执行结果的文本描述
        """
        result = await super().act()

        # After executing the tool, update the plan status
        if self.tool_calls:
            latest_tool_call = self.tool_calls[0]

            # Update the execution status to completed
            if latest_tool_call.id in self.step_execution_tracker:
                self.step_execution_tracker[latest_tool_call.id]["status"] = "completed"
                self.step_execution_tracker[latest_tool_call.id]["result"] = result

                # Update the plan status if this was a non-planning, non-special tool
                if (
                    latest_tool_call.function.name != "planning"
                    and latest_tool_call.function.name not in self.special_tool_names
                ):
                    await self.update_plan_status(latest_tool_call.id)

        return result

    # 获取计划
    # 实现说明：
    # 1. 检查计划ID是否存在
    # 2. 调用规划工具获取计划状态
    # 3. 处理返回结果格式
    async def get_plan(self) -> str:
        """
        Retrieve the current plan status.
        
        计划获取
        
        功能说明：
        1. 有效性检查：验证计划ID是否存在
        2. 状态查询：调用规划工具获取计划
        3. 结果处理：格式化返回的计划信息
        4. 错误处理：处理查询失败的情况
        
        返回值：
        - 当前计划的状态描述
        - 如无活动计划，返回提示信息
        """
        if not self.active_plan_id:
            return "No active plan. Please create a plan first."

        result = await self.available_tools.execute(
            name="planning",
            tool_input={"command": "get", "plan_id": self.active_plan_id},
        )
        return result.output if hasattr(result, "output") else str(result)

    # 运行入口
    # 实现流程：
    # 1. 处理初始请求
    # 2. 创建初始计划
    # 3. 调用父类运行逻辑
    async def run(self, request: Optional[str] = None) -> str:
        """
        Run the agent with an optional initial request.
        
        执行入口
        
        执行流程：
        1. 请求处理：处理可选的初始请求
        2. 计划创建：根据请求创建初始计划
        3. 执行控制：调用父类的运行逻辑
        4. 结果返回：返回执行的最终结果
        """
        if request:
            await self.create_initial_plan(request)
        return await super().run()

    # 更新计划状态
    # 实现细节：
    # 1. 验证计划和工具调用的有效性
    # 2. 检查工具执行状态
    # 3. 更新步骤状态
    # 4. 错误处理和日志记录
    async def update_plan_status(self, tool_call_id: str) -> None:
        """
        Update the current plan progress based on completed tool execution.
        Only marks a step as completed if the associated tool has been successfully executed.
        
        计划状态更新
        
        实现细节：
        1. 参数验证：
           - 检查计划ID的有效性
           - 验证工具调用ID的存在
        2. 状态检查：
           - 确认工具执行完成
           - 验证步骤索引有效
        3. 更新操作：
           - 标记步骤为已完成
           - 更新执行追踪器
        4. 错误处理：
           - 记录更新失败的原因
           - 保持系统状态一致性
        """
        if not self.active_plan_id:
            return

        if tool_call_id not in self.step_execution_tracker:
            logger.warning(f"No step tracking found for tool call {tool_call_id}")
            return

        tracker = self.step_execution_tracker[tool_call_id]
        if tracker["status"] != "completed":
            logger.warning(f"Tool call {tool_call_id} has not completed successfully")
            return

        step_index = tracker["step_index"]

        try:
            # Mark the step as completed
            await self.available_tools.execute(
                name="planning",
                tool_input={
                    "command": "mark_step",
                    "plan_id": self.active_plan_id,
                    "step_index": step_index,
                    "step_status": "completed",
                },
            )
            logger.info(
                f"Marked step {step_index} as completed in plan {self.active_plan_id}"
            )
        except Exception as e:
            logger.warning(f"Failed to update plan status: {e}")

    # 获取当前步骤索引
    # 实现细节：
    # 1. 解析计划文本
    # 2. 定位Steps部分
    # 3. 查找未完成步骤
    # 4. 更新步骤状态
    # 5. 错误处理
    async def _get_current_step_index(self) -> Optional[int]:
        """
        Parse the current plan to identify the first non-completed step's index.
        Returns None if no active step is found.
        
        步骤索引获取
        
        实现细节：
        1. 计划解析：
           - 获取完整的计划文本
           - 按行分割计划内容
        2. 步骤定位：
           - 查找Steps部分的起始位置
           - 识别未完成的步骤
        3. 状态更新：
           - 标记当前步骤为进行中
           - 更新步骤状态
        4. 错误处理：
           - 处理解析失败的情况
           - 返回合适的默认值
        
        返回值：
        - 当前需要执行的步骤索引
        - 如果没有活动步骤，返回None
        """
        if not self.active_plan_id:
            return None

        plan = await self.get_plan()

        try:
            plan_lines = plan.splitlines()
            steps_index = -1

            # Find the index of the "Steps:" line
            for i, line in enumerate(plan_lines):
                if line.strip() == "Steps:":
                    steps_index = i
                    break

            if steps_index == -1:
                return None

            # Find the first non-completed step
            for i, line in enumerate(plan_lines[steps_index + 1 :], start=0):
                if "[ ]" in line or "[→]" in line:  # not_started or in_progress
                    # Mark current step as in_progress
                    await self.available_tools.execute(
                        name="planning",
                        tool_input={
                            "command": "mark_step",
                            "plan_id": self.active_plan_id,
                            "step_index": i,
                            "step_status": "in_progress",
                        },
                    )
                    return i

            return None  # No active step found
        except Exception as e:
            logger.warning(f"Error finding current step index: {e}")
            return None

    # 创建初始计划
    # 实现流程：
    # 1. 生成计划ID
    # 2. 构建初始消息
    # 3. 调用LLM创建计划
    # 4. 执行规划工具
    # 5. 更新内存状态
    async def create_initial_plan(self, request: str) -> None:
        """Create an initial plan based on the request."""
        logger.info(f"Creating initial plan with ID: {self.active_plan_id}")

        messages = [
            Message.user_message(
                f"Analyze the request and create a plan with ID {self.active_plan_id}: {request}"
            )
        ]
        self.memory.add_messages(messages)
        response = await self.llm.ask_tool(
            messages=messages,
            system_msgs=[Message.system_message(self.system_prompt)],
            tools=self.available_tools.to_params(),
            tool_choice=ToolChoice.REQUIRED,
        )
        assistant_msg = Message.from_tool_calls(
            content=response.content, tool_calls=response.tool_calls
        )

        self.memory.add_message(assistant_msg)

        plan_created = False
        for tool_call in response.tool_calls:
            if tool_call.function.name == "planning":
                result = await self.execute_tool(tool_call)
                logger.info(
                    f"Executed tool {tool_call.function.name} with result: {result}"
                )

                # Add tool response to memory
                tool_msg = Message.tool_message(
                    content=result,
                    tool_call_id=tool_call.id,
                    name=tool_call.function.name,
                )
                self.memory.add_message(tool_msg)
                plan_created = True
                break

        if not plan_created:
            logger.warning("No plan created from initial request")
            tool_msg = Message.assistant_message(
                "Error: Parameter `plan_id` is required for command: create"
            )
            self.memory.add_message(tool_msg)


async def main():
    # Configure and run the agent
    agent = PlanningAgent(available_tools=ToolCollection(PlanningTool(), Terminate()))
    result = await agent.run("Help me plan a trip to the moon")
    print(result)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
