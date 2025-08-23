"""
Polymarket客户端简化使用示例 - 重构版

展示新版本客户端的基本使用方法
"""

from trade.polymarket import PolymarketClient, ClientConfig, OrderSide


def main():
    """主函数"""
    # 方式1: 使用环境变量配置
    client = PolymarketClient()
    
    # 方式2: 手动配置
    # config = ClientConfig(
    #     private_key="0x...",
    #     dry_run=True,
    #     enable_cache=True,
    #     enable_storage=False
    # )
    # client = PolymarketClient(config)
    
    print(f"初始化客户端: {client}")
    
    # 健康检查
    print("\n=== 健康检查 ===")
    health = client.health_check()
    print(f"健康状态: {health['healthy']}")
    print(f"钱包地址: {health['wallet_address']}")
    print(f"模拟模式: {health['dry_run_mode']}")
    
    # 获取市场数据
    print("\n=== 获取市场数据 ===")
    try:
        markets = client.get_markets(limit=5)
        print(f"获取到 {len(markets)} 个市场")
        
        if markets:
            market = markets[0]
            print(f"市场示例: {market.question}")
            print(f"状态: {market.status.value}")
            print(f"交易量: ${market.volume:,.2f}")
            print(f"结果数量: {len(market.outcomes)}")
            
            # 获取价格信息
            if market.outcomes:
                token_id = market.outcomes[0].token_id
                price = client.get_price(token_id, "BUY")
                mid_price = client.get_mid_price(token_id)
                print(f"买入价格: {price:.3f}")
                print(f"中间价格: {mid_price:.3f}")
    
    except Exception as e:
        print(f"获取市场数据失败: {e}")
    
    # 搜索市场
    print("\n=== 搜索市场 ===")
    try:
        search_results = client.search_markets("election", limit=3)
        print(f"搜索 'election' 找到 {len(search_results)} 个市场")
        for market in search_results:
            print(f"- {market.question[:80]}...")
    
    except Exception as e:
        print(f"搜索市场失败: {e}")
    
    # 获取余额信息
    print("\n=== 余额信息 ===")
    try:
        balance = client.get_balance_info()
        print(f"USDC余额: ${balance.usdc_balance:.2f}")
        print(f"持仓价值: ${balance.total_position_value:.2f}")
        print(f"可用余额: ${balance.available_balance:.2f}")
        print(f"总权益: ${balance.total_equity:.2f}")
    
    except Exception as e:
        print(f"获取余额失败: {e}")
    
    # 模拟创建订单
    print("\n=== 模拟创建订单 ===")
    if markets and markets[0].outcomes:
        try:
            token_id = markets[0].outcomes[0].token_id
            
            # 计算建议仓位大小
            suggested_size = client.calculate_position_size(
                available_balance=100.0,
                price=0.55,
                max_risk_pct=0.1
            )
            print(f"建议仓位大小: {suggested_size:.2f}")
            
            # 创建限价订单 (模拟模式)
            response = client.create_limit_order(
                token_id=token_id,
                side=OrderSide.BUY,
                size=10.0,
                price=0.55
            )
            
            if response:
                print(f"订单创建成功 (模拟): {response.get('status', 'unknown')}")
                if 'order' in response:
                    order = response['order']
                    print(f"订单ID: {order['id']}")
                    print(f"方向: {order['side']}")
                    print(f"数量: {order['size']}")
                    print(f"价格: {order['price']}")
        
        except Exception as e:
            print(f"创建订单失败: {e}")
    
    # 获取订单列表
    print("\n=== 获取订单列表 ===")
    try:
        orders = client.get_orders()
        print(f"当前订单数量: {len(orders)}")
        
        for order in orders[:3]:  # 只显示前3个
            print(f"订单 {order.id}: {order.side.value} {order.size} @ {order.price}")
    
    except Exception as e:
        print(f"获取订单失败: {e}")
    
    # 缓存统计
    if client.cache:
        print("\n=== 缓存统计 ===")
        print(f"缓存条目数量: {client.cache.size()}")
    
    # 存储统计
    if client.storage:
        print("\n=== 存储统计 ===")
        stats = client.storage.get_stats()
        print(f"存储统计: {stats}")
    
    print("\n=== 演示完成 ===")


if __name__ == "__main__":
    main()

