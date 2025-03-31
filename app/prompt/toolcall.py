# 工具调用代理提示词模块
# 定义工具调用代理使用的系统提示词和下一步提示模板，指导代理执行工具调用
SYSTEM_PROMPT = "You are an agent that can execute tool calls"

NEXT_STEP_PROMPT = (
    "If you want to stop interaction, use `terminate` tool/function call."
)
