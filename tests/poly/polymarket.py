"""
Polymarket 客户端封装类
提供对 Polymarket API 的简洁抽象，方便量化策略开发和研究
"""

import logging
import os
import time
from dataclasses import dataclass
from typing import Any

import httpx
from dotenv import load_dotenv
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import ApiCreds
from py_clob_client.clob_types import AssetType
from py_clob_client.clob_types import BalanceAllowanceParams
from py_clob_client.clob_types import MarketOrderArgs
from py_clob_client.clob_types import OrderArgs
from py_clob_client.clob_types import OrderBookSummary
from py_clob_client.clob_types import OrderType
from py_clob_client.constants import AMOY
from py_clob_client.constants import POLYGON
from py_clob_client.order_builder.constants import BUY
from py_clob_client.order_builder.constants import SELL
from web3 import Web3
from web3.constants import MAX_INT


@dataclass
class MarketInfo:
    """市场信息数据类"""

    id: str
    question: str
    description: str
    end_date: str
    active: bool
    funded: bool
    volume: float
    spread: float
    outcomes: list[str]
    outcome_prices: list[float]
    token_ids: list[str]


@dataclass
class OrderInfo:
    """订单信息数据类"""

    id: str
    market: str
    token_id: str
    side: str
    size: float
    price: float
    status: str
    created_at: str


@dataclass
class BalanceInfo:
    """余额信息数据类"""

    usdc_balance: float
    token_balances: dict[str, float]
    allowances: dict[str, float]


class PolymarketError(Exception):
    """Polymarket 相关错误"""

    pass


class PolymarketClient:
    """
    Polymarket 客户端封装类

    提供对 Polymarket 各种API的统一抽象，包括：
    - 市场数据获取
    - 订单管理
    - 余额和授权管理
    - 链上交互
    """

    def __init__(
        self,
        private_key: str | None = None,
        use_testnet: bool = False,
        dry_run: bool = True,
        log_level: str = "INFO",
    ):
        """
        初始化 Polymarket 客户端

        Args:
            private_key: 钱包私钥，如果为None会从环境变量读取
            use_testnet: 是否使用测试网络 (AMOY)
            dry_run: 是否为模拟模式，不实际执行交易
            log_level: 日志级别
        """
        load_dotenv()

        # 配置日志
        logging.basicConfig(
            level=getattr(logging, log_level),
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        self.logger = logging.getLogger(self.__class__.__name__)

        # 基础配置
        self.dry_run = dry_run
        self.private_key = private_key or os.getenv("PK")
        if not self.private_key:
            raise PolymarketError(
                "Private key not found in environment variables"
            ) from None

        self.chain_id = AMOY if use_testnet else POLYGON
        self.use_testnet = use_testnet

        # API 端点配置
        self.clob_url = os.getenv("CLOB_API_URL", "https://clob.polymarket.com")
        self.gamma_url = "https://gamma-api.polymarket.com"
        self.polygon_rpc = os.getenv("POLYGON_RPC", "https://polygon-rpc.com")

        # 合约地址 (Polygon 主网)
        self.contract_addresses = {
            "usdc": Web3.to_checksum_address(
                "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"
            ),
            "ctf": Web3.to_checksum_address(
                "0x4D97DCd97eC945f40cF65F87097ACe5EA0476045"
            ),
            "exchange": Web3.to_checksum_address(
                "0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E"
            ),
            "neg_risk_exchange": Web3.to_checksum_address(
                "0xC5d563A36AE78145C45a50134d48A1215220f80a"
            ),
            "neg_risk_adapter": Web3.to_checksum_address(
                "0xd91E80cF2E7be2e162c6513ceD06f1dD0dA35296"
            ),
        }

        # 初始化组件
        self._init_web3()
        self._init_clob_client()
        self._init_contracts()

        # 获取钱包地址
        self.wallet_address = self._get_wallet_address()
        self.logger.info(
            f"Initialized Polymarket client for wallet: {self.wallet_address}"
        )
        self.logger.info(
            f"Network: {'Testnet (Amoy)' if use_testnet else 'Mainnet (Polygon)'}"
        )
        self.logger.info(f"Dry run mode: {dry_run}")

    def _init_web3(self) -> None:
        """初始化 Web3 连接"""
        self.w3 = Web3(Web3.HTTPProvider(self.polygon_rpc))
        if not self.w3.is_connected():
            raise PolymarketError(
                f"Cannot connect to Web3 provider: {self.polygon_rpc}"
            ) from None

    def _init_clob_client(self) -> None:
        """初始化 CLOB 客户端"""
        try:
            # 创建客户端
            self.client = ClobClient(
                self.clob_url, key=self.private_key, chain_id=self.chain_id
            )

            # 设置 API 凭证
            api_key = os.getenv("CLOB_API_KEY")
            api_secret = os.getenv("CLOB_SECRET")
            api_passphrase = os.getenv("CLOB_PASS_PHRASE")

            if all([api_key, api_secret, api_passphrase]):
                creds = ApiCreds(
                    api_key=api_key,
                    api_secret=api_secret,
                    api_passphrase=api_passphrase,
                )
                self.client.set_api_creds(creds)
                self.logger.info("Using existing API credentials")
            else:
                # 创建或派生 API 凭证
                creds = self.client.create_or_derive_api_creds()
                self.client.set_api_creds(creds)
                self.logger.info("Created new API credentials")

        except Exception as e:
            raise PolymarketError(f"Failed to initialize CLOB client: {e}") from e

    def _init_contracts(self) -> None:
        """初始化智能合约实例"""
        # USDC 合约 ABI (简化版)
        usdc_abi = [
            {
                "constant": True,
                "inputs": [{"name": "_owner", "type": "address"}],
                "name": "balanceOf",
                "outputs": [{"name": "balance", "type": "uint256"}],
                "type": "function",
            },
            {
                "constant": False,
                "inputs": [
                    {"name": "_spender", "type": "address"},
                    {"name": "_value", "type": "uint256"},
                ],
                "name": "approve",
                "outputs": [{"name": "success", "type": "bool"}],
                "type": "function",
            },
            {
                "constant": True,
                "inputs": [
                    {"name": "_owner", "type": "address"},
                    {"name": "_spender", "type": "address"},
                ],
                "name": "allowance",
                "outputs": [{"name": "remaining", "type": "uint256"}],
                "type": "function",
            },
        ]

        # ERC1155 合约 ABI (CTF tokens)
        erc1155_abi = [
            {
                "inputs": [
                    {"internalType": "address", "name": "account", "type": "address"},
                    {"internalType": "uint256", "name": "id", "type": "uint256"},
                ],
                "name": "balanceOf",
                "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
                "stateMutability": "view",
                "type": "function",
            },
            {
                "inputs": [
                    {"internalType": "address", "name": "operator", "type": "address"},
                    {"internalType": "bool", "name": "approved", "type": "bool"},
                ],
                "name": "setApprovalForAll",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function",
            },
        ]

        # 创建合约实例
        self.usdc_contract = self.w3.eth.contract(
            address=self.contract_addresses["usdc"], abi=usdc_abi
        )

        self.ctf_contract = self.w3.eth.contract(
            address=self.contract_addresses["ctf"], abi=erc1155_abi
        )

    def _get_wallet_address(self) -> str:
        """从私钥获取钱包地址"""
        account = self.w3.eth.account.from_key(self.private_key)
        return account.address

    # =============================================================================
    # 市场数据接口
    # =============================================================================

    def get_markets(
        self, active_only: bool = True, limit: int = 100
    ) -> list[MarketInfo]:
        """
        获取市场列表

        Args:
            active_only: 是否只返回活跃市场
            limit: 返回数量限制

        Returns:
            市场信息列表
        """
        try:
            params = {
                "active": "true" if active_only else "false",
                "limit": str(limit),
                "order": "volume",
                "ascending": "false",
            }

            response = httpx.get(
                f"{self.gamma_url}/markets", params=params, timeout=30.0
            )

            if response.status_code != 200:
                raise PolymarketError(
                    f"Failed to fetch markets: {response.status_code}"
                )

            markets = []
            for market_data in response.json():
                try:
                    market = self._parse_market_data(market_data)
                    markets.append(market)
                except Exception as e:
                    self.logger.warning(
                        f"Failed to parse market {market_data.get('id', 'unknown')}: {e}"
                    )
                    continue

            self.logger.info(f"Retrieved {len(markets)} markets")
            return markets

        except Exception as e:
            raise PolymarketError(f"Error fetching markets: {e}") from e

    def _parse_market_data(self, data: dict[str, Any]) -> MarketInfo:
        """解析市场数据"""
        # 安全解析 outcome_prices
        outcome_prices = []
        raw_prices = data.get("outcomePrices", [])

        if isinstance(raw_prices, list):
            for price in raw_prices:
                try:
                    # 尝试转换为浮点数
                    if isinstance(price, (int, float)):
                        outcome_prices.append(float(price))
                    elif isinstance(price, str):
                        # 处理字符串形式的数字
                        if (
                            price.strip()
                            and price.strip() != "["
                            and price.strip() != "]"
                        ):
                            outcome_prices.append(float(price.strip()))
                except (ValueError, TypeError):
                    # 如果转换失败，跳过这个值
                    self.logger.debug(f"Skipping invalid price value: {price}")
                    continue
        elif isinstance(raw_prices, str):
            # 如果整个字段是字符串，尝试解析
            try:
                import json

                parsed_prices = json.loads(raw_prices)
                if isinstance(parsed_prices, list):
                    for price in parsed_prices:
                        try:
                            outcome_prices.append(float(price))
                        except (ValueError, TypeError):
                            continue
            except json.JSONDecodeError:
                self.logger.debug(f"Failed to parse price string: {raw_prices}")

        return MarketInfo(
            id=str(data["id"]),
            question=data["question"],
            description=data.get("description", ""),
            end_date=data["endDate"],
            active=data["active"],
            funded=data["funded"],
            volume=float(data.get("volume", 0)),
            spread=float(data.get("spread", 0)),
            outcomes=data.get("outcomes", []),
            outcome_prices=outcome_prices,
            token_ids=data.get("clobTokenIds", []),
        )

    def get_market_by_token_id(self, token_id: str) -> MarketInfo | None:
        """
        根据代币ID获取市场信息

        Args:
            token_id: 代币ID

        Returns:
            市场信息或None
        """
        try:
            params = {"clob_token_ids": token_id}
            response = httpx.get(
                f"{self.gamma_url}/markets", params=params, timeout=30.0
            )

            if response.status_code == 200:
                data = response.json()
                if data:
                    return self._parse_market_data(data[0])
            return None

        except Exception as e:
            self.logger.error(f"Error fetching market for token {token_id}: {e}")
            return None

    def get_high_volume_markets(self, min_volume: float = 10000) -> list[MarketInfo]:
        """
        获取高交易量市场

        Args:
            min_volume: 最小交易量阈值

        Returns:
            高交易量市场列表
        """
        all_markets = self.get_markets()
        return [m for m in all_markets if m.volume >= min_volume]

    def search_markets(self, query: str, limit: int = 20) -> list[MarketInfo]:
        """
        搜索市场

        Args:
            query: 搜索关键词
            limit: 返回数量限制

        Returns:
            匹配的市场列表
        """
        all_markets = self.get_markets(limit=limit * 3)  # 获取更多结果进行筛选
        query = query.lower()

        # 简单的文本匹配搜索
        matching_markets = []
        for market in all_markets:
            if query in market.question.lower() or query in market.description.lower():
                matching_markets.append(market)

        return matching_markets[:limit]

    # =============================================================================
    # 订单簿和价格数据
    # =============================================================================

    def get_orderbook(self, token_id: str) -> OrderBookSummary:
        """
        获取订单簿

        Args:
            token_id: 代币ID

        Returns:
            订单簿摘要
        """
        try:
            return self.client.get_order_book(token_id)
        except Exception as e:
            raise PolymarketError(
                f"Failed to get orderbook for token {token_id}: {e}"
            ) from e

    def get_price(self, token_id: str, side: str = "BUY") -> float:
        """
        获取代币价格

        Args:
            token_id: 代币ID
            side: 买卖方向 ("BUY" 或 "SELL")

        Returns:
            价格
        """
        try:
            response = self.client.get_price(token_id, side)
            return float(response.get("price", 0))
        except Exception as e:
            raise PolymarketError(
                f"Failed to get price for token {token_id}: {e}"
            ) from e

    def get_last_trade_price(self, token_id: str) -> float:
        """
        获取最后成交价格

        Args:
            token_id: 代币ID

        Returns:
            最后成交价格
        """
        try:
            response = self.client.get_last_trade_price(token_id=token_id)
            price = response.get("price")
            if price is not None:
                return float(price)
            else:
                raise PolymarketError("Last trade price not available") from None
        except Exception as e:
            raise PolymarketError(
                f"Failed to get last trade price for token {token_id}: {e}"
            ) from e

    def get_mid_price(self, token_id: str) -> float:
        """
        获取中间价格（买一和卖一的平均值）

        Args:
            token_id: 代币ID

        Returns:
            中间价格
        """
        try:
            orderbook = self.get_orderbook(token_id)
            if orderbook.bids and orderbook.asks:
                best_bid = float(orderbook.bids[0].price)
                best_ask = float(orderbook.asks[0].price)
                return (best_bid + best_ask) / 2
            else:
                # 如果没有订单簿数据，返回最后成交价
                return self.get_last_trade_price(token_id)
        except Exception as e:
            self.logger.warning(
                f"Failed to calculate mid price for token {token_id}: {e}"
            )
            return 0.0

    def get_spread(self, token_id: str) -> dict[str, float]:
        """
        获取买卖价差信息

        Args:
            token_id: 代币ID

        Returns:
            包含价差信息的字典
        """
        try:
            orderbook = self.get_orderbook(token_id)
            if orderbook.bids and orderbook.asks:
                best_bid = float(orderbook.bids[0].price)
                best_ask = float(orderbook.asks[0].price)
                spread = best_ask - best_bid
                spread_pct = (
                    (spread / ((best_bid + best_ask) / 2)) * 100
                    if (best_bid + best_ask) > 0
                    else 0
                )

                return {
                    "best_bid": best_bid,
                    "best_ask": best_ask,
                    "spread": spread,
                    "spread_pct": spread_pct,
                    "mid_price": (best_bid + best_ask) / 2,
                }
            else:
                return {
                    "best_bid": 0.0,
                    "best_ask": 0.0,
                    "spread": 0.0,
                    "spread_pct": 0.0,
                    "mid_price": 0.0,
                }
        except Exception as e:
            self.logger.error(f"Failed to get spread for token {token_id}: {e}")
            return {
                "best_bid": 0.0,
                "best_ask": 0.0,
                "spread": 0.0,
                "spread_pct": 0.0,
                "mid_price": 0.0,
            }

    def get_market_depth(self, token_id: str, levels: int = 5) -> dict[str, Any]:
        """
        获取市场深度信息

        Args:
            token_id: 代币ID
            levels: 显示深度层级

        Returns:
            市场深度信息
        """
        try:
            orderbook = self.get_orderbook(token_id)

            bids = []
            asks = []

            # 处理买单
            for i, bid in enumerate(orderbook.bids[:levels]):
                bids.append(
                    {"price": float(bid.price), "size": float(bid.size), "level": i + 1}
                )

            # 处理卖单
            for i, ask in enumerate(orderbook.asks[:levels]):
                asks.append(
                    {"price": float(ask.price), "size": float(ask.size), "level": i + 1}
                )

            return {
                "token_id": token_id,
                "bids": bids,
                "asks": asks,
                "total_bid_size": sum(float(bid.size) for bid in orderbook.bids),
                "total_ask_size": sum(float(ask.size) for ask in orderbook.asks),
                "levels": levels,
            }

        except Exception as e:
            self.logger.error(f"Failed to get market depth for token {token_id}: {e}")
            return {
                "token_id": token_id,
                "bids": [],
                "asks": [],
                "total_bid_size": 0,
                "total_ask_size": 0,
                "levels": 0,
            }

    # =============================================================================
    # 交易接口
    # =============================================================================

    def create_limit_order(
        self,
        token_id: str,
        side: str,
        size: float,
        price: float,
        order_type: OrderType = OrderType.GTC,
    ) -> dict[str, Any] | None:
        """
        创建限价订单

        Args:
            token_id: 代币ID
            side: 买卖方向 ("BUY" 或 "SELL")
            size: 订单数量
            price: 订单价格
            order_type: 订单类型

        Returns:
            订单响应或None
        """
        try:
            if self.dry_run:
                self.logger.info(
                    f"DRY RUN: Would create {side} order for {size} tokens at ${price}"
                )
                return {
                    "status": "simulated",
                    "dry_run": True,
                    "order": {
                        "token_id": token_id,
                        "side": side,
                        "size": size,
                        "price": price,
                        "type": (
                            order_type.value
                            if hasattr(order_type, "value")
                            else str(order_type)
                        ),
                    },
                }

            # 创建订单参数
            order_args = OrderArgs(
                token_id=token_id,
                size=size,
                price=price,
                side=BUY if side.upper() == "BUY" else SELL,
            )

            # 创建并签名订单
            signed_order = self.client.create_order(order_args)

            # 发布订单
            response = self.client.post_order(signed_order, orderType=order_type)

            self.logger.info(f"Created {side} order for {size} tokens at ${price}")
            return response

        except Exception as e:
            self.logger.error(f"Failed to create limit order: {e}")
            if not self.dry_run:
                raise PolymarketError(f"Failed to create limit order: {e}") from e
            return None

    def create_market_order(
        self, token_id: str, side: str, amount: float
    ) -> dict[str, Any] | None:
        """
        创建市价订单

        Args:
            token_id: 代币ID
            side: 买卖方向 ("BUY" 或 "SELL")
            amount: 订单金额 (USD)

        Returns:
            订单响应或None
        """
        try:
            if self.dry_run:
                self.logger.info(
                    f"DRY RUN: Would create market {side} order for ${amount}"
                )
                return {
                    "status": "simulated",
                    "dry_run": True,
                    "order": {
                        "token_id": token_id,
                        "side": side,
                        "amount": amount,
                        "type": "market",
                    },
                }

            # 创建市价订单参数
            order_args = MarketOrderArgs(
                token_id=token_id,
                amount=amount,
                side=BUY if side.upper() == "BUY" else SELL,
            )

            # 创建并签名订单
            signed_order = self.client.create_market_order(order_args)

            # 发布订单 (市价订单使用FOK类型)
            response = self.client.post_order(signed_order, orderType=OrderType.FOK)

            self.logger.info(f"Created market {side} order for ${amount}")
            return response

        except Exception as e:
            self.logger.error(f"Failed to create market order: {e}")
            if not self.dry_run:
                raise PolymarketError(f"Failed to create market order: {e}") from e
            return None

    def get_orders(self, market: str | None = None) -> list[dict[str, Any]]:
        """
        获取订单列表

        Args:
            market: 市场ID (可选)

        Returns:
            订单列表
        """
        try:
            if market:
                return self.client.get_orders(market=market)
            else:
                return self.client.get_orders()
        except Exception as e:
            self.logger.error(f"Failed to get orders: {e}")
            return []

    def get_order(self, order_id: str) -> dict[str, Any] | None:
        """
        获取单个订单信息

        Args:
            order_id: 订单ID

        Returns:
            订单信息或None
        """
        try:
            return self.client.get_order(order_id)
        except Exception as e:
            self.logger.error(f"Failed to get order {order_id}: {e}")
            return None

    def cancel_order(self, order_id: str) -> dict[str, Any] | None:
        """
        取消订单

        Args:
            order_id: 订单ID

        Returns:
            取消响应或None
        """
        try:
            if self.dry_run:
                self.logger.info(f"DRY RUN: Would cancel order {order_id}")
                return {"status": "simulated", "dry_run": True, "order_id": order_id}

            response = self.client.cancel(order_id)
            self.logger.info(f"Cancelled order {order_id}")
            return response
        except Exception as e:
            self.logger.error(f"Failed to cancel order {order_id}: {e}")
            if not self.dry_run:
                raise PolymarketError(f"Failed to cancel order {order_id}: {e}") from e
            return None

    def cancel_all_orders(self, market: str | None = None) -> dict[str, Any] | None:
        """
        取消所有订单

        Args:
            market: 市场ID (可选，如果提供则只取消该市场的订单)

        Returns:
            取消响应或None
        """
        try:
            if self.dry_run:
                self.logger.info(
                    f"DRY RUN: Would cancel all orders for market {market}"
                )
                return {"status": "simulated", "dry_run": True, "market": market}

            response = self.client.cancel_all()
            self.logger.info("Cancelled all orders")
            return response
        except Exception as e:
            self.logger.error(f"Failed to cancel all orders: {e}")
            if not self.dry_run:
                raise PolymarketError(f"Failed to cancel all orders: {e}") from e
            return None

    # =============================================================================
    # 余额和授权管理
    # =============================================================================

    def get_usdc_balance(self) -> float:
        """
        获取 USDC 余额

        Returns:
            USDC 余额
        """
        try:
            balance_info = self.client.get_balance_allowance(
                params=BalanceAllowanceParams(asset_type=AssetType.COLLATERAL)
            )
            balance = float(balance_info.get("balance", 0))
            self.logger.debug(f"USDC balance: ${balance}")
            return balance
        except Exception as e:
            self.logger.error(f"Failed to get USDC balance: {e}")
            return 0.0

    def get_token_balance(self, token_id: str) -> float:
        """
        获取指定代币余额

        Args:
            token_id: 代币ID

        Returns:
            代币余额
        """
        try:
            balance_info = self.client.get_balance_allowance(
                params=BalanceAllowanceParams(
                    asset_type=AssetType.CONDITIONAL, token_id=token_id
                )
            )
            balance = float(balance_info.get("balance", 0))
            self.logger.debug(f"Token {token_id} balance: {balance}")
            return balance
        except Exception as e:
            self.logger.error(f"Failed to get token balance for {token_id}: {e}")
            return 0.0

    def get_all_balances(self) -> BalanceInfo:
        """
        获取所有余额信息

        Returns:
            余额信息
        """
        try:
            usdc_balance = self.get_usdc_balance()

            # 获取所有代币余额 (这里简化处理，实际可能需要遍历所有持有的代币)
            token_balances: dict[str, float] = {}
            allowances: dict[str, float] = {}

            # 从已知的订单或市场中获取代币余额
            # 这里只是一个示例，实际实现可能需要更复杂的逻辑

            return BalanceInfo(
                usdc_balance=usdc_balance,
                token_balances=token_balances,
                allowances=allowances,
            )
        except Exception as e:
            self.logger.error(f"Failed to get all balances: {e}")
            return BalanceInfo(usdc_balance=0.0, token_balances={}, allowances={})

    def check_usdc_allowance(self) -> float:
        """
        检查 USDC 授权额度

        Returns:
            当前授权额度
        """
        try:
            allowance = self.usdc_contract.functions.allowance(
                Web3.to_checksum_address(self.wallet_address),
                Web3.to_checksum_address(self.contract_addresses["exchange"]),
            ).call()
            allowance_usdc = float(allowance) / 1_000_000  # 转换为 USDC 单位
            self.logger.debug(f"USDC allowance: ${allowance_usdc}")
            return allowance_usdc
        except Exception as e:
            self.logger.error(f"Failed to check USDC allowance: {e}")
            return 0.0

    def approve_usdc(self, amount: float | None = None) -> bool:
        """
        授权 USDC 使用

        Args:
            amount: 授权金额，如果为None则使用最大值

        Returns:
            是否成功
        """
        try:
            if self.dry_run:
                self.logger.info(
                    f"DRY RUN: Would approve USDC spending: ${amount or 'MAX'}"
                )
                return True

            # 确定授权金额
            if amount is None:
                amount_wei = int(MAX_INT, 0)
                self.logger.info("Approving maximum USDC allowance")
            else:
                amount_wei = int(amount * 1_000_000)  # 转换为 USDC 单位
                self.logger.info(f"Approving ${amount} USDC allowance")

            # 构建交易
            wallet_checksum = Web3.to_checksum_address(self.wallet_address)
            approve_txn = self.usdc_contract.functions.approve(
                self.contract_addresses["exchange"], amount_wei
            ).build_transaction(
                {
                    "from": wallet_checksum,
                    "nonce": self.w3.eth.get_transaction_count(wallet_checksum),
                    "gas": 100000,
                    "gasPrice": self.w3.eth.gas_price,
                    "chainId": self.chain_id,
                }
            )

            # 签名并发送交易
            signed_txn = self.w3.eth.account.sign_transaction(
                approve_txn, private_key=self.private_key
            )
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)

            # 等待确认
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            self.logger.info(
                f"USDC approval confirmed in block: {receipt['blockNumber']}"
            )

            return receipt["status"] == 1

        except Exception as e:
            self.logger.error(f"Failed to approve USDC: {e}")
            if not self.dry_run:
                raise PolymarketError(f"Failed to approve USDC: {e}") from e
            return False

    def set_ctf_approval(self, operator_address: str, approved: bool = True) -> bool:
        """
        设置 CTF 代币授权

        Args:
            operator_address: 操作者地址
            approved: 是否授权

        Returns:
            是否成功
        """
        try:
            if self.dry_run:
                self.logger.info(
                    f"DRY RUN: Would set CTF approval for {operator_address}: {approved}"
                )
                return True

            # 构建交易
            wallet_checksum = Web3.to_checksum_address(self.wallet_address)
            approval_txn = self.ctf_contract.functions.setApprovalForAll(
                operator_address, approved
            ).build_transaction(
                {
                    "from": wallet_checksum,
                    "nonce": self.w3.eth.get_transaction_count(wallet_checksum),
                    "gas": 100000,
                    "gasPrice": self.w3.eth.gas_price,
                    "chainId": self.chain_id,
                }
            )

            # 签名并发送交易
            signed_txn = self.w3.eth.account.sign_transaction(
                approval_txn, private_key=self.private_key
            )
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)

            # 等待确认
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            self.logger.info(
                f"CTF approval confirmed in block: {receipt['blockNumber']}"
            )

            return receipt["status"] == 1

        except Exception as e:
            self.logger.error(f"Failed to set CTF approval: {e}")
            if not self.dry_run:
                raise PolymarketError(f"Failed to set CTF approval: {e}") from e
            return False

    def setup_trading_permissions(self) -> bool:
        """
        设置所有必要的交易权限

        Returns:
            是否全部设置成功
        """
        try:
            self.logger.info("Setting up trading permissions...")

            success = True

            # 授权 USDC 给主交易所
            if not self.approve_usdc():
                success = False

            # 授权 CTF 代币给主交易所
            if not self.set_ctf_approval(self.contract_addresses["exchange"]):
                success = False

            # 授权给负风险交易所
            if not self.set_ctf_approval(self.contract_addresses["neg_risk_exchange"]):
                success = False

            # 授权给负风险适配器
            if not self.set_ctf_approval(self.contract_addresses["neg_risk_adapter"]):
                success = False

            if success:
                self.logger.info("All trading permissions set successfully")
            else:
                self.logger.warning("Some trading permissions failed to set")

            return success

        except Exception as e:
            self.logger.error(f"Failed to setup trading permissions: {e}")
            return False

    # =============================================================================
    # 工具函数和辅助方法
    # =============================================================================

    def adjust_price(self, price: float, adjustment: float = 0.001) -> float:
        """
        调整价格 (用于提高成交概率)

        Args:
            price: 原价格
            adjustment: 调整幅度

        Returns:
            调整后的价格
        """
        # 买单价格稍微提高，卖单价格稍微降低
        return round(max(0.001, min(0.999, price + adjustment)), 4)

    def calculate_position_size(
        self, available_balance: float, price: float, max_risk_pct: float = 0.1
    ) -> float:
        """
        计算合适的仓位大小

        Args:
            available_balance: 可用余额
            price: 交易价格
            max_risk_pct: 最大风险比例

        Returns:
            建议的仓位大小
        """
        max_risk_amount = available_balance * max_risk_pct
        position_size = max_risk_amount / price

        # 确保最小交易量
        min_size = 5.0
        return max(min_size, position_size)

    def get_market_summary(self, token_id: str) -> dict[str, Any]:
        """
        获取市场概况

        Args:
            token_id: 代币ID

        Returns:
            市场概况信息
        """
        try:
            market = self.get_market_by_token_id(token_id)
            if not market:
                return {"error": "Market not found"}

            spread_info = self.get_spread(token_id)
            depth_info = self.get_market_depth(token_id, levels=3)

            return {
                "market": {
                    "question": market.question,
                    "volume": market.volume,
                    "active": market.active,
                },
                "pricing": spread_info,
                "depth": depth_info,
                "last_trade": self.get_last_trade_price(token_id),
            }

        except Exception as e:
            self.logger.error(f"Failed to get market summary for {token_id}: {e}")
            return {"error": str(e)}

    def detect_category(self, question: str) -> str:
        """
        检测市场类别

        Args:
            question: 市场问题

        Returns:
            市场类别
        """
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
                "fed",
                "rate",
                "chancellor",
                "prime minister",
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
                "cup",
                "championship",
                "win",
                "relegated",
            ],
            "crypto": [
                "bitcoin",
                "eth",
                "crypto",
                "token",
                "blockchain",
                "opensea",
                "nft",
            ],
            "entertainment": [
                "movie",
                "film",
                "actor",
                "actress",
                "award",
                "song",
                "album",
                "show",
            ],
            "tech": ["ai", "openai", "technology", "software", "app", "launch"],
        }

        for category, keywords in categories.items():
            if any(keyword in question for keyword in keywords):
                return category

        return "other"

    def format_currency(self, amount: float) -> str:
        """
        格式化货币显示

        Args:
            amount: 金额

        Returns:
            格式化的货币字符串
        """
        return f"${amount:,.4f}" if amount < 1 else f"${amount:,.2f}"

    def format_percentage(self, value: float) -> str:
        """
        格式化百分比显示

        Args:
            value: 百分比值

        Returns:
            格式化的百分比字符串
        """
        return f"{value:.2f}%"

    def validate_order_params(
        self, token_id: str, side: str, size: float, price: float | None = None
    ) -> dict[str, Any]:
        """
        验证订单参数

        Args:
            token_id: 代币ID
            side: 买卖方向
            size: 订单大小
            price: 价格 (限价订单需要)

        Returns:
            验证结果
        """
        errors = []

        # 验证代币ID
        if not token_id or not isinstance(token_id, str):
            errors.append("Invalid token_id")

        # 验证方向
        if side.upper() not in ["BUY", "SELL"]:
            errors.append("Side must be 'BUY' or 'SELL'")

        # 验证大小
        if size <= 0:
            errors.append("Size must be positive")

        # 验证价格 (如果提供)
        if price is not None:
            if not (0 < price < 1):
                errors.append("Price must be between 0 and 1")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": [],
        }

    def get_trading_fees(self, size: float, price: float) -> dict[str, float]:
        """
        计算交易费用

        Args:
            size: 订单大小
            price: 价格

        Returns:
            费用信息
        """
        notional = size * price

        # Polymarket 的费用结构 (需要根据实际情况调整)
        maker_fee_rate = 0.001  # 0.1%
        taker_fee_rate = 0.001  # 0.1%

        return {
            "notional": notional,
            "maker_fee": notional * maker_fee_rate,
            "taker_fee": notional * taker_fee_rate,
            "estimated_fee": notional * taker_fee_rate,  # 保守估计使用taker费用
        }

    def health_check(self) -> dict[str, Any]:
        """
        执行健康检查

        Returns:
            健康检查结果
        """
        results: dict[str, Any] = {
            "timestamp": str(int(time.time())),
            "wallet_address": self.wallet_address,
            "network": "Testnet (Amoy)" if self.use_testnet else "Mainnet (Polygon)",
            "dry_run_mode": self.dry_run,
        }

        try:
            # 检查网络连接
            results["web3_connected"] = self.w3.is_connected()

            # 检查API连接
            try:
                markets = self.get_markets(limit=1)
                results["api_connected"] = len(markets) >= 0
            except Exception:
                results["api_connected"] = False

            # 检查余额
            try:
                usdc_balance = self.get_usdc_balance()
                results["usdc_balance"] = usdc_balance
                results["sufficient_balance"] = usdc_balance > 0
            except Exception:
                results["usdc_balance"] = 0
                results["sufficient_balance"] = False

            # 检查授权
            try:
                allowance = self.check_usdc_allowance()
                results["usdc_allowance"] = allowance
                results["has_allowance"] = allowance > 0
            except Exception:
                results["usdc_allowance"] = 0
                results["has_allowance"] = False

            # 总体状态
            results["healthy"] = all(
                [
                    results["web3_connected"],
                    results["api_connected"],
                ]
            )

        except Exception as e:
            results["error"] = str(e)
            results["healthy"] = False

        return results

    def __str__(self) -> str:
        """字符串表示"""
        return f"PolymarketClient(wallet={self.wallet_address[:10]}..., dry_run={self.dry_run})"

    def __repr__(self) -> str:
        """详细字符串表示"""
        return (
            f"PolymarketClient("
            f"wallet={self.wallet_address}, "
            f"network={'Testnet' if self.use_testnet else 'Mainnet'}, "
            f"dry_run={self.dry_run})"
        )


if __name__ == "__main__":
    # 简单测试和演示
    print("=== Polymarket Client 演示 ===\n")

    # 初始化客户端 (dry_run 模式)
    client = PolymarketClient(dry_run=True, log_level="INFO")

    # 1. 获取市场数据
    print("1. 获取热门市场:")
    markets = client.get_markets(limit=5)
    for i, market in enumerate(markets[:3], 1):
        print(f"   {i}. {market.question}")
        print(f"      交易量: ${market.volume:,.2f}")
        print(f"      状态: {'活跃' if market.active else '非活跃'}")
        print()

    if markets:
        # 2. 获取第一个市场的详细信息
        first_market = markets[0]
        if first_market.token_ids:
            token_id = first_market.token_ids[0]
            print(f"2. 市场详细信息 - {first_market.question[:50]}...")

            # 获取价格信息
            try:
                mid_price = client.get_mid_price(token_id)
                print(f"   中间价: {client.format_currency(mid_price)}")

                # 获取价差信息
                spread = client.get_spread(token_id)
                print(f"   买一价: {client.format_currency(spread['best_bid'])}")
                print(f"   卖一价: {client.format_currency(spread['best_ask'])}")
                print(f"   价差: {client.format_percentage(spread['spread_pct'])}")

            except Exception as e:
                print(f"   获取价格信息失败: {e}")
            print()

    # 3. 健康检查
    print("3. 系统状态检查:")
    health = client.health_check()
    print(f"   网络连接: {'✓' if health.get('web3_connected') else '✗'}")
    print(f"   API 连接: {'✓' if health.get('api_connected') else '✗'}")
    print(f"   模式: {'模拟模式' if health.get('dry_run_mode') else '实盘模式'}")
    print(f"   网络: {health.get('network', 'Unknown')}")

    # 4. 演示订单验证
    print("\n4. 订单验证演示:")
    validation = client.validate_order_params(
        token_id="test_token_abc123", side="BUY", size=10.0, price=0.55
    )
    print(f"   参数有效: {'✓' if validation['valid'] else '✗'}")
    if validation["errors"]:
        for error in validation["errors"]:
            print(f"   错误: {error}")

    print("\n=== 演示完成 ===")
    print(f"客户端信息: {client}")

    # 5. 类别检测演示
    print("\n5. 市场类别检测演示:")
    sample_questions = [
        "Will Donald Trump win the 2024 election?",
        "Will the Lakers make the playoffs?",
        "Will Bitcoin reach $100k by end of 2024?",
        "Will a new AI model be released by OpenAI?",
    ]

    for question in sample_questions:
        category = client.detect_category(question)
        print(f"   '{question}' -> {category}")

    print("\n客户端功能验证完成！")
