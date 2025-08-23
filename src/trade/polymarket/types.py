"""
Polymarket类型定义
"""

from datetime import datetime
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Dict, Any


class MarketStatus(Enum):
    """市场状态"""
    ACTIVE = "active"
    CLOSED = "closed"
    RESOLVED = "resolved"


class OrderSide(Enum):
    """订单方向"""
    BUY = "BUY"
    SELL = "SELL"


class OrderType(Enum):
    """订单类型"""
    LIMIT = "limit"
    MARKET = "market"
    GTC = "gtc"
    FOK = "fok"


class OrderStatus(Enum):
    """订单状态"""
    OPEN = "open"
    FILLED = "filled"
    CANCELLED = "cancelled"
    PARTIALLY_FILLED = "partially_filled"


@dataclass
class OutcomeToken:
    """结果代币信息"""
    token_id: str
    outcome: str
    price: float
    volume: float = 0.0


@dataclass
class MarketInfo:
    """市场信息"""
    id: str
    question: str
    description: str
    end_date: datetime
    status: MarketStatus
    volume: float
    liquidity: float
    outcomes: List[OutcomeToken]
    condition_id: Optional[str] = None
    neg_risk: bool = False
    category: str = "other"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "question": self.question,
            "description": self.description,
            "end_date": self.end_date.isoformat(),
            "status": self.status.value,
            "volume": self.volume,
            "liquidity": self.liquidity,
            "outcomes": [
                {
                    "token_id": outcome.token_id,
                    "outcome": outcome.outcome,
                    "price": outcome.price,
                    "volume": outcome.volume,
                }
                for outcome in self.outcomes
            ],
            "condition_id": self.condition_id,
            "neg_risk": self.neg_risk,
            "category": self.category,
        }


@dataclass
class OrderInfo:
    """订单信息"""
    id: str
    market_id: str
    token_id: str
    side: OrderSide
    order_type: OrderType
    status: OrderStatus
    size: float
    price: float
    filled_size: float = 0.0
    remaining_size: float = 0.0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    fee_rate: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "market_id": self.market_id,
            "token_id": self.token_id,
            "side": self.side.value,
            "order_type": self.order_type.value,
            "status": self.status.value,
            "size": self.size,
            "price": self.price,
            "filled_size": self.filled_size,
            "remaining_size": self.remaining_size,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "fee_rate": self.fee_rate,
        }


@dataclass
class PositionInfo:
    """持仓信息"""
    token_id: str
    market_id: str
    outcome: str
    size: float
    avg_price: float
    current_price: float
    last_updated: datetime
    
    @property
    def market_value(self) -> float:
        """市场价值"""
        return self.size * self.current_price
    
    @property
    def cost_basis(self) -> float:
        """成本基础"""
        return self.size * self.avg_price
    
    @property
    def unrealized_pnl(self) -> float:
        """未实现盈亏"""
        return self.market_value - self.cost_basis
    
    @property
    def unrealized_pnl_pct(self) -> float:
        """未实现盈亏百分比"""
        if self.cost_basis == 0:
            return 0.0
        return (self.unrealized_pnl / self.cost_basis) * 100
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "token_id": self.token_id,
            "market_id": self.market_id,
            "outcome": self.outcome,
            "size": self.size,
            "avg_price": self.avg_price,
            "current_price": self.current_price,
            "market_value": self.market_value,
            "cost_basis": self.cost_basis,
            "unrealized_pnl": self.unrealized_pnl,
            "unrealized_pnl_pct": self.unrealized_pnl_pct,
            "last_updated": self.last_updated.isoformat(),
        }


@dataclass
class BalanceInfo:
    """余额信息"""
    usdc_balance: float
    total_position_value: float
    available_balance: float
    margin_used: float
    last_updated: datetime
    
    @property
    def total_equity(self) -> float:
        """总权益"""
        return self.usdc_balance + self.total_position_value
    
    @property
    def margin_ratio(self) -> float:
        """保证金比例"""
        if self.total_equity == 0:
            return 0.0
        return self.margin_used / self.total_equity
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "usdc_balance": self.usdc_balance,
            "total_position_value": self.total_position_value,
            "available_balance": self.available_balance,
            "margin_used": self.margin_used,
            "total_equity": self.total_equity,
            "margin_ratio": self.margin_ratio,
            "last_updated": self.last_updated.isoformat(),
        }


@dataclass
class PriceData:
    """价格数据"""
    token_id: str
    price: float
    volume: float
    timestamp: datetime
    source: str = "api"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "token_id": self.token_id,
            "price": self.price,
            "volume": self.volume,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
        }

