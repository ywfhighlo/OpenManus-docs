# 工具调用代理提示词配置
# 设计说明：
# 1. 角色定位：专门执行工具调用的代理
# 2. 职责范围：工具函数的调用与执行
# 3. 交互模式：基于工具的任务处理
SYSTEM_PROMPT = "You are an agent that can execute tool calls"

# 下一步操作提示词
# 说明：使用terminate工具/函数来结束交互
NEXT_STEP_PROMPT = (
    "If you want to stop interaction, use `terminate` tool/function call."
)
