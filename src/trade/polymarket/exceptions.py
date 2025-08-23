"""
Polymarket异常定义
"""

from typing import Optional


class PolymarketError(Exception):
    """Polymarket基础异常"""
    pass


class NetworkError(PolymarketError):
    """网络连接异常"""
    pass


class APIError(PolymarketError):
    """API调用异常"""
    
    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class OrderError(PolymarketError):
    """订单相关异常"""
    pass


class ValidationError(PolymarketError):
    """参数验证异常"""
    pass


class ConfigError(PolymarketError):
    """配置异常"""
    pass
