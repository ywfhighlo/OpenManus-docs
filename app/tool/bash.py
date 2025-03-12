# Bash命令执行工具模块
# 设计说明：
# 1. 提供交互式Bash会话功能
# 2. 支持长时间运行的命令
# 3. 处理命令超时和中断
# 4. 支持后台运行和日志重定向

import asyncio
import os
from typing import Optional

from app.exceptions import ToolError
from app.tool.base import BaseTool, CLIResult, ToolResult


# Bash工具描述
# 功能说明：
# 1. 长时间运行命令：支持后台运行并重定向输出
# 2. 交互式命令：支持多次调用和输入
# 3. 超时处理：支持重试和后台运行
_BASH_DESCRIPTION = """Execute a bash command in the terminal.
* Long running commands: For commands that may run indefinitely, it should be run in the background and the output should be redirected to a file, e.g. command = `python3 app.py > server.log 2>&1 &`.
* Interactive: If a bash command returns exit code `-1`, this means the process is not yet finished. The assistant must then send a second call to terminal with an empty `command` (which will retrieve any additional logs), or it can send additional text (set `command` to the text) to STDIN of the running process, or it can send command=`ctrl+c` to interrupt the process.
* Timeout: If a command execution result says "Command timed out. Sending SIGINT to the process", the assistant should retry running the command in the background.
"""


# Bash会话类
# 功能特性：
# 1. 会话管理：启动、停止和状态跟踪
# 2. 命令执行：支持命令执行和输出获取
# 3. 超时控制：自动处理超时情况
# 4. 缓冲区管理：处理输入输出流
class _BashSession:
    """A session of a bash shell."""

    _started: bool
    _process: asyncio.subprocess.Process

    command: str = "/bin/bash"
    _output_delay: float = 0.2  # seconds
    _timeout: float = 120.0  # seconds
    _sentinel: str = "<<exit>>"

    def __init__(self):
        self._started = False
        self._timed_out = False

    async def start(self):
        """启动Bash会话"""
        if self._started:
            return

        # 创建子进程并设置管道
        self._process = await asyncio.create_subprocess_shell(
            self.command,
            preexec_fn=os.setsid,
            shell=True,
            bufsize=0,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        self._started = True

    def stop(self):
        """终止Bash会话"""
        if not self._started:
            raise ToolError("Session has not started.")
        if self._process.returncode is not None:
            return
        self._process.terminate()

    async def run(self, command: str):
        """在Bash会话中执行命令
        
        实现细节：
        1. 检查会话状态
        2. 写入命令并添加哨兵
        3. 等待输出直到遇到哨兵
        4. 处理超时情况
        5. 清理缓冲区
        """
        if not self._started:
            raise ToolError("Session has not started.")
        if self._process.returncode is not None:
            return ToolResult(
                system="tool must be restarted",
                error=f"bash has exited with returncode {self._process.returncode}",
            )
        if self._timed_out:
            raise ToolError(
                f"timed out: bash has not returned in {self._timeout} seconds and must be restarted",
            )

        # 确保进程的输入输出流可用
        assert self._process.stdin
        assert self._process.stdout
        assert self._process.stderr

        # 发送命令到进程
        self._process.stdin.write(
            command.encode() + f"; echo '{self._sentinel}'\n".encode()
        )
        await self._process.stdin.drain()

        # 读取进程输出直到遇到哨兵
        try:
            async with asyncio.timeout(self._timeout):
                while True:
                    await asyncio.sleep(self._output_delay)
                    # 直接从缓冲区读取，避免等待EOF
                    output = (
                        self._process.stdout._buffer.decode()
                    )  # pyright: ignore[reportAttributeAccessIssue]
                    if self._sentinel in output:
                        # 去除哨兵并退出循环
                        output = output[: output.index(self._sentinel)]
                        break
        except asyncio.TimeoutError:
            self._timed_out = True
            raise ToolError(
                f"timed out: bash has not returned in {self._timeout} seconds and must be restarted",
            ) from None

        # 处理输出格式
        if output.endswith("\n"):
            output = output[:-1]

        # 获取错误输出
        error = (
            self._process.stderr._buffer.decode()
        )  # pyright: ignore[reportAttributeAccessIssue]
        if error.endswith("\n"):
            error = error[:-1]

        # 清理缓冲区
        self._process.stdout._buffer.clear()  # pyright: ignore[reportAttributeAccessIssue]
        self._process.stderr._buffer.clear()  # pyright: ignore[reportAttributeAccessIssue]

        return CLIResult(output=output, error=error)


# Bash工具类
# 功能特性：
# 1. 会话管理：创建和重启会话
# 2. 命令执行：支持空命令和中断命令
# 3. 错误处理：统一的错误返回
class Bash(BaseTool):
    """A tool for executing bash commands"""

    name: str = "bash"
    description: str = _BASH_DESCRIPTION
    # 工具参数定义
    # - command: 要执行的bash命令
    #   - 可以为空（查看额外日志）
    #   - 可以是ctrl+c（中断当前进程）
    parameters: dict = {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "The bash command to execute. Can be empty to view additional logs when previous exit code is `-1`. Can be `ctrl+c` to interrupt the currently running process.",
            },
        },
        "required": ["command"],
    }

    _session: Optional[_BashSession] = None

    async def execute(
        self, command: str | None = None, restart: bool = False, **kwargs
    ) -> CLIResult:
        """执行Bash命令
        
        参数：
            command: 要执行的命令
            restart: 是否重启会话
        """
        # 处理会话重启
        if restart:
            if self._session:
                self._session.stop()
            self._session = _BashSession()
            await self._session.start()

            return ToolResult(system="tool has been restarted.")

        # 确保会话已启动
        if self._session is None:
            self._session = _BashSession()
            await self._session.start()

        # 执行命令
        if command is not None:
            return await self._session.run(command)

        raise ToolError("no command provided.")


if __name__ == "__main__":
    bash = Bash()
    rst = asyncio.run(bash.execute("ls -l"))
    print(rst)
