#!/usr/bin/env python
# MCP代理运行模块
# 提供多种方式与MCP服务器交互的命令行工具，支持单次、交互式和默认模式
import argparse
import asyncio
import sys

from app.agent.mcp import MCPAgent
from app.config import config
from app.logger import logger


class MCPRunner:
    """Runner class for MCP Agent with proper path handling and configuration."""

    def __init__(self):
        # 初始化根路径和服务器引用
        self.root_path = config.root_path
        self.server_reference = "app.mcp.server"
        self.agent = MCPAgent()

    async def initialize(
        self,
        connection_type: str,
        server_url: str | None = None,
    ) -> None:
        """Initialize the MCP agent with the appropriate connection."""
        # 根据连接类型初始化MCP代理
        logger.info(f"Initializing MCPAgent with {connection_type} connection...")

        if connection_type == "stdio":
            # 使用标准输入输出连接
            await self.agent.initialize(
                connection_type="stdio",
                command=sys.executable,
                args=["-m", self.server_reference],
            )
        else:  # sse
            # 使用服务器发送事件(SSE)连接
            await self.agent.initialize(connection_type="sse", server_url=server_url)

        logger.info(f"Connected to MCP server via {connection_type}")

    async def run_interactive(self) -> None:
        """Run the agent in interactive mode."""
        # 交互模式：持续接收用户输入直到退出
        print("\nMCP Agent Interactive Mode (type 'exit' to quit)\n")
        while True:
            user_input = input("\nEnter your request: ")
            if user_input.lower() in ["exit", "quit", "q"]:
                break
            response = await self.agent.run(user_input)
            print(f"\nAgent: {response}")

    async def run_single_prompt(self, prompt: str) -> None:
        """Run the agent with a single prompt."""
        # 单次提示模式：执行单个命令然后退出
        await self.agent.run(prompt)

    async def run_default(self) -> None:
        """Run the agent in default mode."""
        # 默认模式：执行一次提示并显示处理进度
        prompt = input("Enter your prompt: ")
        if not prompt.strip():
            logger.warning("Empty prompt provided.")
            return

        logger.warning("Processing your request...")
        await self.agent.run(prompt)
        logger.info("Request processing completed.")

    async def cleanup(self) -> None:
        """Clean up agent resources."""
        # 清理代理资源并结束会话
        await self.agent.cleanup()
        logger.info("Session ended")


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="Run the MCP Agent")
    parser.add_argument(
        "--connection",
        "-c",
        choices=["stdio", "sse"],
        default="stdio",
        help="Connection type: stdio or sse",
    )
    parser.add_argument(
        "--server-url",
        default="http://127.0.0.1:8000/sse",
        help="URL for SSE connection",
    )
    parser.add_argument(
        "--interactive", "-i", action="store_true", help="Run in interactive mode"
    )
    parser.add_argument("--prompt", "-p", help="Single prompt to execute and exit")
    return parser.parse_args()


async def run_mcp() -> None:
    """Main entry point for the MCP runner."""
    # MCP运行器的主入口点
    args = parse_args()
    runner = MCPRunner()

    try:
        # 根据参数初始化和运行MCP
        await runner.initialize(args.connection, args.server_url)

        if args.prompt:
            # 单次提示模式
            await runner.run_single_prompt(args.prompt)
        elif args.interactive:
            # 交互模式
            await runner.run_interactive()
        else:
            # 默认模式
            await runner.run_default()

    except KeyboardInterrupt:
        # 处理用户中断
        logger.info("Program interrupted by user")
    except Exception as e:
        # 处理运行时错误
        logger.error(f"Error running MCPAgent: {str(e)}", exc_info=True)
        sys.exit(1)
    finally:
        # 确保清理资源
        await runner.cleanup()


# 当作为脚本直接运行时执行run_mcp
if __name__ == "__main__":
    asyncio.run(run_mcp())
