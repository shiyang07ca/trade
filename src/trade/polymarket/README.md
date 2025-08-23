# Polymarket 交易客户端 v3.0 - 重构版

简化的同步 Polymarket 客户端，专注于核心功能和易用性。

## 🎯 重构目标

本次重构的主要目标：
- **简化架构**: 从8个子模块合并为4个核心文件
- **同步化**: 移除所有异步代码，使用同步HTTP请求
- **精简功能**: 保留核心功能，移除复杂的不常用特性
- **提高可用性**: 简化API，减少配置复杂度

## 📁 新架构

```
polymarket/
├── __init__.py          # 主入口和导出
├── client.py           # 统一客户端 (合并所有核心功能)
├── config.py           # 配置管理
├── types.py            # 所有类型定义
├── exceptions.py       # 异常定义
├── storage.py          # 可选的简化存储
└── examples/
    └── simple_usage.py  # 使用示例
```

## 🚀 主要特性

### 核心功能
- **市场数据获取**: 实时市场信息、价格数据、订单簿
- **订单管理**: 限价单、市价单创建和管理
- **投资组合管理**: 持仓查询、余额管理
- **简单缓存**: 内存缓存减少API调用
- **可选存储**: 轻量级SQLite存储

### 简化特性
- **同步API**: 所有操作都是同步的，无需async/await
- **统一接口**: 单一客户端类提供所有功能
- **简化配置**: 最少必需配置，支持环境变量
- **模拟模式**: 内置dry-run模式用于测试

## 📦 安装依赖

```bash
pip install py-clob-client requests web3 python-dotenv
```

## ⚙️ 环境配置

创建 `.env` 文件：

```bash
# 必需配置
PK=your_private_key_here

# 可选配置
DRY_RUN=true                    # 模拟模式
ENABLE_CACHE=true               # 启用缓存
ENABLE_STORAGE=false            # 启用存储
LOG_LEVEL=INFO                  # 日志级别
```

## 🔧 快速开始

### 基础使用

```python
from trade.polymarket import PolymarketClient, OrderSide

# 初始化客户端 (从环境变量加载配置)
client = PolymarketClient()

# 获取市场数据
markets = client.get_markets(limit=10)
print(f"获取到 {len(markets)} 个市场")

# 获取余额信息
balance = client.get_balance_info()
print(f"USDC余额: ${balance.usdc_balance:.2f}")

# 创建限价订单 (模拟模式)
if markets:
    token_id = markets[0].outcomes[0].token_id
    response = client.create_limit_order(
        token_id=token_id,
        side=OrderSide.BUY,
        size=10.0,
        price=0.55
    )
    print(f"订单创建: {response}")
```

### 手动配置

```python
from trade.polymarket import PolymarketClient, ClientConfig

config = ClientConfig(
    private_key="0x...",
    dry_run=True,
    enable_cache=True,
    enable_storage=False,
    log_level="INFO"
)

client = PolymarketClient(config)
```

## 📊 API 参考

### 市场数据

```python
# 获取市场列表
markets = client.get_markets(active_only=True, limit=100, category="politics")

# 搜索市场
results = client.search_markets("election", limit=20)

# 获取价格
price = client.get_price(token_id, side="BUY")
mid_price = client.get_mid_price(token_id)

# 获取订单簿
orderbook = client.get_orderbook(token_id)
```

### 交易操作

```python
# 创建限价订单
response = client.create_limit_order(
    token_id="0x123...",
    side=OrderSide.BUY,
    size=10.0,
    price=0.55
)

# 创建市价订单
response = client.create_market_order(
    token_id="0x123...",
    side=OrderSide.SELL,
    amount=100.0
)

# 查询订单
orders = client.get_orders()

# 取消订单
success = client.cancel_order(order_id)
success = client.cancel_all_orders()
```

### 投资组合

```python
# 获取余额信息
balance = client.get_balance_info()

# 获取代币余额
token_balance = client.get_token_balance(token_id)

# 计算仓位大小
size = client.calculate_position_size(
    available_balance=1000.0,
    price=0.55,
    max_risk_pct=0.1
)
```

## 🛠️ 配置选项

### ClientConfig 参数

```python
@dataclass
class ClientConfig:
    # 必需配置
    private_key: str
    
    # API端点
    clob_url: str = "https://clob.polymarket.com"
    gamma_url: str = "https://gamma-api.polymarket.com"
    
    # 区块链配置
    polygon_rpc: str = "https://polygon-rpc.com"
    chain_id: int = 137  # 137 for Polygon, 80002 for Amoy
    
    # 交易配置
    dry_run: bool = True
    
    # 功能开关
    enable_cache: bool = True
    enable_storage: bool = False
    
    # 其他配置
    log_level: str = "INFO"
    cache_ttl: int = 300  # 缓存TTL (秒)
```

## 🔧 工具方法

```python
# 健康检查
health = client.health_check()

# 清空缓存
client.clear_cache()

# 清理旧数据 (如果启用存储)
stats = client.cleanup_old_data(days=30)
```

## ❌ 错误处理

```python
from trade.polymarket import (
    PolymarketError, APIError, NetworkError, 
    OrderError, ValidationError
)

try:
    response = client.create_limit_order(...)
except ValidationError as e:
    print(f"参数验证失败: {e}")
except OrderError as e:
    print(f"订单创建失败: {e}")
except APIError as e:
    print(f"API调用失败: {e}")
```

## 🎨 最佳实践

### 1. 使用模拟模式进行测试

```python
# 在生产环境前先使用模拟模式测试
config = ClientConfig(
    private_key="0x...",
    dry_run=True  # 启用模拟模式
)
client = PolymarketClient(config)
```

### 2. 启用缓存减少API调用

```python
# 启用缓存以提高性能
markets = client.get_markets(use_cache=True)
```

### 3. 参数验证

```python
# 在创建订单前进行基础验证
try:
    response = client.create_limit_order(
        token_id=token_id,
        side=OrderSide.BUY,
        size=10.0,
        price=0.55,
        validate=True  # 启用验证
    )
except ValidationError as e:
    print(f"订单参数无效: {e}")
```

### 4. 错误恢复

```python
import time

def get_markets_with_retry(client, max_retries=3):
    for attempt in range(max_retries):
        try:
            return client.get_markets()
        except APIError as e:
            if attempt == max_retries - 1:
                raise
            time.sleep(2 ** attempt)  # 指数退避
```

## 📈 性能优化

### 缓存使用
- 市场数据默认缓存5分钟
- 价格数据不缓存（实时性要求高）
- 手动清理缓存: `client.clear_cache()`

### 存储功能
- 可选启用SQLite存储历史数据
- 自动清理旧数据: `client.cleanup_old_data(days=30)`

## 🔄 从v2.0迁移

### 主要变化

1. **移除异步**: 所有 `async def` 改为 `def`，移除 `await`
2. **统一接口**: 所有功能合并到 `PolymarketClient`
3. **简化导入**: 
   ```python
   # v2.0
   from trade.polymarket.data import MarketDataService
   from trade.polymarket.trading import OrderManager
   
   # v3.0
   from trade.polymarket import PolymarketClient
   ```
4. **配置简化**: 使用 `ClientConfig` 替代多个配置类

### 迁移示例

```python
# v2.0 (旧版)
import asyncio
from trade.polymarket import PolymarketClient

async def main():
    client = PolymarketClient()
    markets = await client.get_markets()
    balance = await client.get_balance_info()

asyncio.run(main())

# v3.0 (新版)
from trade.polymarket import PolymarketClient

client = PolymarketClient()
markets = client.get_markets()
balance = client.get_balance_info()
```

## 🐛 故障排除

### 常见问题

1. **私钥格式错误**
   ```
   ValueError: Invalid private key format
   ```
   确保私钥以 `0x` 开头且长度为66个字符

2. **网络连接失败**
   ```
   NetworkError: Cannot connect to Web3
   ```
   检查 `POLYGON_RPC` 配置和网络连接

3. **API调用失败**
   ```
   APIError: Failed to fetch markets: 429
   ```
   启用缓存或增加请求间隔

### 调试模式

```python
import logging

# 启用详细日志
config = ClientConfig(
    private_key="0x...",
    log_level="DEBUG"
)
client = PolymarketClient(config)
```

## 📝 版本历史

### v3.0.0 (重构版)
- ✅ 完全重构为同步架构
- ✅ 简化模块结构 (8个模块 → 4个文件)
- ✅ 统一客户端接口
- ✅ 移除复杂的异步依赖
- ✅ 简化配置和使用方式
- ✅ 提供完整的迁移指南

### v2.0.0 (旧版)
- 模块化异步架构
- 复杂的服务分层
- 完整的历史数据功能

### v1.0.0
- 基础功能实现

---

**注意**: 本版本专注于简化和易用性。如果需要高级功能如异步处理、复杂的历史数据分析等，可以考虑基于当前架构进行扩展。