# 主程序模块
# 提供简单的命令行接口直接运行Manus代理，处理单次用户请求
import asyncio

from app.agent.manus import Manus
from app.logger import logger


async def main():
    # 初始化Manus代理
    agent = Manus()
    try:
        # 获取用户输入的提示词
        prompt = input("Enter your prompt: ")
        if not prompt.strip():
            logger.warning("Empty prompt provided.")
            return

        # 处理请求并显示进度
        logger.warning("Processing your request...")
        await agent.run(prompt)
        logger.info("Request processing completed.")
    except KeyboardInterrupt:
        # 处理用户中断
        logger.warning("Operation interrupted.")


# 当作为主程序运行时执行main函数
if __name__ == "__main__":
    asyncio.run(main())
