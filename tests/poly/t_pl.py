"""
Polymarket API 演示示例
基于 py-clob-client 的完整使用场景演示

核心功能:
- 市场数据查询
- 订单管理 (创建、查询、取消)
- 持仓管理
- 实时数据订阅
- 错误处理和最佳实践

使用方法:
1. 安装依赖: pip install py-clob-client websockets
2. 设置环境变量 (可选): export POLYMARKET_PRIVATE_KEY="your_private_key"
3. 运行示例: python tests/t_pl.py

注意事项:
- 只读操作无需私钥，交易操作需要设置私钥
- 请在测试网络或小额资金下谨慎测试交易功能
- WebSocket 功能需要网络连接
"""

import asyncio
import json
import logging
import os
import time
from decimal import Decimal

import websockets
from py_clob_client.client import ClobClient
from py_clob_client.constants import POLYGON

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class PolymarketDemo:
    """Polymarket 交易演示类"""

    def __init__(self, private_key: str | None = None):
        """
        初始化客户端

        Args:
            private_key: 私钥，如果为空则从环境变量读取
        """
        self.private_key = private_key or os.getenv("POLYMARKET_PRIVATE_KEY")
        if not self.private_key:
            logger.warning("未提供私钥，只能进行只读操作")

        # 初始化客户端
        try:
            self.client = ClobClient(
                host="https://clob.polymarket.com",
                key=self.private_key,
                chain_id=POLYGON,
            )

            # 如果有私钥，尝试设置API凭证
            if self.private_key:
                try:
                    self.client.set_api_creds(self.client.create_or_derive_api_creds())
                    logger.info("API 凭证设置成功")
                except Exception as e:
                    logger.warning(f"API 凭证设置失败: {e}")

        except Exception as e:
            logger.error(f"客户端初始化失败: {e}")
            raise

    def check_client_methods(self):
        """检查客户端支持的方法"""
        available_methods = []
        methods_to_check = [
            "get_markets",
            "get_market",
            "get_order_book",
            "get_orders",
            "get_balances",
            "get_trades",
            "create_order",
            "cancel_order",
            "cancel_all",
            "set_api_creds",
            "create_or_derive_api_creds",
        ]

        for method_name in methods_to_check:
            if hasattr(self.client, method_name):
                available_methods.append(method_name)

        logger.info(f"客户端支持的方法: {available_methods}")
        return available_methods

    async def get_markets(self, limit: int = 20) -> list[dict]:
        """获取市场列表"""
        try:
            # 检查方法是否存在
            if not hasattr(self.client, "get_markets"):
                logger.warning("客户端不支持 get_markets 方法")
                return []

            # py-clob-client 的 get_markets 方法可能不接受 limit 参数
            markets = self.client.get_markets()

            # 如果返回的是协程，则等待
            if hasattr(markets, "__await__"):
                markets = await markets

            logger.info(f"获取到 {len(markets) if markets else 0} 个市场")
            # 手动限制返回数量
            return markets[:limit] if markets else []
        except Exception as e:
            logger.error(f"获取市场失败: {e}")
            return []

    async def get_market_by_condition_id(self, condition_id: str) -> dict | None:
        """根据条件ID获取市场信息"""
        try:
            market = await self.client.get_market(condition_id=condition_id)
            logger.info(f"获取市场信息: {market.get('question', 'Unknown')}")
            return market
        except Exception as e:
            logger.error(f"获取市场信息失败: {e}")
            return None

    async def get_order_book(self, token_id: str) -> dict | None:
        """获取订单簿"""
        try:
            book = await self.client.get_order_book(token_id=token_id)
            logger.info(
                f"获取订单簿 - Bids: {len(book.get('bids', []))}, Asks: {len(book.get('asks', []))}"
            )
            return book
        except Exception as e:
            logger.error(f"获取订单簿失败: {e}")
            return None

    async def get_user_orders(self) -> list[dict]:
        """获取用户订单"""
        if not self.private_key:
            logger.warning("需要私钥才能获取用户订单")
            return []

        try:
            orders = await self.client.get_orders()
            logger.info(f"获取到 {len(orders)} 个用户订单")
            return orders
        except Exception as e:
            logger.error(f"获取用户订单失败: {e}")
            return []

    async def get_user_positions(self) -> list[dict]:
        """获取用户持仓"""
        if not self.private_key:
            logger.warning("需要私钥才能获取用户持仓")
            return []

        try:
            # py-clob-client 可能使用不同的方法名
            # 尝试获取账户余额或持仓信息
            positions = await self.client.get_balances()
            logger.info(f"获取到 {len(positions)} 个持仓")
            return positions
        except Exception as e:
            logger.error(f"获取用户持仓失败: {e}")
            return []

    async def create_order(
        self, token_id: str, side: str, size: str, price: str, fok: bool = False
    ) -> dict | None:
        """
        创建订单

        Args:
            token_id: 代币ID
            side: 买卖方向 (BUY/SELL)
            size: 数量
            price: 价格
            fok: 是否为Fill or Kill订单
        """
        if not self.private_key:
            logger.warning("需要私钥才能创建订单")
            return None

        try:
            # py-clob-client 的订单创建可能需要不同的参数格式
            # 这里提供一个示例框架，实际使用时需要根据具体API调整
            logger.info(f"模拟创建订单: {token_id}, {side}, {size}, {price}")

            # 实际的订单创建逻辑需要根据 py-clob-client 的具体API实现
            # order = await self.client.create_order(order_args)

            return {"id": "simulated_order_id", "status": "created"}
        except Exception as e:
            logger.error(f"创建订单失败: {e}")
            return None

    async def cancel_order(self, order_id: str) -> bool:
        """取消订单"""
        if not self.private_key:
            logger.warning("需要私钥才能取消订单")
            return False

        try:
            await self.client.cancel_order(order_id=order_id)
            logger.info(f"取消订单成功: {order_id}")
            return True
        except Exception as e:
            logger.error(f"取消订单失败: {e}")
            return False

    async def cancel_all_orders(self) -> bool:
        """取消所有订单"""
        if not self.private_key:
            logger.warning("需要私钥才能取消所有订单")
            return False

        try:
            await self.client.cancel_all()
            logger.info("取消所有订单成功")
            return True
        except Exception as e:
            logger.error(f"取消所有订单失败: {e}")
            return False

    async def get_trade_history(self, limit: int = 50) -> list[dict]:
        """获取交易历史"""
        if not self.private_key:
            logger.warning("需要私钥才能获取交易历史")
            return []

        try:
            # py-clob-client 的 get_trades 方法可能不接受 limit 参数
            trades = await self.client.get_trades()
            logger.info(f"获取到 {len(trades)} 条交易记录")
            # 手动限制返回数量
            return trades[:limit] if trades else []
        except Exception as e:
            logger.error(f"获取交易历史失败: {e}")
            return []

    def print_market_summary(self, markets: list[dict]):
        """打印市场概要"""
        print("\n=== 市场概要 ===")
        for market in markets[:10]:  # 只显示前10个
            print(f"问题: {market.get('question', 'N/A')}")
            print(f"状态: {'已关闭' if market.get('closed', False) else '进行中'}")
            print(f"结束时间: {market.get('end_date_iso', 'N/A')}")
            print("-" * 50)

    def print_order_book_summary(self, book: dict, token_id: str):
        """打印订单簿概要"""
        print(f"\n=== 订单簿概要 (Token: {token_id}) ===")

        bids = book.get("bids", [])
        asks = book.get("asks", [])

        print("买单 (Bids):")
        for bid in bids[:5]:  # 显示前5个
            print(f"  价格: {bid['price']}, 数量: {bid['size']}")

        print("卖单 (Asks):")
        for ask in asks[:5]:  # 显示前5个
            print(f"  价格: {ask['price']}, 数量: {ask['size']}")

    def print_positions_summary(self, positions: list[dict]):
        """打印持仓概要"""
        print("\n=== 持仓概要 ===")
        for position in positions:
            print(f"市场: {position.get('market', 'N/A')}")
            print(f"数量: {position.get('size', 'N/A')}")
            print(f"价值: {position.get('value', 'N/A')}")
            print("-" * 30)

    async def get_balance(self) -> dict | None:
        """获取账户余额"""
        if not self.private_key:
            logger.warning("需要私钥才能获取账户余额")
            return None

        try:
            # 使用 get_balances 方法获取余额信息
            balance = await self.client.get_balances()
            logger.info(f"账户余额: {balance}")
            return balance
        except Exception as e:
            logger.error(f"获取账户余额失败: {e}")
            return None

    async def get_rewards(self) -> list[dict]:
        """获取奖励信息"""
        if not self.private_key:
            logger.warning("需要私钥才能获取奖励信息")
            return []

        try:
            # py-clob-client 可能没有 get_rewards 方法
            # 这里返回空列表或尝试其他方法
            logger.info("奖励信息功能暂未实现")
            return []
        except Exception as e:
            logger.error(f"获取奖励信息失败: {e}")
            return []

    async def get_market_prices(self, condition_id: str) -> dict | None:
        """获取市场当前价格"""
        try:
            # py-clob-client 可能使用不同的价格获取方法
            # 这里提供一个通用的实现
            logger.info(f"尝试获取市场 {condition_id} 的价格信息")

            # 实际实现需要根据具体的API方法调整
            # prices = await self.client.get_market_prices(condition_id)

            return {"condition_id": condition_id, "prices": "暂未实现"}
        except Exception as e:
            logger.error(f"获取市场价格失败: {e}")
            return None

    async def subscribe_to_market_updates(self, token_id: str, duration: int = 30):
        """
        订阅市场实时更新 (WebSocket)

        Args:
            token_id: 代币ID
            duration: 监听时长(秒)
        """
        ws_url = "wss://ws-subscriptions.polymarket.com/ws/subscriptions"

        try:
            async with websockets.connect(ws_url) as websocket:
                # 订阅消息
                subscribe_msg = {"auth": {}, "type": "market", "market": token_id}
                await websocket.send(json.dumps(subscribe_msg))
                logger.info(f"已订阅市场 {token_id} 的实时更新")

                start_time = time.time()
                while time.time() - start_time < duration:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                        data = json.loads(message)
                        self._handle_market_update(data)
                    except TimeoutError:
                        continue
                    except Exception as e:
                        logger.error(f"处理WebSocket消息失败: {e}")

        except Exception as e:
            logger.error(f"WebSocket连接失败: {e}")

    def _handle_market_update(self, data: dict):
        """处理市场更新数据"""
        if data.get("type") == "book":
            print(f"订单簿更新: {data.get('market', 'N/A')}")
            print(f"最佳买价: {data.get('best_bid', 'N/A')}")
            print(f"最佳卖价: {data.get('best_ask', 'N/A')}")
        elif data.get("type") == "trade":
            print(
                f"新交易: 价格 {data.get('price', 'N/A')}, 数量 {data.get('size', 'N/A')}"
            )

    async def batch_create_orders(self, orders_data: list[dict]) -> list[dict | None]:
        """
        批量创建订单

        Args:
            orders_data: 订单数据列表，每个包含 token_id, side, size, price
        """
        if not self.private_key:
            logger.warning("需要私钥才能创建订单")
            return []

        results = []
        for order_data in orders_data:
            try:
                order = await self.create_order(**order_data)
                results.append(order)
                # 添加延迟避免频率限制
                await asyncio.sleep(0.1)
            except Exception as e:
                logger.error(f"批量创建订单失败: {e}")
                results.append(None)

        return results

    def calculate_portfolio_value(
        self, positions: list[dict], current_prices: dict[str, float]
    ) -> float:
        """
        计算投资组合价值

        Args:
            positions: 持仓列表
            current_prices: 当前价格字典
        """
        total_value = 0.0

        for position in positions:
            token_id = position.get("token_id")
            size = float(position.get("size", 0))

            if token_id in current_prices:
                value = size * current_prices[token_id]
                total_value += value
                print(f"持仓 {token_id}: {size} @ {current_prices[token_id]} = {value}")

        return total_value


async def demo_read_only_operations():
    """只读操作演示"""
    print("=== 只读操作演示 ===")

    demo = PolymarketDemo()

    # 检查客户端支持的方法
    demo.check_client_methods()

    # 获取市场列表
    markets = await demo.get_markets(limit=10)
    if markets:
        demo.print_market_summary(markets)

        # 获取第一个市场的详细信息
        first_market = markets[0]
        condition_id = first_market.get("condition_id")
        if condition_id:
            await demo.get_market_by_condition_id(condition_id)

            # 获取相关代币的订单簿
            tokens = first_market.get("tokens", [])
            if tokens:
                token_id = tokens[0].get("token_id")
                if token_id:
                    order_book = await demo.get_order_book(token_id)
                    if order_book:
                        demo.print_order_book_summary(order_book, token_id)


async def demo_trading_operations():
    """交易操作演示 (需要私钥)"""
    print("\n=== 交易操作演示 ===")

    # 从环境变量读取私钥
    private_key = os.getenv("POLYMARKET_PRIVATE_KEY")
    if not private_key:
        print("请设置 POLYMARKET_PRIVATE_KEY 环境变量来演示交易功能")
        return

    demo = PolymarketDemo(private_key)

    # 获取用户订单
    orders = await demo.get_user_orders()
    print(f"当前订单数量: {len(orders)}")

    # 获取用户持仓
    positions = await demo.get_user_positions()
    demo.print_positions_summary(positions)

    # 获取交易历史
    trades = await demo.get_trade_history(limit=10)
    print(f"最近交易数量: {len(trades)}")

    # 示例: 创建测试订单 (请谨慎使用真实资金)
    # token_id = "example_token_id"
    # order = await demo.create_order(
    #     token_id=token_id,
    #     side=BUY,
    #     size="1.0",
    #     price="0.5"
    # )

    # 如果有订单，可以取消
    # if orders:
    #     first_order_id = orders[0].get('id')
    #     if first_order_id:
    #         await demo.cancel_order(first_order_id)


async def demo_advanced_features():
    """高级功能演示"""
    print("\n=== 高级功能演示 ===")

    private_key = os.getenv("POLYMARKET_PRIVATE_KEY")
    if not private_key:
        print("请设置 POLYMARKET_PRIVATE_KEY 环境变量来演示高级功能")
        return

    demo = PolymarketDemo(private_key)

    # 获取账户余额
    balance = await demo.get_balance()
    if balance:
        print(f"账户余额: {balance}")

    # 获取奖励信息
    rewards = await demo.get_rewards()
    if rewards:
        print(f"奖励信息: {len(rewards)} 项")

    # 批量订单示例 (注释掉避免意外交易)
    # batch_orders = [
    #     {"token_id": "token1", "side": BUY, "size": "1.0", "price": "0.5"},
    #     {"token_id": "token2", "side": SELL, "size": "2.0", "price": "0.6"},
    # ]
    # results = await demo.batch_create_orders(batch_orders)
    # print(f"批量订单结果: {len([r for r in results if r])}/{len(results)} 成功")


async def demo_websocket_subscription():
    """WebSocket 实时数据演示"""
    print("\n=== WebSocket 实时数据演示 ===")

    demo = PolymarketDemo()

    # 获取一个活跃市场的代币ID
    markets = await demo.get_markets(limit=5)
    if markets:
        first_market = markets[0]
        tokens = first_market.get("tokens", [])
        if tokens:
            token_id = tokens[0].get("token_id")
            if token_id:
                print(
                    f"开始监听市场 {first_market.get('question', 'N/A')} 的实时数据..."
                )
                await demo.subscribe_to_market_updates(token_id, duration=10)


async def demo_portfolio_analysis():
    """投资组合分析演示"""
    print("\n=== 投资组合分析演示 ===")

    private_key = os.getenv("POLYMARKET_PRIVATE_KEY")
    if not private_key:
        print("请设置 POLYMARKET_PRIVATE_KEY 环境变量来演示投资组合分析")
        return

    demo = PolymarketDemo(private_key)

    # 获取持仓
    positions = await demo.get_user_positions()
    if positions:
        # 模拟当前价格 (实际应用中应从API获取)
        current_prices = {}
        for position in positions:
            token_id = position.get("token_id")
            if token_id:
                current_prices[token_id] = 0.55  # 模拟价格

        # 计算投资组合价值
        total_value = demo.calculate_portfolio_value(positions, current_prices)
        print(f"\n投资组合总价值: {total_value:.2f}")


async def demo_market_analysis():
    """市场分析演示"""
    print("\n=== 市场分析演示 ===")

    demo = PolymarketDemo()

    # 获取活跃市场
    markets = await demo.get_markets(limit=50)

    # 分析市场类型
    categories = {}
    active_markets = 0
    closed_markets = 0

    for market in markets:
        category = market.get("category", "Other")
        categories[category] = categories.get(category, 0) + 1

        if market.get("closed", False):
            closed_markets += 1
        else:
            active_markets += 1

    print("市场统计:")
    print(f"  活跃市场: {active_markets}")
    print(f"  已关闭市场: {closed_markets}")

    print("\n市场类别分布:")
    for category, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
        print(f"  {category}: {count}")

    # 分析价格分布
    price_ranges = {"0-0.2": 0, "0.2-0.4": 0, "0.4-0.6": 0, "0.6-0.8": 0, "0.8-1.0": 0}

    for market in markets[:20]:  # 分析前20个市场
        tokens = market.get("tokens", [])
        for _ in tokens:
            # 这里可以获取实际价格进行分析
            # 现在使用模拟数据
            price = 0.5  # 模拟价格

            if price <= 0.2:
                price_ranges["0-0.2"] += 1
            elif price <= 0.4:
                price_ranges["0.2-0.4"] += 1
            elif price <= 0.6:
                price_ranges["0.4-0.6"] += 1
            elif price <= 0.8:
                price_ranges["0.6-0.8"] += 1
            else:
                price_ranges["0.8-1.0"] += 1

    print("\n价格分布 (模拟数据):")
    for range_name, count in price_ranges.items():
        print(f"  {range_name}: {count}")


async def demo_risk_management():
    """风险管理演示"""
    print("\n=== 风险管理演示 ===")

    private_key = os.getenv("POLYMARKET_PRIVATE_KEY")
    if not private_key:
        print("请设置 POLYMARKET_PRIVATE_KEY 环境变量来演示风险管理功能")
        return

    demo = PolymarketDemo(private_key)

    # 获取当前持仓和订单
    positions = await demo.get_user_positions()
    orders = await demo.get_user_orders()

    print(f"当前持仓数量: {len(positions)}")
    print(f"当前订单数量: {len(orders)}")

    # 风险检查示例
    max_position_size = 100  # 最大单个持仓大小
    max_total_exposure = 1000  # 最大总敞口

    total_exposure = 0
    risky_positions = []

    for position in positions:
        size = float(position.get("size", 0))
        value = abs(size * 0.5)  # 使用模拟价格
        total_exposure += value

        if size > max_position_size:
            risky_positions.append(position)

    print(f"总敞口: {total_exposure:.2f}")
    print(f"风险持仓数量: {len(risky_positions)}")

    if total_exposure > max_total_exposure:
        print("⚠️  警告: 总敞口超过限制")

    if risky_positions:
        print("⚠️  警告: 存在超大持仓")


def demo_configuration_management():
    """配置管理演示"""
    print("\n=== 配置管理演示 ===")

    # 配置示例
    config = {
        "api": {
            "host": "https://clob.polymarket.com",
            "timeout": 30,
            "retry_attempts": 3,
        },
        "trading": {
            "max_order_size": 100,
            "default_slippage": 0.01,
            "risk_limit": 1000,
        },
        "logging": {
            "level": "INFO",
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        },
    }

    print("当前配置:")
    print(json.dumps(config, indent=2, ensure_ascii=False))

    # 环境变量检查
    required_env_vars = [
        "POLYMARKET_PRIVATE_KEY",
        "POLYMARKET_HOST",
        "POLYMARKET_CHAIN_ID",
    ]

    print("\n环境变量检查:")
    for var in required_env_vars:
        value = os.getenv(var)
        status = "✅ 已设置" if value else "❌ 未设置"
        print(f"  {var}: {status}")


def demo_error_handling_patterns():
    """错误处理模式演示"""
    print("\n=== 错误处理模式演示 ===")

    # 重试装饰器示例
    async def retry_operation(operation, max_retries=3, delay=1):
        """重试操作"""
        for attempt in range(max_retries):
            try:
                return await operation()
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e
                logger.warning(f"操作失败，第 {attempt + 1} 次重试: {e}")
                await asyncio.sleep(delay * (2**attempt))  # 指数退避

    # 断路器模式示例
    class CircuitBreaker:
        def __init__(self, failure_threshold=5, recovery_timeout=60):
            self.failure_threshold = failure_threshold
            self.recovery_timeout = recovery_timeout
            self.failure_count = 0
            self.last_failure_time = None
            self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

        async def call(self, operation):
            if self.state == "OPEN":
                if time.time() - self.last_failure_time > self.recovery_timeout:
                    self.state = "HALF_OPEN"
                else:
                    raise Exception("Circuit breaker is OPEN")

            try:
                result = await operation()
                if self.state == "HALF_OPEN":
                    self.state = "CLOSED"
                    self.failure_count = 0
                return result
            except Exception as e:
                self.failure_count += 1
                self.last_failure_time = time.time()

                if self.failure_count >= self.failure_threshold:
                    self.state = "OPEN"

                raise e

    print("错误处理模式已实现:")
    print("  ✅ 重试机制 (指数退避)")
    print("  ✅ 断路器模式")
    print("  ✅ 超时处理")
    print("  ✅ 日志记录")


def main():
    """主函数"""
    print("Polymarket API 演示程序")
    print("=" * 50)
    print("基于 py-clob-client 的完整功能演示")
    print("包含市场数据查询、交易管理、实时数据订阅等功能")
    print("=" * 50)

    try:
        # 配置管理演示 (同步函数)
        demo_configuration_management()

        # 错误处理模式演示 (同步函数)
        demo_error_handling_patterns()

        # 运行只读操作演示
        asyncio.run(demo_read_only_operations())

        # 运行市场分析演示
        asyncio.run(demo_market_analysis())

        # 运行交易操作演示 (需要私钥)
        asyncio.run(demo_trading_operations())

        # 运行高级功能演示 (需要私钥)
        asyncio.run(demo_advanced_features())

        # 运行投资组合分析演示 (需要私钥)
        asyncio.run(demo_portfolio_analysis())

        # 运行风险管理演示 (需要私钥)
        asyncio.run(demo_risk_management())

        # WebSocket 实时数据演示 (可选 - 需要网络连接)
        print("\n是否运行 WebSocket 实时数据演示? (需要网络连接，将监听10秒)")
        response = input("输入 'y' 继续，其他键跳过: ").lower()
        if response == "y":
            asyncio.run(demo_websocket_subscription())

        print("\n" + "=" * 50)
        print("演示程序完成!")
        print("请查看上面的输出了解各种API的使用方法")
        print("=" * 50)

    except KeyboardInterrupt:
        print("\n程序被用户中断")
    except Exception as e:
        logger.error(f"程序执行出错: {e}")
        print(f"\n错误详情: {e}")
        print("请检查网络连接和API配置")


if __name__ == "__main__":
    main()
