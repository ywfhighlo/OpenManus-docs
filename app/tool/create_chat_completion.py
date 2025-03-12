# 聊天补全工具模块
# 设计说明：
# 1. 提供结构化的聊天补全功能
# 2. 支持多种输出类型转换
# 3. 自动生成JSON Schema
# 4. 灵活的参数验证

from typing import Any, List, Optional, Type, Union, get_args, get_origin

from pydantic import BaseModel, Field

from app.tool import BaseTool


# 聊天补全工具类
# 功能特性：
# 1. 类型映射和转换
# 2. 动态参数构建
# 3. 结构化输出
# 4. 类型验证和转换
class CreateChatCompletion(BaseTool):
    name: str = "create_chat_completion"
    description: str = (
        "Creates a structured completion with specified output formatting."
    )

    # 类型映射表
    # Python类型到JSON Schema类型的映射关系
    type_mapping: dict = {
        str: "string",
        int: "integer",
        float: "number",
        bool: "boolean",
        dict: "object",
        list: "array",
    }
    response_type: Optional[Type] = None
    required: List[str] = Field(default_factory=lambda: ["response"])

    def __init__(self, response_type: Optional[Type] = str):
        """初始化聊天补全工具
        
        参数：
            response_type: 期望的响应类型
        """
        super().__init__()
        self.response_type = response_type
        self.parameters = self._build_parameters()

    def _build_parameters(self) -> dict:
        """构建参数模式
        
        功能：
        1. 处理字符串类型
        2. 处理Pydantic模型
        3. 处理其他类型
        """
        if self.response_type == str:
            return {
                "type": "object",
                "properties": {
                    "response": {
                        "type": "string",
                        "description": "The response text that should be delivered to the user.",
                    },
                },
                "required": self.required,
            }

        if isinstance(self.response_type, type) and issubclass(
            self.response_type, BaseModel
        ):
            schema = self.response_type.model_json_schema()
            return {
                "type": "object",
                "properties": schema["properties"],
                "required": schema.get("required", self.required),
            }

        return self._create_type_schema(self.response_type)

    def _create_type_schema(self, type_hint: Type) -> dict:
        """创建类型的JSON Schema
        
        功能：
        1. 处理基本类型
        2. 处理列表类型
        3. 处理字典类型
        4. 处理联合类型
        """
        origin = get_origin(type_hint)
        args = get_args(type_hint)

        # 处理基本类型
        if origin is None:
            return {
                "type": "object",
                "properties": {
                    "response": {
                        "type": self.type_mapping.get(type_hint, "string"),
                        "description": f"Response of type {type_hint.__name__}",
                    }
                },
                "required": self.required,
            }

        # 处理列表类型
        if origin is list:
            item_type = args[0] if args else Any
            return {
                "type": "object",
                "properties": {
                    "response": {
                        "type": "array",
                        "items": self._get_type_info(item_type),
                    }
                },
                "required": self.required,
            }

        # 处理字典类型
        if origin is dict:
            value_type = args[1] if len(args) > 1 else Any
            return {
                "type": "object",
                "properties": {
                    "response": {
                        "type": "object",
                        "additionalProperties": self._get_type_info(value_type),
                    }
                },
                "required": self.required,
            }

        # 处理联合类型
        if origin is Union:
            return self._create_union_schema(args)

        return self._build_parameters()

    def _get_type_info(self, type_hint: Type) -> dict:
        """获取类型信息
        
        功能：
        1. 处理Pydantic模型
        2. 处理基本类型
        """
        if isinstance(type_hint, type) and issubclass(type_hint, BaseModel):
            return type_hint.model_json_schema()

        return {
            "type": self.type_mapping.get(type_hint, "string"),
            "description": f"Value of type {getattr(type_hint, '__name__', 'any')}",
        }

    def _create_union_schema(self, types: tuple) -> dict:
        """创建联合类型的Schema"""
        return {
            "type": "object",
            "properties": {
                "response": {"anyOf": [self._get_type_info(t) for t in types]}
            },
            "required": self.required,
        }

    async def execute(self, required: list | None = None, **kwargs) -> Any:
        """执行聊天补全
        
        功能：
        1. 处理必需字段
        2. 类型转换
        3. 结果验证
        
        参数：
            required: 必需字段列表
            **kwargs: 响应数据
        
        返回：
            根据response_type转换后的响应
        """
        required = required or self.required

        # 处理必需字段列表
        if isinstance(required, list) and len(required) > 0:
            if len(required) == 1:
                required_field = required[0]
                result = kwargs.get(required_field, "")
            else:
                # 返回多个字段的字典
                return {field: kwargs.get(field, "") for field in required}
        else:
            required_field = "response"
            result = kwargs.get(required_field, "")

        # 类型转换逻辑
        if self.response_type == str:
            return result

        if isinstance(self.response_type, type) and issubclass(
            self.response_type, BaseModel
        ):
            return self.response_type(**kwargs)

        if get_origin(self.response_type) in (list, dict):
            return result  # 假设结果已经是正确的格式

        try:
            return self.response_type(result)
        except (ValueError, TypeError):
            return result
