import akshare as ak
from devtools import pprint

# 获取股票日线行情数据
stock_data = ak.stock_zh_a_daily(
    symbol="sz000001", start_date="2022-01-01", end_date="2022-12-31"
)
pprint(stock_data)
