"""
Polymarket统一客户端 - 重构版

简化的同步客户端，合并所有功能到单一接口
"""

import logging
import time
from datetime import datetime, timezone
from typing import Any

import requests
from web3 import Web3
from web3.middleware import geth_poa_middleware
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import (
    ApiCreds,
    OrderArgs,
    MarketOrderArgs,
    BalanceAllowanceParams,
    AssetType,
)
from py_clob_client.order_builder.constants import BUY, SELL
from py_clob_client.clob_types import OrderType as ClobOrderType
from py_clob_client.constants import POLYGON, AMOY

from .config import ClientConfig
from .exceptions import (
    PolymarketError,
    NetworkError,
    APIError,
    OrderError,
    ValidationError,
)
from .types import (
    MarketInfo,
    MarketStatus,
    OutcomeToken,
    OrderInfo,
    OrderSide,
    OrderType,
    OrderStatus,
    BalanceInfo,
)
from .storage import SimpleStorage


class SimpleCache:
    """简单的内存缓存"""

    def __init__(self, default_ttl: int = 300):
        self.default_ttl = default_ttl
        self._cache: Dict[str, Dict[str, Any]] = {}

    def get(self, key: str) -> Optional[Any]:
        """获取缓存数据"""
        if key in self._cache:
            entry = self._cache[key]
            if time.time() < entry["expires"]:
                return entry["data"]
            else:
                del self._cache[key]
        return None

    def set(self, key: str, data: Any, ttl: Optional[int] = None) -> None:
        """设置缓存数据"""
        ttl = ttl or self.default_ttl
        self._cache[key] = {"data": data, "expires": time.time() + ttl}

    def clear(self) -> None:
        """清空缓存"""
        self._cache.clear()

    def size(self) -> int:
        """获取缓存大小"""
        return len(self._cache)


class PolymarketClient:
    """
    Polymarket统一客户端 - 重构版

    提供所有核心功能的同步接口：
    - 市场数据获取
    - 订单管理
    - 投资组合查询
    - 可选的数据存储
    """

    def __init__(self, config: Optional[ClientConfig] = None):
        """初始化客户端"""
        self.config = config or ClientConfig.from_env()
        self.config.validate()

        # 设置日志
        self._setup_logging()

        # 初始化连接
        self._init_web3()
        self._init_clob_client()

        # 获取钱包地址
        self.wallet_address = self._get_wallet_address()

        # 初始化缓存
        self.cache = (
            SimpleCache(self.config.cache_ttl) if self.config.enable_cache else None
        )

        # 初始化存储（可选）
        self.storage = (
            SimpleStorage(self.config.db_path) if self.config.enable_storage else None
        )

        # HTTP会话（用于同步请求）
        self.session = requests.Session()
        self.session.timeout = 30

        self.logger.info(
            f"Polymarket client initialized for wallet: {self.wallet_address}"
        )
        self.logger.info(f"Dry run mode: {self.config.dry_run}")
        self.logger.info(f"Cache enabled: {self.config.enable_cache}")
        self.logger.info(f"Storage enabled: {self.config.enable_storage}")

    def _setup_logging(self) -> None:
        """设置日志"""
        logging.basicConfig(
            level=getattr(logging, self.config.log_level),
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        self.logger = logging.getLogger(self.__class__.__name__)

    def _init_web3(self) -> None:
        """初始化Web3连接"""
        try:
            self.w3 = Web3(Web3.HTTPProvider(self.config.polygon_rpc))
            self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)

            if not self.w3.is_connected():
                raise NetworkError(f"Cannot connect to Web3: {self.config.polygon_rpc}")

            self.logger.info("Web3 connection established")
        except Exception as e:
            raise NetworkError(f"Failed to initialize Web3: {e}") from e

    def _init_clob_client(self) -> None:
        """初始化CLOB客户端"""
        try:
            chain_id = AMOY if self.config.chain_id == 80002 else POLYGON

            self.client = ClobClient(
                host=self.config.clob_url,
                key=self.config.private_key,
                chain_id=chain_id,
            )

            # 设置API凭证
            if all(
                [
                    self.config.api_key,
                    self.config.api_secret,
                    self.config.api_passphrase,
                ]
            ):
                creds = ApiCreds(
                    api_key=self.config.api_key,
                    api_secret=self.config.api_secret,
                    api_passphrase=self.config.api_passphrase,
                )
                self.client.set_api_creds(creds)
                self.logger.info("Using existing API credentials")
            else:
                creds = self.client.create_or_derive_api_creds()
                self.client.set_api_creds(creds)
                self.logger.info("Created new API credentials")

        except Exception as e:
            raise PolymarketError(f"Failed to initialize CLOB client: {e}") from e

    def _get_wallet_address(self) -> str:
        """获取钱包地址"""
        try:
            account = self.w3.eth.account.from_key(self.config.private_key)
            return account.address
        except Exception as e:
            raise PolymarketError(f"Failed to derive wallet address: {e}") from e

    # =============================================================================
    # 市场数据接口
    # =============================================================================

    def get_markets(
        self,
        active_only: bool = True,
        limit: int = 100,
        category: Optional[str] = None,
        use_cache: bool = True,
    ) -> List[MarketInfo]:
        """获取市场列表"""
        cache_key = f"markets_{active_only}_{limit}_{category}"

        # 尝试从缓存获取
        if use_cache and self.cache:
            cached_data = self.cache.get(cache_key)
            if cached_data:
                return cached_data

        try:
            params = {
                "active": "true" if active_only else "false",
                "limit": str(limit),
                "order": "volume",
                "ascending": "false",
            }
            if category:
                params["category"] = category

            response = self.session.get(
                f"{self.config.gamma_url}/markets", params=params
            )
            response.raise_for_status()

            markets = []
            for market_data in response.json():
                try:
                    market = self._parse_market_data(market_data)
                    markets.append(market)

                    # 保存到存储
                    if self.storage:
                        self.storage.save_market(market)

                except Exception as e:
                    self.logger.warning(
                        f"Failed to parse market {market_data.get('id', 'unknown')}: {e}"
                    )
                    continue

            # 缓存结果
            if use_cache and self.cache:
                self.cache.set(cache_key, markets)

            self.logger.info(f"Retrieved {len(markets)} markets")
            return markets

        except Exception as e:
            raise APIError(f"Error fetching markets: {e}") from e

    def get_market_by_id(self, market_id: str) -> Optional[MarketInfo]:
        """根据市场ID获取市场信息"""
        try:
            response = self.session.get(f"{self.config.gamma_url}/markets/{market_id}")
            if response.status_code == 200:
                return self._parse_market_data(response.json())
            return None
        except Exception as e:
            self.logger.error(f"Error fetching market {market_id}: {e}")
            return None

    def search_markets(self, query: str, limit: int = 20) -> List[MarketInfo]:
        """搜索市场"""
        all_markets = self.get_markets(limit=limit * 3)
        query = query.lower()

        matching_markets = []
        for market in all_markets:
            if query in market.question.lower() or query in market.description.lower():
                matching_markets.append(market)

        return matching_markets[:limit]

    def get_orderbook(self, token_id: str) -> Dict[str, Any]:
        """获取订单簿"""
        try:
            orderbook = self.client.get_order_book(token_id)
            return {
                "bids": [
                    {"price": float(bid.price), "size": float(bid.size)}
                    for bid in orderbook.bids
                ],
                "asks": [
                    {"price": float(ask.price), "size": float(ask.size)}
                    for ask in orderbook.asks
                ],
                "token_id": token_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            raise APIError(f"Failed to get orderbook for token {token_id}: {e}") from e

    def get_price(self, token_id: str, side: str = "BUY") -> float:
        """获取代币价格"""
        try:
            response = self.client.get_price(token_id, side)
            price = float(response.get("price", 0))

            # 保存价格到存储
            if self.storage and price > 0:
                self.storage.save_price(token_id, price, source="orderbook")

            return price
        except Exception as e:
            raise APIError(f"Failed to get price for token {token_id}: {e}") from e

    def get_mid_price(self, token_id: str) -> float:
        """获取中间价格"""
        try:
            orderbook_data = self.get_orderbook(token_id)
            bids = orderbook_data["bids"]
            asks = orderbook_data["asks"]

            if bids and asks:
                best_bid = bids[0]["price"]
                best_ask = asks[0]["price"]
                return (best_bid + best_ask) / 2
            else:
                # 尝试获取最后成交价
                try:
                    response = self.client.get_last_trade_price(token_id=token_id)
                    price = response.get("price")
                    return float(price) if price is not None else 0.0
                except Exception:
                    return 0.0
        except Exception as e:
            self.logger.warning(
                f"Failed to calculate mid price for token {token_id}: {e}"
            )
            return 0.0

    # =============================================================================
    # 订单管理接口
    # =============================================================================

    def create_limit_order(
        self,
        token_id: str,
        side: OrderSide,
        size: float,
        price: float,
        order_type: OrderType = OrderType.GTC,
        validate: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """创建限价订单"""
        # 基础验证
        if validate:
            if size <= 0:
                raise ValidationError("Order size must be positive")
            if price <= 0:
                raise ValidationError("Order price must be positive")
            if price > 1.0:
                raise ValidationError("Price cannot exceed 1.0 for prediction markets")

        try:
            if self.config.dry_run:
                self.logger.info(
                    f"DRY RUN: Would create {side.value} limit order for {size} tokens at ${price}"
                )
                return self._create_dry_run_response(
                    token_id, side, size, price, "limit"
                )

            # 创建订单参数
            order_args = OrderArgs(
                token_id=token_id,
                size=size,
                price=price,
                side=BUY if side == OrderSide.BUY else SELL,
            )

            # 创建并签名订单
            signed_order = self.client.create_order(order_args)

            # 转换订单类型
            clob_order_type = self._convert_order_type(order_type)

            # 发布订单
            response = self.client.post_order(signed_order, orderType=clob_order_type)

            self.logger.info(
                f"Created {side.value} limit order for {size} tokens at ${price}"
            )
            return response

        except Exception as e:
            self.logger.error(f"Failed to create limit order: {e}")
            if not self.config.dry_run:
                raise OrderError(f"Failed to create limit order: {e}") from e
            return None

    def create_market_order(
        self, token_id: str, side: OrderSide, amount: float, validate: bool = True
    ) -> Optional[Dict[str, Any]]:
        """创建市价订单"""
        # 基础验证
        if validate:
            if amount <= 0:
                raise ValidationError("Order amount must be positive")

        try:
            if self.config.dry_run:
                self.logger.info(
                    f"DRY RUN: Would create {side.value} market order for ${amount}"
                )
                return self._create_dry_run_response(
                    token_id, side, amount, 0.0, "market"
                )

            # 创建市价订单参数
            order_args = MarketOrderArgs(
                token_id=token_id,
                amount=amount,
                side=BUY if side == OrderSide.BUY else SELL,
            )

            # 创建并签名订单
            signed_order = self.client.create_market_order(order_args)

            # 发布订单
            response = self.client.post_order(signed_order, orderType=ClobOrderType.FOK)

            self.logger.info(f"Created {side.value} market order for ${amount}")
            return response

        except Exception as e:
            self.logger.error(f"Failed to create market order: {e}")
            if not self.config.dry_run:
                raise OrderError(f"Failed to create market order: {e}") from e
            return None

    def get_orders(self, market_id: Optional[str] = None) -> List[OrderInfo]:
        """获取订单列表"""
        try:
            if market_id:
                raw_orders = self.client.get_orders(market=market_id)
            else:
                raw_orders = self.client.get_orders()

            orders = []
            for raw_order in raw_orders:
                try:
                    order_info = self._parse_order_data(raw_order)
                    orders.append(order_info)
                except Exception as e:
                    self.logger.warning(
                        f"Failed to parse order {raw_order.get('id', 'unknown')}: {e}"
                    )
                    continue

            return orders

        except Exception as e:
            self.logger.error(f"Failed to get orders: {e}")
            return []

    def cancel_order(self, order_id: str) -> bool:
        """取消订单"""
        try:
            if self.config.dry_run:
                self.logger.info(f"DRY RUN: Would cancel order {order_id}")
                return True

            response = self.client.cancel(order_id)
            success = response.get("success", False)

            if success:
                self.logger.info(f"Successfully cancelled order {order_id}")
            else:
                self.logger.warning(f"Failed to cancel order {order_id}: {response}")

            return success

        except Exception as e:
            self.logger.error(f"Failed to cancel order {order_id}: {e}")
            if not self.config.dry_run:
                raise OrderError(f"Failed to cancel order {order_id}: {e}") from e
            return False

    def cancel_all_orders(self, market_id: Optional[str] = None) -> bool:
        """取消所有订单"""
        try:
            if self.config.dry_run:
                self.logger.info(
                    f"DRY RUN: Would cancel all orders for market {market_id}"
                )
                return True

            if market_id:
                response = self.client.cancel_market_orders(market=market_id)
            else:
                response = self.client.cancel_all()

            success = response.get("success", False)

            if success:
                self.logger.info("Successfully cancelled all orders")
            else:
                self.logger.warning(f"Failed to cancel all orders: {response}")

            return success

        except Exception as e:
            self.logger.error(f"Failed to cancel all orders: {e}")
            if not self.config.dry_run:
                raise OrderError(f"Failed to cancel all orders: {e}") from e
            return False

    # =============================================================================
    # 投资组合接口
    # =============================================================================

    def get_balance_info(self) -> BalanceInfo:
        """获取余额信息"""
        try:
            # 获取USDC余额
            balance_info = self.client.get_balance_allowance(
                params=BalanceAllowanceParams(asset_type=AssetType.COLLATERAL)
            )
            usdc_balance = float(balance_info.get("balance", 0))

            # 获取持仓价值（简化计算）
            position_value = 0.0  # 这里可以扩展为实际计算

            return BalanceInfo(
                usdc_balance=usdc_balance,
                total_position_value=position_value,
                available_balance=usdc_balance,  # 简化处理
                margin_used=0.0,  # 简化处理
                last_updated=datetime.now(timezone.utc),
            )

        except Exception as e:
            self.logger.error(f"Failed to get balance info: {e}")
            return BalanceInfo(
                usdc_balance=0.0,
                total_position_value=0.0,
                available_balance=0.0,
                margin_used=0.0,
                last_updated=datetime.now(timezone.utc),
            )

    def get_token_balance(self, token_id: str) -> float:
        """获取指定代币余额"""
        try:
            balance_info = self.client.get_balance_allowance(
                params=BalanceAllowanceParams(
                    asset_type=AssetType.CONDITIONAL, token_id=token_id
                )
            )
            return float(balance_info.get("balance", 0))
        except Exception as e:
            self.logger.error(f"Failed to get token balance for {token_id}: {e}")
            return 0.0

    def calculate_position_size(
        self, available_balance: float, price: float, max_risk_pct: float = 0.1
    ) -> float:
        """计算建议的仓位大小"""
        if price <= 0 or available_balance <= 0:
            return 0.0

        max_risk_amount = available_balance * max_risk_pct
        position_size = max_risk_amount / price

        # 确保最小交易量
        min_size = 5.0
        return max(min_size, position_size)

    # =============================================================================
    # 工具方法
    # =============================================================================

    def health_check(self) -> Dict[str, Any]:
        """执行健康检查"""
        results = {
            "wallet_address": self.wallet_address,
            "dry_run_mode": self.config.dry_run,
            "chain_id": self.config.chain_id,
        }

        try:
            # 检查Web3连接
            results["web3_connected"] = self.w3.is_connected()

            # 检查区块高度
            if results["web3_connected"]:
                results["latest_block"] = self.w3.eth.block_number

            # 检查缓存状态
            if self.cache:
                results["cache_size"] = self.cache.size()

            # 检查存储状态
            if self.storage:
                results["storage_stats"] = self.storage.get_stats()

            # 总体健康状态
            results["healthy"] = results["web3_connected"]

        except Exception as e:
            results["error"] = str(e)
            results["healthy"] = False

        return results

    def clear_cache(self) -> None:
        """清空缓存"""
        if self.cache:
            self.cache.clear()
            self.logger.info("Cache cleared")

    def cleanup_old_data(self, days: int = 30) -> Dict[str, Any]:
        """清理旧数据"""
        if not self.storage:
            return {"error": "Storage not enabled"}

        deleted = self.storage.cleanup_old_prices(days)
        return {"prices_deleted": deleted}

    # =============================================================================
    # 内部辅助方法
    # =============================================================================

    def _parse_market_data(self, data: Dict[str, Any]) -> MarketInfo:
        """解析市场数据"""
        # 解析结果代币
        outcomes = []
        token_ids = data.get("clobTokenIds", [])
        outcome_names = data.get("outcomes", [])
        outcome_prices = data.get("outcomePrices", [])

        for i, token_id in enumerate(token_ids):
            outcome_name = (
                outcome_names[i] if i < len(outcome_names) else f"Outcome {i + 1}"
            )
            price = 0.0

            # 安全解析价格
            if i < len(outcome_prices):
                try:
                    if isinstance(outcome_prices[i], (int, float)):
                        price = float(outcome_prices[i])
                    elif isinstance(outcome_prices[i], str):
                        price = float(outcome_prices[i])
                except (ValueError, TypeError):
                    price = 0.0

            outcomes.append(
                OutcomeToken(
                    token_id=str(token_id),
                    outcome=outcome_name,
                    price=price,
                    volume=0.0,
                )
            )

        # 解析市场状态
        status = (
            MarketStatus.ACTIVE if data.get("active", False) else MarketStatus.CLOSED
        )

        # 解析结束时间
        end_date_str = data.get("endDate", "")
        try:
            end_date = datetime.fromisoformat(end_date_str.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            end_date = datetime.now(timezone.utc)

        return MarketInfo(
            id=str(data["id"]),
            question=data["question"],
            description=data.get("description", ""),
            end_date=end_date,
            status=status,
            volume=float(data.get("volume", 0)),
            liquidity=float(data.get("liquidity", 0)),
            outcomes=outcomes,
            condition_id=data.get("conditionId"),
            neg_risk=data.get("negRisk", False),
            category=self._detect_category(data["question"]),
        )

    def _detect_category(self, question: str) -> str:
        """检测市场类别"""
        question = question.lower()

        categories = {
            "politics": [
                "election",
                "president",
                "vote",
                "congress",
                "senate",
                "minister",
                "government",
            ],
            "sports": [
                "nba",
                "nfl",
                "mlb",
                "soccer",
                "football",
                "basketball",
                "baseball",
                "league",
            ],
            "crypto": ["bitcoin", "eth", "crypto", "token", "blockchain"],
            "entertainment": [
                "movie",
                "film",
                "actor",
                "actress",
                "award",
                "song",
                "album",
            ],
            "tech": ["ai", "openai", "technology", "software", "app", "launch"],
        }

        for category, keywords in categories.items():
            if any(keyword in question for keyword in keywords):
                return category

        return "other"

    def _parse_order_data(self, raw_order: Dict[str, Any]) -> OrderInfo:
        """解析订单数据"""
        # 解析订单方向
        side = OrderSide.BUY if raw_order["side"] == "BUY" else OrderSide.SELL

        # 解析订单类型
        order_type = OrderType.LIMIT  # 默认为限价单

        # 解析订单状态
        status_map = {
            "OPEN": OrderStatus.OPEN,
            "FILLED": OrderStatus.FILLED,
            "CANCELLED": OrderStatus.CANCELLED,
            "PARTIALLY_FILLED": OrderStatus.PARTIALLY_FILLED,
        }
        status = status_map.get(raw_order.get("status", "OPEN"), OrderStatus.OPEN)

        # 计算已成交和剩余数量
        original_size = float(raw_order.get("original_size", 0))
        size_matched = float(raw_order.get("size_matched", 0))
        remaining_size = original_size - size_matched

        # 解析时间
        created_at = self._parse_timestamp(raw_order.get("created_at"))
        updated_at = self._parse_timestamp(
            raw_order.get("updated_at", raw_order.get("created_at"))
        )

        return OrderInfo(
            id=raw_order["id"],
            market_id=raw_order.get("market", ""),
            token_id=raw_order["asset_id"],
            side=side,
            order_type=order_type,
            status=status,
            size=original_size,
            price=float(raw_order.get("price", 0)),
            filled_size=size_matched,
            remaining_size=remaining_size,
            created_at=created_at,
            updated_at=updated_at,
            fee_rate=float(raw_order.get("fee_rate", 0)),
        )

    def _parse_timestamp(self, timestamp_str: Optional[str]) -> datetime:
        """解析时间戳"""
        if not timestamp_str:
            return datetime.now(timezone.utc)

        try:
            return datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return datetime.now(timezone.utc)

    def _convert_order_type(self, order_type: OrderType) -> ClobOrderType:
        """转换订单类型"""
        type_map = {
            OrderType.GTC: ClobOrderType.GTC,
            OrderType.FOK: ClobOrderType.FOK,
            OrderType.LIMIT: ClobOrderType.GTC,
            OrderType.MARKET: ClobOrderType.FOK,
        }
        return type_map.get(order_type, ClobOrderType.GTC)

    def _create_dry_run_response(
        self, token_id: str, side: OrderSide, size: float, price: float, order_type: str
    ) -> Dict[str, Any]:
        """创建模拟运行响应"""
        return {
            "status": "simulated",
            "dry_run": True,
            "order": {
                "id": f"dry_run_{int(datetime.now().timestamp())}",
                "token_id": token_id,
                "side": side.value,
                "size": size,
                "price": price,
                "type": order_type,
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        }

    def __str__(self) -> str:
        """字符串表示"""
        return f"PolymarketClient(wallet={self.wallet_address[:10]}..., dry_run={self.config.dry_run})"
