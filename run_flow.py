# 流程执行入口模块
# 设计说明：
# 1. 流程管理：使用FlowFactory创建和管理执行流程
# 2. 多Agent支持：支持多个Agent的协同工作
# 3. 超时控制：设置合理的执行时间限制
# 4. 错误处理：完整的异常捕获和恢复机制
# 5. 性能监控：记录执行时间和状态信息

import asyncio
import time

from app.agent.manus import Manus
from app.flow.base import FlowType
from app.flow.flow_factory import FlowFactory
from app.logger import logger


async def run_flow():
    """
    Main entry point for running flows with agents.
    
    流程执行主函数
    
    功能说明：
    1. Agent配置：
       - 初始化Agent字典
       - 支持多Agent注册
    2. 交互处理：
       - 用户输入处理
       - 退出命令支持
    3. 流程控制：
       - 使用工厂模式创建流程
       - 支持不同类型的流程
    4. 执行管理：
       - 超时控制（1小时）
       - 性能监控
    5. 异常处理：
       - 超时处理
       - 键盘中断
       - 运行时异常
    """
    # Agent配置
    # - 使用字典管理多个Agent
    # - 当前支持Manus Agent
    agents = {
        "manus": Manus(),
    }

    try:
        prompt = input("Enter your prompt: ")

        if prompt.strip().isspace() or not prompt:
            logger.warning("Empty prompt provided.")
            return

        flow = FlowFactory.create_flow(
            flow_type=FlowType.PLANNING,
            agents=agents,
        )
        logger.warning("Processing your request...")

        try:
            start_time = time.time()
            result = await asyncio.wait_for(
                flow.execute(prompt),
                timeout=3600,  # 60 minute timeout for the entire execution
            )
            elapsed_time = time.time() - start_time
            logger.info(f"Request processed in {elapsed_time:.2f} seconds")
            logger.info(result)
        except asyncio.TimeoutError:
            logger.error("Request processing timed out after 1 hour")
            logger.info(
                "Operation terminated due to timeout. Please try a simpler request."
            )

    except KeyboardInterrupt:
        logger.info("Operation cancelled by user.")
    except Exception as e:
        logger.error(f"Error: {str(e)}")


if __name__ == "__main__":
    # 程序入口
    # - 使用asyncio运行异步函数
    # - 确保正确的事件循环管理
    asyncio.run(run_flow())
