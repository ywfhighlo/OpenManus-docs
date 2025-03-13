# OpenManus命令行入口模块
# 设计说明：
# 1. 交互模式：提供命令行交互界面
# 2. 异步处理：使用asyncio支持异步操作
# 3. 错误处理：完整的异常捕获机制
# 4. 日志记录：集成日志系统记录运行状态
# 5. 优雅退出：支持多种退出方式

import asyncio

from app.agent.manus import Manus
from app.logger import logger


async def main():
    """
    Main entry point for the OpenManus CLI.
    
    命令行主函数
    
    功能说明：
    1. Agent初始化：创建Manus实例
    2. 交互循环：持续接收用户输入
    3. 命令处理：
       - 退出命令：exit/quit
       - 空输入处理
       - 正常请求处理
    4. 异常处理：
       - 键盘中断
       - 运行时异常
    5. 状态反馈：通过日志系统提供执行状态
    """
    agent = Manus()
    try:
        prompt = input("Enter your prompt: ")
        if not prompt.strip():
            logger.warning("Empty prompt provided.")
            return

        logger.warning("Processing your request...")
        await agent.run(prompt)
        logger.info("Request processing completed.")
    except KeyboardInterrupt:
        logger.warning("Operation interrupted.")


if __name__ == "__main__":
    # 程序入口
    # - 使用asyncio运行异步主函数
    # - 确保正确的事件循环管理
    asyncio.run(main())
