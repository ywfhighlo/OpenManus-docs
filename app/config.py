# 配置管理模块
# 设计说明：
# 1. 提供全局配置管理
# 2. 支持多LLM模型配置
# 3. 实现单例模式确保配置一致性
# 4. 支持配置文件加载和覆盖

import threading
import tomllib
from pathlib import Path
from typing import Dict

from pydantic import BaseModel, Field


def get_project_root() -> Path:
    """
    Get the project root directory
    
    获取项目根目录
    
    功能：
    1. 路径解析：解析当前文件路径
    2. 目录定位：定位到项目根目录
    """
    return Path(__file__).resolve().parent.parent


# 全局路径配置
PROJECT_ROOT = get_project_root()
WORKSPACE_ROOT = PROJECT_ROOT / "workspace"


class LLMSettings(BaseModel):
    """
    LLM模型配置类
    
    功能特性：
    1. 模型参数：定义模型名称、URL等基本参数
    2. API配置：管理API密钥和版本信息
    3. 运行参数：控制最大token数和温度等
    4. 类型验证：使用Pydantic进行参数验证
    """
    model: str = Field(..., description="Model name")
    base_url: str = Field(..., description="API base URL")
    api_key: str = Field(..., description="API key")
    max_tokens: int = Field(4096, description="Maximum number of tokens per request")
    temperature: float = Field(1.0, description="Sampling temperature")
    api_type: str = Field(..., description="AzureOpenai or Openai")
    api_version: str = Field(..., description="Azure Openai version if AzureOpenai")


class AppConfig(BaseModel):
    """
    应用配置类
    
    功能特性：
    1. LLM配置：管理多个LLM模型的配置
    2. 参数验证：使用Pydantic确保配置有效性
    """
    llm: Dict[str, LLMSettings]


class Config:
    """
    配置管理类（单例模式）
    
    功能特性：
    1. 单例实现：确保全局配置唯一性
    2. 线程安全：使用锁机制保护配置
    3. 延迟加载：首次访问时才加载配置
    4. 配置覆盖：支持默认值和自定义值
    """
    _instance = None
    _lock = threading.Lock()
    _initialized = False

    def __new__(cls):
        """
        创建单例实例
        
        功能：
        1. 实例检查：确保只创建一个实例
        2. 线程安全：使用锁保护实例创建
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """
        初始化配置
        
        功能：
        1. 状态检查：避免重复初始化
        2. 配置加载：加载初始配置
        """
        if not self._initialized:
            with self._lock:
                if not self._initialized:
                    self._config = None
                    self._load_initial_config()
                    self._initialized = True

    @staticmethod
    def _get_config_path() -> Path:
        """
        获取配置文件路径
        
        功能：
        1. 路径查找：查找配置文件位置
        2. 备选方案：支持示例配置文件
        3. 错误处理：文件不存在时抛出异常
        """
        root = PROJECT_ROOT
        config_path = root / "config" / "config.toml"
        if config_path.exists():
            return config_path
        example_path = root / "config" / "config.example.toml"
        if example_path.exists():
            return example_path
        raise FileNotFoundError("No configuration file found in config directory")

    def _load_config(self) -> dict:
        """
        加载配置文件
        
        功能：
        1. 文件读取：读取TOML配置文件
        2. 格式转换：转换为Python字典
        """
        config_path = self._get_config_path()
        with config_path.open("rb") as f:
            return tomllib.load(f)

    def _load_initial_config(self):
        """
        加载初始配置
        
        功能：
        1. 基础配置：加载基本LLM配置
        2. 配置覆盖：处理自定义配置覆盖
        3. 默认值：设置默认参数值
        4. 验证转换：转换为Pydantic模型
        """
        raw_config = self._load_config()
        base_llm = raw_config.get("llm", {})
        llm_overrides = {
            k: v for k, v in raw_config.get("llm", {}).items() if isinstance(v, dict)
        }

        default_settings = {
            "model": base_llm.get("model"),
            "base_url": base_llm.get("base_url"),
            "api_key": base_llm.get("api_key"),
            "max_tokens": base_llm.get("max_tokens", 4096),
            "temperature": base_llm.get("temperature", 1.0),
            "api_type": base_llm.get("api_type", ""),
            "api_version": base_llm.get("api_version", ""),
        }

        config_dict = {
            "llm": {
                "default": default_settings,
                **{
                    name: {**default_settings, **override_config}
                    for name, override_config in llm_overrides.items()
                },
            }
        }

        self._config = AppConfig(**config_dict)

    @property
    def llm(self) -> Dict[str, LLMSettings]:
        """
        获取LLM配置
        
        功能：
        1. 配置访问：提供LLM配置的访问接口
        2. 类型保证：确保返回正确的配置类型
        """
        return self._config.llm


# 全局配置实例
config = Config()
