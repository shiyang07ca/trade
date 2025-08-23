"""
Polymarket 交易客户端 - 重构版

简化的同步客户端，提供：
- 市场数据获取
- 订单管理和交易执行
- 投资组合管理
- 可选的数据存储
"""

from .client import PolymarketClient
from .config import ClientConfig
from .exceptions import (
    APIError,
    ConfigError,
    NetworkError,
    OrderError,
    PolymarketError,
    ValidationError,
)
from .types import (
    BalanceInfo,
    MarketInfo,
    MarketStatus,
    OrderInfo,
    OrderSide,
    OrderStatus,
    OrderType,
    OutcomeToken,
    PositionInfo,
)

__version__ = "3.0.0"

__all__ = [
    # Client
    "PolymarketClient",
    "ClientConfig",
    # Types
    "BalanceInfo",
    "MarketInfo",
    "MarketStatus",
    "OrderInfo",
    "OrderSide",
    "OrderStatus",
    "OrderType",
    "OutcomeToken",
    "PositionInfo",
    # Exceptions
    "APIError",
    "ConfigError",
    "NetworkError",
    "OrderError",
    "PolymarketError",
    "ValidationError",
]
