"""
配置管理模块 - 基于 pydantic-settings
"""

from enum import Enum
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LogLevel(str, Enum):
    """日志级别"""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class DBEngine(str, Enum):
    """数据库引擎"""

    SQLITE = "sqlite"
    MYSQL = "mysql"
    POSTGRESQL = "postgresql"


class Settings(BaseSettings):
    """系统配置管理类"""

    # 基本配置文件设置
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="trade__",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="ignore",
    )

    # 基础配置
    env: Literal["development", "production", "testing"] = "development"
    debug: bool = Field(default=True, description="调试模式")
    log_level: LogLevel = Field(default=LogLevel.INFO, description="日志级别")

    # 项目路径
    base_dir: Path = Path(__file__).parent.parent.parent.parent.resolve()

    tushare_token: str | None = Field(default=None, description="Tushare API令牌")

    def is_development(self) -> bool:
        """是否是开发环境"""
        return self.env == "development"

    def is_production(self) -> bool:
        """是否是生产环境"""
        return self.env == "production"

    def is_testing(self) -> bool:
        """是否是测试环境"""
        return self.env == "testing"


# 创建全局配置实例
settings = Settings()
