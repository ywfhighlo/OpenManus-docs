# Shell命令执行工具模块
# 设计说明：
# 1. 提供异步Shell命令执行功能
# 2. 支持超时控制
# 3. 输出长度限制
# 4. 统一的错误处理

"""Utility to run shell commands asynchronously with a timeout."""

import asyncio


# 输出截断相关常量
# TRUNCATED_MESSAGE: 截断提示信息
# MAX_RESPONSE_LEN: 最大响应长度（16000字符）
TRUNCATED_MESSAGE: str = "<response clipped><NOTE>To save on context only part of this file has been shown to you. You should retry this tool after you have searched inside the file with `grep -n` in order to find the line numbers of what you are looking for.</NOTE>"
MAX_RESPONSE_LEN: int = 16000


# 内容截断函数
# 功能：
# 1. 检查内容长度
# 2. 超出限制时进行截断
# 3. 添加截断提示信息
def maybe_truncate(content: str, truncate_after: int | None = MAX_RESPONSE_LEN):
    """Truncate content and append a notice if content exceeds the specified length."""
    return (
        content
        if not truncate_after or len(content) <= truncate_after
        else content[:truncate_after] + TRUNCATED_MESSAGE
    )


# 异步命令执行函数
# 功能：
# 1. 异步执行Shell命令
# 2. 超时控制和中断处理
# 3. 输出截断处理
# 4. 错误处理和返回码管理
async def run(
    cmd: str,
    timeout: float | None = 120.0,  # seconds
    truncate_after: int | None = MAX_RESPONSE_LEN,
):
    """Run a shell command asynchronously with a timeout."""
    # 创建异步子进程
    process = await asyncio.create_subprocess_shell(
        cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )

    try:
        # 等待进程执行完成并获取输出
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
        return (
            process.returncode or 0,
            maybe_truncate(stdout.decode(), truncate_after=truncate_after),
            maybe_truncate(stderr.decode(), truncate_after=truncate_after),
        )
    except asyncio.TimeoutError as exc:
        # 超时处理：终止进程并抛出异常
        try:
            process.kill()
        except ProcessLookupError:
            pass
        raise TimeoutError(
            f"Command '{cmd}' timed out after {timeout} seconds"
        ) from exc
