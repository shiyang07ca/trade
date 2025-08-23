"""
简化的数据存储功能
"""

import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Dict, Any

from .types import MarketInfo


class SimpleStorage:
    """简化的数据存储"""

    def __init__(self, db_path: str = "data/polymarket.db"):
        """初始化存储"""
        self.db_path = Path(db_path)
        self.logger = logging.getLogger(self.__class__.__name__)

        # 确保数据目录存在
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # 初始化数据库
        self._init_database()

    def _init_database(self) -> None:
        """初始化数据库表"""
        with sqlite3.connect(self.db_path) as conn:
            # 市场表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS markets (
                    id TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

            # 价格表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS prices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    token_id TEXT NOT NULL,
                    price REAL NOT NULL,
                    volume REAL DEFAULT 0,
                    timestamp TEXT NOT NULL,
                    source TEXT DEFAULT 'api'
                )
            """)

            # 创建索引
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_prices_token_id ON prices(token_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_prices_timestamp ON prices(timestamp)"
            )

    def save_market(self, market: MarketInfo) -> None:
        """保存市场信息"""
        try:
            now = datetime.now(timezone.utc).isoformat()
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO markets (id, data, created_at, updated_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (market.id, json.dumps(market.to_dict()), now, now),
                )
        except Exception as e:
            self.logger.error(f"Failed to save market {market.id}: {e}")

    def get_market(self, market_id: str) -> Optional[MarketInfo]:
        """获取市场信息"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT data FROM markets WHERE id = ?", (market_id,)
                )
                row = cursor.fetchone()
                if row:
                    data = json.loads(row[0])
                    # 这里需要将字典转换回MarketInfo对象
                    # 为简化起见，返回原始数据
                    return data
            return None
        except Exception as e:
            self.logger.error(f"Failed to get market {market_id}: {e}")
            return None

    def save_price(
        self, token_id: str, price: float, volume: float = 0.0, source: str = "api"
    ) -> None:
        """保存价格数据"""
        try:
            timestamp = datetime.now(timezone.utc).isoformat()
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO prices (token_id, price, volume, timestamp, source)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (token_id, price, volume, timestamp, source),
                )
        except Exception as e:
            self.logger.error(f"Failed to save price for {token_id}: {e}")

    def get_recent_prices(
        self, token_id: str, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """获取最近的价格数据"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    """
                    SELECT * FROM prices 
                    WHERE token_id = ? 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                    """,
                    (token_id, limit),
                )
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            self.logger.error(f"Failed to get prices for {token_id}: {e}")
            return []

    def get_stats(self) -> Dict[str, Any]:
        """获取存储统计信息"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM markets")
                market_count = cursor.fetchone()[0]

                cursor = conn.execute("SELECT COUNT(*) FROM prices")
                price_count = cursor.fetchone()[0]

                return {
                    "markets": market_count,
                    "prices": price_count,
                    "db_path": str(self.db_path),
                    "db_size_mb": self.db_path.stat().st_size / 1024 / 1024
                    if self.db_path.exists()
                    else 0,
                }
        except Exception as e:
            self.logger.error(f"Failed to get stats: {e}")
            return {"error": str(e)}

    def cleanup_old_prices(self, days: int = 30) -> int:
        """清理旧的价格数据"""
        try:
            cutoff = datetime.now(timezone.utc).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            cutoff = cutoff.replace(day=cutoff.day - days)
            cutoff_str = cutoff.isoformat()

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "DELETE FROM prices WHERE timestamp < ?", (cutoff_str,)
                )
                deleted = cursor.rowcount

            self.logger.info(f"Cleaned up {deleted} old price records")
            return deleted
        except Exception as e:
            self.logger.error(f"Failed to cleanup old prices: {e}")
            return 0
