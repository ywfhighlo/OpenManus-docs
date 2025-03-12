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

    while True:
        try:
            # 用户输入处理
            # - 提供清晰的提示信息
            # - 支持exit退出命令
            prompt = input("Enter your prompt (or 'exit' to quit): ")
            if prompt.lower() == "exit":
                logger.info("Goodbye!")
                break

            # 流程创建和配置
            # - 使用规划类型流程
            # - 配置已注册的agents
            flow = FlowFactory.create_flow(
                flow_type=FlowType.PLANNING,
                agents=agents,
            )
            if prompt.strip().isspace():
                logger.warning("Skipping empty prompt.")
                continue
            logger.warning("Processing your request...")

            try:
                # 执行控制
                # - 记录开始时间
                # - 设置超时限制
                # - 等待执行完成
                start_time = time.time()
                result = await asyncio.wait_for(
                    flow.execute(prompt),
                    timeout=3600,  # 60分钟超时限制
                )
                # 性能统计
                # - 计算执行时间
                # - 记录执行结果
                elapsed_time = time.time() - start_time
                logger.info(f"Request processed in {elapsed_time:.2f} seconds")
                logger.info(result)
            except asyncio.TimeoutError:
                # 超时处理
                # - 记录错误信息
                # - 提供用户建议
                logger.error("Request processing timed out after 1 hour")
                logger.info(
                    "Operation terminated due to timeout. Please try a simpler request."
                )

        except KeyboardInterrupt:
            # 中断处理
            # - 记录用户取消操作
            logger.info("Operation cancelled by user.")
        except Exception as e:
            # 异常处理
            # - 记录详细错误信息
            logger.error(f"Error: {str(e)}")


if __name__ == "__main__":
    # 程序入口
    # - 使用asyncio运行异步函数
    # - 确保正确的事件循环管理
    asyncio.run(run_flow())
