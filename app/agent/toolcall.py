# 工具调用Agent模块
# 设计说明：
# 1. 工具抽象：提供统一的工具调用接口
# 2. 执行控制：支持多种工具调用模式
# 3. 错误处理：完整的异常捕获和恢复机制
# 4. 状态管理：工具执行状态的转换控制
# 5. 扩展支持：灵活的工具注册和管理机制

import json

from typing import Any, List, Literal, Optional, Union

from pydantic import Field

from app.agent.react import ReActAgent
from app.logger import logger
from app.prompt.toolcall import NEXT_STEP_PROMPT, SYSTEM_PROMPT
from app.schema import AgentState, Message, ToolCall, TOOL_CHOICE_TYPE, ToolChoice
from app.tool import CreateChatCompletion, Terminate, ToolCollection


TOOL_CALL_REQUIRED = "Tool calls required but none provided"


class ToolCallAgent(ReActAgent):
    """
    Base agent class for handling tool/function calls with enhanced abstraction
    
    工具调用Agent基类
    
    核心功能：
    1. 工具管理：统一的工具注册和调用接口
    2. 执行模式：支持自动、强制和禁用三种调用模式
    3. 状态控制：特殊工具的状态转换管理
    4. 错误处理：完整的异常捕获和恢复机制
    5. 结果处理：统一的工具执行结果格式化
    """

    name: str = "toolcall"
    description: str = "an agent that can execute tool calls."

    system_prompt: str = SYSTEM_PROMPT
    next_step_prompt: str = NEXT_STEP_PROMPT

    # 工具配置
    # 设计说明：
    # 1. 默认工具集：
    #    - CreateChatCompletion: 对话生成工具
    #    - Terminate: 执行终止工具
    # 2. 调用模式：
    #    - none: 禁用工具调用
    #    - auto: 智能选择是否使用工具
    #    - required: 强制要求使用工具
    # 3. 特殊工具：可以影响Agent状态的工具列表
    available_tools: ToolCollection = ToolCollection(
        CreateChatCompletion(), Terminate()
    )
    tool_choices: TOOL_CHOICE_TYPE = ToolChoice.AUTO # type: ignore
    special_tool_names: List[str] = Field(default_factory=lambda: [Terminate().name])

    # 运行时状态
    # 说明：
    # - tool_calls: 存储当前待执行的工具调用列表
    # - 每个工具调用包含工具名称和参数信息
    tool_calls: List[ToolCall] = Field(default_factory=list)

    # 执行控制参数
    # 说明：
    # - 默认30步：考虑到工具调用的复杂性
    # - 可通过子类调整以适应不同场景
    max_steps: int = 30
    max_observe: Optional[Union[int, bool]] = None

    async def think(self) -> bool:
        """
        Process current state and decide next actions using tools
        
        思考阶段实现
        
        执行流程：
        1. 提示处理：添加next_step_prompt到对话历史
        2. LLM调用：使用工具选项获取模型响应
        3. 响应处理：根据tool_choices处理结果
        4. 状态更新：更新内存和工具调用状态
        5. 异常处理：捕获并记录执行异常
        
        返回值：
        - True: 表示需要继续执行
        - False: 表示当前阶段结束
        """
        if self.next_step_prompt:
            user_msg = Message.user_message(self.next_step_prompt)
            self.messages += [user_msg]

        # Get response with tool options
        response = await self.llm.ask_tool(
            messages=self.messages,
            system_msgs=[Message.system_message(self.system_prompt)]
            if self.system_prompt
            else None,
            tools=self.available_tools.to_params(),
            tool_choice=self.tool_choices,
        )
        self.tool_calls = response.tool_calls

        # Log response info
        logger.info(f"✨ {self.name}'s thoughts: {response.content}")
        logger.info(
            f"🛠️ {self.name} selected {len(response.tool_calls) if response.tool_calls else 0} tools to use"
        )
        if response.tool_calls:
            logger.info(
                f"🧰 Tools being prepared: {[call.function.name for call in response.tool_calls]}"
            )

        try:
            # Handle different tool_choices modes
            if self.tool_choices == ToolChoice.NONE:
                if response.tool_calls:
                    logger.warning(
                        f"🤔 Hmm, {self.name} tried to use tools when they weren't available!"
                    )
                if response.content:
                    self.memory.add_message(Message.assistant_message(response.content))
                    return True
                return False

            # Create and add assistant message
            assistant_msg = (
                Message.from_tool_calls(
                    content=response.content, tool_calls=self.tool_calls
                )
                if self.tool_calls
                else Message.assistant_message(response.content)
            )
            self.memory.add_message(assistant_msg)

            if self.tool_choices == ToolChoice.REQUIRED and not self.tool_calls:
                return True  # Will be handled in act()

            # For 'auto' mode, continue with content if no commands but content exists
            if self.tool_choices == ToolChoice.AUTO and not self.tool_calls:
                return bool(response.content)

            return bool(self.tool_calls)
        except Exception as e:
            logger.error(f"🚨 Oops! The {self.name}'s thinking process hit a snag: {e}")
            self.memory.add_message(
                Message.assistant_message(
                    f"Error encountered while processing: {str(e)}"
                )
            )
            return False

    async def act(self) -> str:
        """
        Execute tool calls and handle their results
        
        行动阶段实现
        
        执行流程：
        1. 调用验证：检查是否存在待执行的工具
        2. 顺序执行：依次执行每个工具调用
        3. 结果处理：记录执行结果到内存
        4. 状态更新：更新Agent状态
        
        返回值：
        - 字符串形式的执行结果
        - 多个结果会被合并为一个字符串
        """
        if not self.tool_calls:
            if self.tool_choices == ToolChoice.REQUIRED:
                raise ValueError(TOOL_CALL_REQUIRED)

            # Return last message content if no tool calls
            return self.messages[-1].content or "No content or commands to execute"

        results = []
        for command in self.tool_calls:
            result = await self.execute_tool(command)

            if self.max_observe:
                result = result[: self.max_observe]

            logger.info(
                f"🎯 Tool '{command.function.name}' completed its mission! Result: {result}"
            )

            # Add tool response to memory
            tool_msg = Message.tool_message(
                content=result, tool_call_id=command.id, name=command.function.name
            )
            self.memory.add_message(tool_msg)
            results.append(result)

        return "\n\n".join(results)

    async def execute_tool(self, command: ToolCall) -> str:
        """
        Execute a single tool call with robust error handling
        
        工具执行实现
        
        执行流程：
        1. 命令验证：检查命令格式和工具可用性
        2. 参数解析：将JSON格式参数转换为Python对象
        3. 工具调用：执行具体工具的逻辑
        4. 结果处理：格式化执行结果
        5. 状态处理：处理特殊工具的状态变化
        
        异常处理：
        1. JSON解析错误：参数格式无效
        2. 工具执行错误：工具内部异常
        3. 未知工具错误：工具不存在
        """
        if not command or not command.function or not command.function.name:
            return "Error: Invalid command format"

        name = command.function.name
        if name not in self.available_tools.tool_map:
            return f"Error: Unknown tool '{name}'"

        try:
            # Parse arguments
            args = json.loads(command.function.arguments or "{}")

            # Execute the tool
            logger.info(f"🔧 Activating tool: '{name}'...")
            result = await self.available_tools.execute(name=name, tool_input=args)

            # Format result for display
            observation = (
                f"Observed output of cmd `{name}` executed:\n{str(result)}"
                if result
                else f"Cmd `{name}` completed with no output"
            )

            # Handle special tools like `finish`
            await self._handle_special_tool(name=name, result=result)

            return observation
        except json.JSONDecodeError:
            error_msg = f"Error parsing arguments for {name}: Invalid JSON format"
            logger.error(
                f"📝 Oops! The arguments for '{name}' don't make sense - invalid JSON, arguments:{command.function.arguments}"
            )
            return f"Error: {error_msg}"
        except Exception as e:
            error_msg = f"⚠️ Tool '{name}' encountered a problem: {str(e)}"
            logger.error(error_msg)
            return f"Error: {error_msg}"

    async def _handle_special_tool(self, name: str, result: Any, **kwargs):
        """
        Handle special tool execution and state changes
        
        特殊工具处理
        
        功能：
        1. 状态转换：处理可能改变Agent状态的工具
        2. 执行控制：根据工具结果决定是否继续执行
        3. 扩展支持：允许通过kwargs传递额外参数
        """
        if not self._is_special_tool(name):
            return

        if self._should_finish_execution(name=name, result=result, **kwargs):
            # Set agent state to finished
            logger.info(f"🏁 Special tool '{name}' has completed the task!")
            self.state = AgentState.FINISHED

    @staticmethod
    def _should_finish_execution(**kwargs) -> bool:
        """
        Determine if tool execution should finish the agent
        
        执行完成判断
        
        功能：
        1. 默认行为：返回True表示执行应该结束
        2. 可重写：子类可以实现自定义的完成判断逻辑
        3. 参数灵活：支持通过kwargs传递额外判断条件
        """
        return True

    def _is_special_tool(self, name: str) -> bool:
        """
        Check if tool name is in special tools list
        
        特殊工具检查
        
        实现特点：
        1. 大小写不敏感：忽略工具名称的大小写
        2. 高效实现：使用列表推导进行名称匹配
        3. 灵活配置：支持动态更新特殊工具列表
        """
        return name.lower() in [n.lower() for n in self.special_tool_names]
