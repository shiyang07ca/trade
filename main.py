#!/usr/bin/env python
"""
交易策略分析工具 - 主入口
"""

import sys
from trade.config.settings import settings


def main():
    """主函数"""
    print(f"交易系统启动，当前环境：{settings.env}")
    print(f"调试模式：{settings.debug}")
    print(f"日志级别：{settings.log_level}")
    print(f"数据源：{settings.data_source}")

    if settings.is_development():
        print("当前处于开发环境")
    elif settings.is_production():
        print("当前处于生产环境")
    elif settings.is_testing():
        print("当前处于测试环境")

    # 这里可以添加更多的初始化和应用逻辑


if __name__ == "__main__":
    sys.exit(main())
