"""
配置管理模块测试
"""

from devtools import pprint

# import os
# from pathlib import Path
# import pytest
# from typing import Generator

# from trade.config import Settings
# from trade.config.settings import LogLevel, DataSource, DBEngine


# @pytest.fixture
# def env_vars() -> Generator[None, None, None]:
#     """临时设置环境变量"""
#     # 保存原始环境变量
#     original_vars = {}
#     test_vars = {
#         "ENV": "testing",
#         "DEBUG": "false",
#         "LOG_LEVEL": "error",
#         "DATA_SOURCE": "baostock",
#         "DB_ENGINE": "postgresql",
#     }

#     # 设置测试环境变量
#     for key, value in test_vars.items():
#         if key in os.environ:
#             original_vars[key] = os.environ[key]
#         os.environ[key] = value

#     yield

#     # 恢复原始环境变量
#     for key in test_vars:
#         if key in original_vars:
#             os.environ[key] = original_vars[key]
#         else:
#             del os.environ[key]


# def test_default_settings():
#     """测试默认配置"""
#     settings = Settings()
#     assert settings.env == "development"
#     assert settings.debug is True
#     assert settings.log_level == LogLevel.INFO
#     assert settings.data_source == DataSource.TUSHARE
#     assert settings.db_engine == DBEngine.SQLITE
#     assert settings.api_port == 8000


# def test_environment_variables(env_vars):
#     """测试环境变量覆盖"""
#     settings = Settings()
#     assert settings.env == "testing"
#     assert settings.debug is False
#     assert settings.log_level == LogLevel.ERROR
#     assert settings.data_source == DataSource.BAOSTOCK
#     assert settings.db_engine == DBEngine.POSTGRESQL


# def test_custom_settings():
#     """测试自定义配置"""
#     settings = Settings(
#         env="production",
#         debug=False,
#         log_level="critical",
#         data_source="baostock",
#         api_port=9000,
#     )
#     assert settings.env == "production"
#     assert settings.debug is False
#     assert settings.log_level == LogLevel.CRITICAL
#     assert settings.data_source == DataSource.BAOSTOCK
#     assert settings.api_port == 9000


# def test_validators():
#     """测试验证器"""
#     # Tushare数据源无token应该抛出异常
#     with pytest.raises(ValueError) as exc_info:
#         Settings(data_source="tushare", tushare_token=None)
#     assert "使用Tushare数据源时，必须提供tushare_token" in str(exc_info.value)

#     # 提供token应该通过验证
#     settings = Settings(data_source="tushare", tushare_token="test_token")
#     assert settings.tushare_token == "test_token"


# def test_helper_methods():
#     """测试辅助方法"""
#     # 开发环境
#     settings = Settings(env="development")
#     assert settings.is_development() is True
#     assert settings.is_production() is False
#     assert settings.is_testing() is False

#     # 生产环境
#     settings = Settings(env="production")
#     assert settings.is_development() is False
#     assert settings.is_production() is True
#     assert settings.is_testing() is False

#     # 测试环境
#     settings = Settings(env="testing")

#     assert settings.is_development() is False
#     assert settings.is_production() is False
#     assert settings.is_testing() is True


# def test_get_db_url():
#     """测试数据库URL生成"""
#     # SQLite
#     settings = Settings(db_engine="sqlite", db_path="./test.db")
#     assert settings.get_db_url() == "sqlite:///./test.db"

#     # 不支持的数据库引擎
#     with pytest.raises(NotImplementedError):
#         settings = Settings(db_engine="mysql")
#         settings.get_db_url()


def echo_config():
    """测试配置"""
    from trade.config.settings import settings

    pprint(settings)


if __name__ == "__main__":
    echo_config()
