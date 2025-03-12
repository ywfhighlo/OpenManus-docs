# 流程工厂模块
# 设计说明：
# 1. 工厂模式：实现流程实例的统一创建接口
# 2. 类型管理：使用枚举确保流程类型的安全性
# 3. 配置灵活：支持多种Agent配置方式
# 4. 扩展支持：预留新流程类型的扩展接口
# 5. 错误处理：完善的异常处理机制

from typing import Dict, List, Union

from app.agent.base import BaseAgent
from app.flow.base import BaseFlow, FlowType
from app.flow.planning import PlanningFlow


class FlowFactory:
    """
    Factory for creating different types of flows with support for multiple agents
    
    流程工厂类
    
    核心功能：
    1. 流程创建：提供统一的流程实例化接口
    2. 类型验证：确保流程类型的正确性和安全性
    3. 参数管理：支持灵活的Agent配置和参数传递
    4. 扩展性：支持新流程类型的动态添加
    5. 错误处理：优雅处理未知类型和参数错误
    """

    @staticmethod
    def create_flow(
        flow_type: FlowType,
        agents: Union[BaseAgent, List[BaseAgent], Dict[str, BaseAgent]],
        **kwargs,
    ) -> BaseFlow:
        """
        Create a flow instance of the specified type
        
        流程创建方法
        
        实现说明：
        1. 静态方法：
           - 无需实例化工厂类
           - 全局统一的创建接口
           - 简化调用方式
        
        2. 参数设计：
           - flow_type: 使用枚举确保类型安全
           - agents: 支持多种Agent配置格式
           - kwargs: 支持额外参数的灵活传递
        
        3. 类型映射：
           - 使用字典维护类型映射关系
           - 支持动态扩展新的流程类型
           - 便于维护和更新
        
        4. 错误处理：
           - 验证流程类型的有效性
           - 处理未知类型的异常情况
           - 提供清晰的错误信息
        
        返回值：
        - BaseFlow: 创建的流程实例
        - 确保返回类型符合基类接口
        
        异常：
        - ValueError: 当指定了未知的流程类型
        """
        # 流程类型映射表
        # 设计说明：
        # 1. 类型注册：
        #    - 将流程类型枚举映射到具体的实现类
        #    - 便于集中管理所有可用的流程类型
        # 2. 当前支持：
        #    - PLANNING: 规划流程类型
        #      - 用于任务的分解和执行
        #      - 支持复杂任务的规划管理
        flows = {
            FlowType.PLANNING: PlanningFlow,
        }

        # 获取具体的流程类
        flow_class = flows.get(flow_type)
        if not flow_class:
            raise ValueError(f"Unknown flow type: {flow_type}")

        # 创建并返回流程实例
        return flow_class(agents, **kwargs)
