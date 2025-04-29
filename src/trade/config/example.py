"""
配置管理模块使用示例
"""

from trade.config import Settings
from trade.config.settings import settings


def config_usage_example():
    """配置使用示例"""
    # 使用已经创建的单例实例
    print(f"当前环境: {settings.env}")
    print(f"调试模式: {settings.debug}")
    print(f"日志级别: {settings.log_level}")
    print(f"数据源: {settings.data_source}")

    # 检查环境
    if settings.is_development():
        print("当前是开发环境")

    # 获取数据库URL
    db_url = settings.get_db_url()
    print(f"数据库URL: {db_url}")

    # 创建自定义配置实例
    custom_settings = Settings(
        env="production", debug=False, log_level="error", data_source="baostock"
    )
    print(f"\n自定义配置环境: {custom_settings.env}")
    print(f"自定义调试模式: {custom_settings.debug}")
    print(f"自定义日志级别: {custom_settings.log_level}")
    print(f"自定义数据源: {custom_settings.data_source}")


if __name__ == "__main__":
    config_usage_example()
