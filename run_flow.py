# 流程执行模块
# 提供命令行接口运行OpenManus工作流，支持规划和执行复杂任务
import asyncio
import time

from app.agent.manus import Manus
from app.flow.base import FlowType
from app.flow.flow_factory import FlowFactory
from app.logger import logger


async def run_flow():
    # 初始化代理字典，当前只使用Manus代理
    agents = {
        "manus": Manus(),
    }

    try:
        # 从命令行获取用户输入的提示词
        prompt = input("Enter your prompt: ")

        if prompt.strip().isspace() or not prompt:
            logger.warning("Empty prompt provided.")
            return

        # 使用工厂创建PLANNING类型的工作流，并传入代理
        flow = FlowFactory.create_flow(
            flow_type=FlowType.PLANNING,
            agents=agents,
        )
        logger.warning("Processing your request...")

        try:
            # 执行流程并计时，设置最大执行时间为1小时
            start_time = time.time()
            result = await asyncio.wait_for(
                flow.execute(prompt),
                timeout=3600,  # 60分钟超时，用于整个执行过程
            )
            elapsed_time = time.time() - start_time
            logger.info(f"Request processed in {elapsed_time:.2f} seconds")
            logger.info(result)
        except asyncio.TimeoutError:
            # 超时处理
            logger.error("Request processing timed out after 1 hour")
            logger.info(
                "Operation terminated due to timeout. Please try a simpler request."
            )

    except KeyboardInterrupt:
        # 用户中断处理
        logger.info("Operation cancelled by user.")
    except Exception as e:
        # 一般错误处理
        logger.error(f"Error: {str(e)}")


# 当作为主程序运行时，执行run_flow函数
if __name__ == "__main__":
    asyncio.run(run_flow())
