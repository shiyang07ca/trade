# Polymarket Client 封装

这是一个对 Polymarket API 的简洁抽象封装，方便量化策略开发和研究。

## 功能特性

### 1. 核心架构
- 统一的错误处理和日志记录
- 灵活的配置管理 (支持测试网和主网)
- Dry run 模式支持，便于安全测试
- 完整的类型提示支持

### 2. 市场数据接口
- 获取市场列表和详细信息
- 实时价格数据和订单簿
- 市场深度和价差分析
- 高交易量市场筛选
- 市场搜索功能

### 3. 交易接口
- 限价单和市价单创建
- 订单管理 (查询、取消)
- 余额查询 (USDC 和代币)
- 智能合约授权管理
- 一键设置交易权限

### 4. 工具函数
- 价格调整和仓位计算
- 交易费用计算
- 市场类别自动检测
- 订单参数验证
- 系统健康检查

## 使用示例

```python
from polymarket import PolymarketClient

# 初始化客户端 (模拟模式)
client = PolymarketClient(dry_run=True, log_level="INFO")

# 获取热门市场
markets = client.get_markets(limit=10)
for market in markets[:5]:
    print(f"{market.question} - Volume: ${market.volume:,.2f}")

# 获取价格信息
if markets:
    token_id = markets[0].token_ids[0]
    price = client.get_mid_price(token_id)
    spread = client.get_spread(token_id)
    print(f"中间价: ${price:.4f}")
    print(f"价差: {spread['spread_pct']:.2f}%")

# 创建限价单 (模拟模式)
response = client.create_limit_order(
    token_id=token_id,
    side="BUY",
    size=10.0,
    price=0.55
)

# 系统健康检查
health = client.health_check()
print(f"系统状态: {'健康' if health['healthy'] else '异常'}")
```

## 安全特性

### Dry Run 模式
- 默认启用模拟模式，不会执行实际交易
- 所有交易操作都会记录日志但不发送到链上
- 便于策略开发和调试

### 参数验证
- 自动验证订单参数的合理性
- 价格范围检查 (0-1)
- 代币ID 和交易方向验证

### 错误处理
- 统一的异常处理机制
- 详细的错误日志记录
- 优雅的降级处理

## 配置说明

### 环境变量
```bash
# 必需
PK=your_private_key

# 可选 (如果有现有API凭证)
CLOB_API_KEY=your_api_key
CLOB_SECRET=your_api_secret  
CLOB_PASS_PHRASE=your_passphrase

# 可选
CLOB_API_URL=https://clob.polymarket.com
POLYGON_RPC=https://polygon-rpc.com
```

### 初始化参数
- `private_key`: 钱包私钥 (如果不提供会从环境变量读取)
- `use_testnet`: 是否使用测试网络 (默认: False)
- `dry_run`: 是否为模拟模式 (默认: True)
- `log_level`: 日志级别 (默认: "INFO")

## API 覆盖

### 市场数据
- ✅ 获取市场列表
- ✅ 市场详细信息
- ✅ 实时价格
- ✅ 订单簿
- ✅ 交易深度
- ✅ 价差分析

### 交易功能
- ✅ 限价单
- ✅ 市价单
- ✅ 订单管理
- ✅ 订单查询
- ✅ 批量取消

### 账户管理
- ✅ USDC 余额
- ✅ 代币余额
- ✅ 授权管理
- ✅ 权限设置

## 开发和调试

### 日志记录
```python
# 调试模式
client = PolymarketClient(log_level="DEBUG")

# 查看详细的API调用和响应日志
```

### 健康检查
```python
health = client.health_check()
print(f"网络连接: {health['web3_connected']}")
print(f"API连接: {health['api_connected']}")
print(f"余额: ${health['usdc_balance']}")
print(f"授权: ${health['usdc_allowance']}")
```

## 注意事项

1. **安全第一**: 默认使用 dry_run 模式，实际交易前请充分测试
2. **私钥管理**: 私钥应存储在环境变量中，不要硬编码
3. **网络费用**: 所有链上操作需要支付 Polygon 网络费用
4. **API限制**: 请注意 Polymarket API 的调用频率限制
5. **授权管理**: 首次使用需要设置 USDC 和 CTF 代币的使用授权

## 扩展和定制

这个封装设计遵循简洁性原则，便于后续扩展：

- 添加新的市场指标计算
- 实现高级交易策略
- 集成风险管理模块
- 添加实时数据流支持
- 实现多账户管理

## 支持

如有问题或建议，请查看代码注释或联系开发者。代码遵循 Python 最佳实践，具有完整的类型提示和文档字符串。
