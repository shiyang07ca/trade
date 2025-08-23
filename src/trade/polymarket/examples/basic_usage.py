"""
Polymarket 客户端基础使用示例

演示如何使用重构后的 Polymarket 客户端进行基本操作
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta

from ..client import PolymarketClient
from ..client.config import ClientConfig
from ..types import OrderSide


async def main():
    """主演示函数"""
    # 配置日志
    logging.basicConfig(level=logging.INFO)

    print("=== Polymarket 客户端演示 ===\n")

    # 1. 初始化客户端
    print("1. 初始化客户端...")
    config = ClientConfig.from_env()
    client = PolymarketClient(config, enable_storage=True)

    # 2. 健康检查
    print("\n2. 系统健康检查:")
    health = client.health_check()
    print(f"   网络连接: {'✓' if health.get('web3_connected') else '✗'}")
    print(f"   数据存储: {'✓' if health.get('services', {}).get('storage') else '✗'}")
    print(f"   钱包地址: {health.get('wallet_address', 'Unknown')}")
    print(f"   运行模式: {'模拟' if config.dry_run else '实盘'}")

    # 3. 获取市场数据
    print("\n3. 获取热门市场:")
    try:
        markets = await client.get_markets(limit=5)
        for i, market in enumerate(markets[:3], 1):
            print(f"   {i}. {market.question}")
            print(f"      交易量: ${market.volume:,.2f}")
            print(f"      状态: {'活跃' if market.is_active else '非活跃'}")
            if market.outcomes:
                print(f"      结果数: {len(market.outcomes)}")
            print()
    except Exception as e:
        print(f"   获取市场数据失败: {e}")

    # 4. 获取投资组合信息
    print("4. 投资组合信息:")
    try:
        balance_info = await client.get_balance_info()
        print(f"   USDC 余额: ${balance_info.usdc_balance:,.2f}")
        print(f"   持仓价值: ${balance_info.total_position_value:,.2f}")
        print(f"   总资产: ${balance_info.total_balance:,.2f}")

        positions = await client.get_positions()
        print(f"   持仓数量: {len(positions)}")

        if positions:
            print("   前3个持仓:")
            for pos in positions[:3]:
                pnl_color = "+" if pos.unrealized_pnl >= 0 else ""
                print(f"     - {pos.outcome}: {pos.size:.2f} 份额")
                print(
                    f"       成本: ${pos.cost_basis:.2f}, 市值: ${pos.market_value:.2f}"
                )
                print(
                    f"       盈亏: {pnl_color}{pos.unrealized_pnl:.2f} ({pos.unrealized_pnl_pct:.1f}%)"
                )
    except Exception as e:
        print(f"   获取投资组合信息失败: {e}")

    # 5. 演示订单验证
    print("\n5. 订单验证演示:")
    if markets and markets[0].outcomes:
        token_id = markets[0].outcomes[0].token_id

        # 验证一个有效订单
        validation = client.validator.validate_limit_order(
            token_id, OrderSide.BUY, 10.0, 0.55
        )
        print(f"   有效订单验证: {'✓' if validation['valid'] else '✗'}")

        # 验证一个无效订单
        validation = client.validator.validate_limit_order(
            token_id,
            OrderSide.BUY,
            -5.0,
            1.5,  # 无效的大小和价格
        )
        print(f"   无效订单验证: {'✗' if not validation['valid'] else '✓'}")
        if validation["errors"]:
            print(f"   错误信息: {validation['errors']}")

    # 6. 缓存统计
    print("\n6. 缓存统计:")
    cache_stats = client.get_cache_stats()
    print(f"   缓存条目: {cache_stats.get('total_entries', 0)}")
    print(f"   命中率: {cache_stats.get('hit_rate', 0):.1%}")
    print(f"   内存使用: {cache_stats.get('memory_usage_estimate', 0) / 1024:.1f} KB")

    # 7. 历史数据演示（如果有合适的代币）
    print("\n7. 历史数据演示:")
    if markets and markets[0].outcomes:
        token_id = markets[0].outcomes[0].token_id
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=7)

        try:
            historical_prices = await client.get_historical_prices(
                token_id, start_date, end_date, "1h"
            )
            print(f"   获取到 {len(historical_prices)} 个历史价格数据点")

            if historical_prices:
                first_price = historical_prices[0]
                last_price = historical_prices[-1]
                print(
                    f"   价格变化: ${first_price.get('price', 0):.4f} -> ${last_price.get('price', 0):.4f}"
                )
        except Exception as e:
            print(f"   获取历史数据失败: {e}")

    # 8. 数据库统计（如果启用了存储）
    if client.repository:
        print("\n8. 数据库统计:")
        try:
            db_stats = client.repository.get_stats()
            table_stats = db_stats.get("table_stats", {})
            print(f"   市场记录: {table_stats.get('markets', 0)}")
            print(f"   价格记录: {table_stats.get('prices', 0)}")
            print(f"   交易记录: {table_stats.get('trades', 0)}")

            db_size = db_stats.get("database_size", {})
            print(f"   数据库大小: {db_size.get('file_size_mb', 0):.2f} MB")
        except Exception as e:
            print(f"   获取数据库统计失败: {e}")

    print("\n=== 演示完成 ===")
    print(f"客户端信息: {client}")


if __name__ == "__main__":
    # 运行演示
    asyncio.run(main())
