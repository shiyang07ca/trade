"""
Polymarket客户端配置管理
"""

import os
import logging
from dataclasses import dataclass
from typing import Optional


@dataclass
class ClientConfig:
    """Polymarket客户端配置"""
    
    # 必需配置
    private_key: str
    
    # API端点
    clob_url: str = "https://clob.polymarket.com"
    gamma_url: str = "https://gamma-api.polymarket.com"
    
    # 区块链配置
    polygon_rpc: str = "https://polygon-rpc.com"
    chain_id: int = 137
    
    # API凭证（可选）
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    api_passphrase: Optional[str] = None
    
    # 交易配置
    dry_run: bool = True
    default_slippage: float = 0.01
    max_gas_price: int = 100
    
    # 日志配置
    log_level: str = "INFO"
    
    # 缓存配置
    enable_cache: bool = True
    cache_ttl: int = 300
    
    # 存储配置
    enable_storage: bool = False
    db_path: str = "data/polymarket.db"
    
    @classmethod
    def from_env(cls) -> "ClientConfig":
        """从环境变量加载配置"""
        private_key = os.getenv("PK")
        if not private_key:
            raise ValueError("Private key (PK) must be provided in environment variables")
        
        return cls(
            private_key=private_key,
            clob_url=os.getenv("CLOB_URL", "https://clob.polymarket.com"),
            gamma_url=os.getenv("GAMMA_URL", "https://gamma-api.polymarket.com"),
            polygon_rpc=os.getenv("POLYGON_RPC", "https://polygon-rpc.com"),
            chain_id=int(os.getenv("CHAIN_ID", "137")),
            api_key=os.getenv("CLOB_API_KEY"),
            api_secret=os.getenv("CLOB_SECRET"),
            api_passphrase=os.getenv("CLOB_PASS_PHRASE"),
            dry_run=os.getenv("DRY_RUN", "true").lower() == "true",
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            enable_cache=os.getenv("ENABLE_CACHE", "true").lower() == "true",
            cache_ttl=int(os.getenv("CACHE_TTL", "300")),
            enable_storage=os.getenv("ENABLE_STORAGE", "false").lower() == "true",
            db_path=os.getenv("DB_PATH", "data/polymarket.db"),
        )
    
    def validate(self) -> None:
        """验证配置"""
        if not self.private_key:
            raise ValueError("Private key is required")
        
        if not self.private_key.startswith("0x"):
            self.private_key = "0x" + self.private_key
        
        if len(self.private_key) != 66:
            raise ValueError("Invalid private key format")
        
        if self.chain_id not in [137, 80002]:
            raise ValueError("Unsupported chain ID. Use 137 (Polygon) or 80002 (Amoy)")
        
        # 验证日志级别
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.log_level.upper() not in valid_levels:
            raise ValueError(f"Invalid log level. Must be one of: {valid_levels}")
        
        self.log_level = self.log_level.upper()

