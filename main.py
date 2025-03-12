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
    while True:
        try:
            # 用户输入处理
            # - 提供清晰的提示信息
            # - 支持多种退出命令
            # - 过滤空白输入
            prompt = input("Enter your prompt (or 'exit'/'quit' to quit): ")
            prompt_lower = prompt.lower()
            if prompt_lower in ["exit", "quit"]:
                logger.info("Goodbye!")
                break
            if not prompt.strip():
                logger.warning("Skipping empty prompt.")
                continue
            
            # 请求处理
            # - 提供处理状态反馈
            # - 异步执行Agent操作
            logger.warning("Processing your request...")
            await agent.run(prompt)
        except KeyboardInterrupt:
            # 中断处理
            # - 优雅退出程序
            # - 提供友好的退出提示
            logger.warning("Goodbye!")
            break


if __name__ == "__main__":
    # 程序入口
    # - 使用asyncio运行异步主函数
    # - 确保正确的事件循环管理
    asyncio.run(main())
