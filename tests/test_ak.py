import akshare as ak
import matplotlib.pyplot as plt
from devtools import pprint
import pandas as pd
import matplotlib.dates as mdates

# 设置中文字体
plt.rcParams["font.sans-serif"] = ["Arial Unicode MS"]  # MacOS
plt.rcParams["axes.unicode_minus"] = False  # 解决负号显示问题


def test_stock_zh_a_daily():
    # 获取股票日线行情数据
    stock_data = ak.stock_zh_a_daily(
        symbol="sz000001", start_date="2022-01-01", end_date="2022-12-31"
    )
    pprint(stock_data)


def test_stock_account_statistics_em():
    # 获取股票开户数据
    stock_account = ak.stock_account_statistics_em()

    # 将日期列转换为datetime类型
    stock_account["数据日期"] = pd.to_datetime(stock_account["数据日期"])

    # 筛选最近三年的数据
    three_years_ago = pd.Timestamp.now() - pd.DateOffset(years=3)
    recent_data = stock_account[stock_account["数据日期"] >= three_years_ago]

    print("股票开户数据列名：")
    print(recent_data.columns.tolist())
    print("\n股票开户数据前5行：")
    print(recent_data.head())

    # 获取股票开户数据趋势图
    plt.figure(figsize=(15, 8))  # 增加图表大小
    plt.plot(
        recent_data["数据日期"],
        recent_data["新增投资者-数量"],
        label="新增投资者数",
    )
    plt.title("近三年股票市场新增投资者趋势")
    plt.xlabel("日期")
    plt.ylabel("新增投资者数(万户)")

    # 优化x轴日期显示
    plt.gca().xaxis.set_major_locator(
        mdates.MonthLocator(interval=3)
    )  # 每3个月显示一个刻度
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))  # 设置日期格式
    plt.xticks(rotation=45)

    plt.legend()
    plt.grid(True)  # 添加网格线
    plt.tight_layout()
    plt.show()

    # 获取股票资金流向数据
    stock_flow = ak.stock_individual_fund_flow_rank(indicator="今日")
    print("\n资金流向数据列名：")
    print(stock_flow.columns.tolist())
    print("\n资金流向数据前5行：")
    print(stock_flow.head())

    # 获取股票龙虎榜数据
    stock_top_list = ak.stock_em_ztb()
    print("\n龙虎榜数据列名：")
    print(stock_top_list.columns.tolist())
    print("\n龙虎榜数据前5行：")
    print(stock_top_list.head())


if __name__ == "__main__":
    # test_stock_zh_a_daily()

    test_stock_account_statistics_em()
