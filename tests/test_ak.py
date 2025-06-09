import akshare as ak
import matplotlib.dates as mdates
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from devtools import pprint


def setup_chinese_font():
    """
    设置中文字体并检测可用字体
    """

    # 获取所有可用字体
    font_list = [f.name for f in fm.fontManager.ttflist]

    # 检测中文字体
    chinese_fonts = []
    possible_fonts = [
        "PingFang SC",
        "PingFang HK",
        "Hiragino Sans GB",
        "STHeiti",
        "STFangsong",
        "Microsoft YaHei",
        "SimHei",
        "WenQuanYi Micro Hei",
        "Noto Sans CJK SC",
    ]

    for font in possible_fonts:
        if font in font_list:
            chinese_fonts.append(font)

    print("检测到的中文字体：", chinese_fonts)

    if chinese_fonts:
        chosen_font = chinese_fonts[0]
        print(f"使用字体: {chosen_font}")

        # 更强制性的字体设置
        plt.rcParams.update(
            {
                "font.sans-serif": [chosen_font],
                "font.family": "sans-serif",
                "axes.unicode_minus": False,
                "font.size": 12,
            }
        )

        print(f"当前字体设置: {plt.rcParams['font.sans-serif']}")
        return chosen_font
    else:
        print("警告：未找到合适的中文字体")
        # 搜索其他可能的中文字体
        other_fonts = [
            f.name
            for f in fm.fontManager.ttflist
            if any(
                keyword in f.name.lower()
                for keyword in ["ping", "hei", "unicode", "sans"]
            )
        ]
        print("其他可能的字体：", other_fonts[:10])
        return None


# 设置中文字体
setup_chinese_font()


# 设置中文显示的全局字体大小
plt.rcParams["font.size"] = 12


print(f"最终字体设置: {plt.rcParams['font.sans-serif']}")


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
    fig, ax = plt.subplots(figsize=(15, 8))  # 使用 fig, ax 方式创建图表
    ax.plot(
        recent_data["数据日期"],
        recent_data["新增投资者-数量"],
        label="新增投资者数",
        marker="o",
    )
    ax.set_title("近三年股票市场新增投资者趋势", fontsize=16, pad=20)
    ax.set_xlabel("日期", fontsize=12)
    ax.set_ylabel("新增投资者数(万户)", fontsize=12)

    # 优化x轴日期显示
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))  # 每3个月显示一个刻度
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))  # 设置日期格式
    plt.setp(ax.get_xticklabels(), rotation=45)

    ax.legend(fontsize=12)
    ax.grid(True, linestyle="--", alpha=0.7)  # 添加网格线
    plt.tight_layout()
    plt.show()

    # 获取股票资金流向数据
    stock_flow = ak.stock_individual_fund_flow_rank(indicator="今日")
    print("\n资金流向数据列名：")
    print(stock_flow.columns.tolist())
    print("\n资金流向数据前5行：")
    print(stock_flow.head())

    # 获取股票龙虎榜数据（注释掉已废弃的API）
    try:
        # 尝试使用新的龙虎榜API
        stock_top_list = ak.stock_lhb_detail_em(
            start_date="20241201", end_date="20241209"
        )
        print("\n龙虎榜数据列名：")
        print(stock_top_list.columns.tolist())
        print("\n龙虎榜数据前5行：")
        print(stock_top_list.head())
    except Exception as e:
        print(f"\n获取龙虎榜数据时发生错误: {e}")
        print("该API可能已更新，请查阅最新的AKShare文档")


def analyze_stock_industry():
    """
    行业分析示例
    """
    try:
        # 获取行业板块数据
        industry_data = ak.stock_board_industry_name_em()
        print("\n行业板块列表：")
        print(industry_data.head())

        # 获取特定行业详细数据（以医药行业为例）
        medical_industry = ak.stock_board_industry_cons_em(symbol="医药制造")
        print("\n医药制造行业成分股：")
        print(medical_industry.head())

        # 可视化行业涨跌幅分布
        plt.figure(figsize=(15, 8))
        sns.boxplot(data=industry_data, y="涨跌幅")
        plt.title("行业板块涨跌幅分布")
        plt.tight_layout()
        plt.show()
    except Exception as e:
        print(f"获取行业数据时发生错误: {e}")


def analyze_fund_data():
    """
    基金数据分析示例
    """
    try:
        # 获取基金排名数据
        fund_rank = ak.fund_open_fund_rank_em()  # 修正API名称
        print("\n基金排名数据：")
        print(fund_rank.head())

        # 获取基金持仓数据
        try:
            fund_portfolio = ak.fund_portfolio_hold_em()
            print("\n基金持仓数据：")
            print(fund_portfolio.head())
        except Exception as e:
            print(f"\n获取基金持仓数据时发生错误: {e}")

        # 可视化基金收益分布
        if "近1年" in fund_rank.columns:
            plt.figure(figsize=(15, 8))
            sns.histplot(data=fund_rank, x="近1年", bins=50)
            plt.title("基金近1年收益分布")
            plt.xlabel("收益率(%)")
            plt.ylabel("基金数量")
            plt.tight_layout()
            plt.show()
        else:
            print("基金数据中没有'近1年'列，跳过可视化")
    except Exception as e:
        print(f"获取基金数据时发生错误: {e}")


def analyze_macro_economy():
    """
    宏观经济数据分析示例
    """
    try:
        # 获取GDP数据
        gdp_data = ak.macro_china_gdp()
        print("\nGDP数据：")
        print(gdp_data.head())
        print("\nGDP数据列名：")
        print(gdp_data.columns.tolist())

        # 获取CPI数据
        cpi_data = ak.macro_china_cpi_monthly()
        print("\nCPI数据：")
        print(cpi_data.head())
        print("\nCPI数据列名：")
        print(cpi_data.columns.tolist())

        # 可视化GDP增长趋势
        if len(gdp_data) > 0:
            plt.figure(figsize=(15, 8))

            # 检查可用的列名
            gdp_growth_col = None
            for col in gdp_data.columns:
                if "同比增长" in col or "增长" in col:
                    gdp_growth_col = col
                    break

            if gdp_growth_col:
                # 获取最近20个季度的数据
                recent_gdp = gdp_data.tail(20)

                plt.plot(
                    range(len(recent_gdp)),
                    recent_gdp[gdp_growth_col],
                    marker="o",
                    linewidth=2,
                    markersize=6,
                )
                plt.title("GDP同比增长趋势", fontsize=16)
                plt.xlabel("季度（倒序）", fontsize=12)
                plt.ylabel("同比增长(%)", fontsize=12)
                plt.grid(True, alpha=0.3)

                # 设置x轴标签
                quarter_labels = recent_gdp["季度"].tolist()
                plt.xticks(range(len(recent_gdp)), quarter_labels, rotation=45)

                plt.tight_layout()
                plt.show()

                # 打印统计信息
                print("\nGDP统计信息（最近20个季度）：")
                print(f"平均增长率: {recent_gdp[gdp_growth_col].mean():.2f}%")
                print(f"最高增长率: {recent_gdp[gdp_growth_col].max():.2f}%")
                print(f"最低增长率: {recent_gdp[gdp_growth_col].min():.2f}%")
                print(f"最新增长率: {recent_gdp[gdp_growth_col].iloc[-1]:.2f}%")
            else:
                print("未找到GDP增长率相关列，跳过可视化")

        # 可视化CPI趋势
        if len(cpi_data) > 0:
            plt.figure(figsize=(15, 8))

            # 获取最近24个月的数据
            recent_cpi = cpi_data.tail(24)

            plt.plot(
                range(len(recent_cpi)),
                recent_cpi["今值"],
                marker="s",
                linewidth=2,
                markersize=4,
                color="red",
            )
            plt.axhline(y=0, color="gray", linestyle="--", alpha=0.5)
            plt.title("CPI月率趋势", fontsize=16)
            plt.xlabel("月份（倒序）", fontsize=12)
            plt.ylabel("CPI月率(%)", fontsize=12)
            plt.grid(True, alpha=0.3)

            # 设置x轴标签（每隔3个月显示一个）
            try:
                # 尝试转换日期格式
                if pd.api.types.is_datetime64_any_dtype(recent_cpi["日期"]):
                    date_labels = recent_cpi["日期"].dt.strftime("%Y-%m").tolist()
                else:
                    # 如果不是datetime类型，尝试转换
                    date_labels = (
                        pd.to_datetime(recent_cpi["日期"]).dt.strftime("%Y-%m").tolist()
                    )

                step = max(1, len(date_labels) // 8)  # 显示大约8个标签
                plt.xticks(
                    range(0, len(recent_cpi), step),
                    [date_labels[i] for i in range(0, len(date_labels), step)],
                    rotation=45,
                )
            except Exception as e:
                print(f"日期格式化失败: {e}")
                # 使用简单的数字标签
                plt.xticks(
                    range(0, len(recent_cpi), 3),
                    [f"第{i + 1}期" for i in range(0, len(recent_cpi), 3)],
                    rotation=45,
                )

            plt.tight_layout()
            plt.show()

            # 打印统计信息
            print("\nCPI统计信息（最近24个月）：")
            print(f"平均CPI月率: {recent_cpi['今值'].mean():.2f}%")
            print(f"最高CPI月率: {recent_cpi['今值'].max():.2f}%")
            print(f"最低CPI月率: {recent_cpi['今值'].min():.2f}%")
            print(f"最新CPI月率: {recent_cpi['今值'].iloc[-1]:.2f}%")

    except Exception as e:
        print(f"获取宏观经济数据时发生错误: {e}")


def analyze_market_sentiment():
    """
    市场情绪指标分析示例
    """
    try:
        # 获取北向资金数据 - 使用可用的API
        try:
            # 使用沪深港通资金流向汇总API
            north_money = ak.stock_hsgt_fund_flow_summary_em()
            print("\n沪深港通资金流向汇总：")
            print(north_money.head())

            # 获取历史北向资金数据
            north_hist = ak.stock_hsgt_hist_em(symbol="北向资金")
            print("\n北向资金历史数据：")
            print(north_hist.head())

            # 可视化北向资金流向
            if len(north_hist) > 0:
                plt.figure(figsize=(15, 8))

                # 获取最近30个交易日的数据
                recent_data = north_hist.tail(30)

                plt.plot(
                    recent_data["日期"],
                    recent_data["当日成交净买额"],
                    marker="o",
                    linewidth=2,
                    label="当日成交净买额",
                )
                plt.axhline(y=0, color="r", linestyle="--", alpha=0.5, label="零轴")

                plt.title("北向资金近30日流向", fontsize=16)
                plt.xlabel("日期", fontsize=12)
                plt.ylabel("资金流入(万元)", fontsize=12)
                plt.legend(fontsize=12)
                plt.grid(True, alpha=0.3)
                plt.xticks(rotation=45)
                plt.tight_layout()
                plt.show()

                # 打印统计信息
                print("\n北向资金统计信息（最近30个交易日）：")
                print(f"平均净买额: {recent_data['当日成交净买额'].mean():.2f}万元")
                print(f"最大净买额: {recent_data['当日成交净买额'].max():.2f}万元")
                print(f"最小净买额: {recent_data['当日成交净买额'].min():.2f}万元")
                print(f"累计净买额: {recent_data['当日成交净买额'].sum():.2f}万元")

        except Exception as e:
            print(f"获取北向资金数据时发生错误: {e}")

        # 获取融资融券数据 - 使用可用的API
        try:
            # 使用上交所融资融券数据
            margin_sse = ak.stock_margin_sse()
            print("\n上交所融资融券数据：")
            print(margin_sse.head())

            # 使用深交所融资融券数据
            margin_szse = ak.stock_margin_szse()
            print("\n深交所融资融券数据：")
            print(margin_szse.head())

            # 可视化融资融券余额趋势
            if len(margin_sse) > 10:
                plt.figure(figsize=(15, 8))

                # 获取最近20个交易日的数据
                recent_margin = margin_sse.tail(20)

                plt.subplot(2, 1, 1)
                plt.plot(
                    recent_margin["信用交易日期"],
                    recent_margin["融资余额"],
                    marker="o",
                    label="融资余额",
                    color="blue",
                )
                plt.title("上交所融资余额趋势", fontsize=14)
                plt.ylabel("融资余额(万元)", fontsize=12)
                plt.legend()
                plt.grid(True, alpha=0.3)
                plt.xticks(rotation=45)

                plt.subplot(2, 1, 2)
                plt.plot(
                    recent_margin["信用交易日期"],
                    recent_margin["融券余量金额"],
                    marker="s",
                    label="融券余额",
                    color="red",
                )
                plt.title("上交所融券余额趋势", fontsize=14)
                plt.xlabel("日期", fontsize=12)
                plt.ylabel("融券余额(万元)", fontsize=12)
                plt.legend()
                plt.grid(True, alpha=0.3)
                plt.xticks(rotation=45)

                plt.tight_layout()
                plt.show()

                # 打印统计信息
                print("\n融资融券统计信息（最近20个交易日）：")
                print(f"平均融资余额: {recent_margin['融资余额'].mean():.2f}万元")
                print(f"平均融券余额: {recent_margin['融券余量金额'].mean():.2f}万元")
                print(
                    f"融资余额变化: {recent_margin['融资余额'].iloc[-1] - recent_margin['融资余额'].iloc[0]:.2f}万元"
                )

        except Exception as e:
            print(f"获取融资融券数据时发生错误: {e}")
            # 尝试获取融资融券标的信息
            try:
                margin_info = ak.stock_margin_underlying_info_szse()
                print("\n深交所融资融券标的信息（前10只）：")
                print(margin_info.head(10))
            except Exception as e2:
                print(f"获取融资融券标的信息也失败: {e2}")

    except Exception as e:
        print(f"获取市场情绪数据时发生错误: {e}")


def analyze_market_index():
    """
    市场指数分析示例
    """
    try:
        # 获取上证指数数据
        sh_index = ak.stock_zh_index_daily(symbol="sh000001")

        if sh_index.empty:
            print("获取上证指数数据为空")
            return

        # 确保数据有足够的行数
        if len(sh_index) < 20:
            print(f"数据量不足，只有{len(sh_index)}行数据")
            return

        # 计算移动平均线
        sh_index["MA5"] = sh_index["close"].rolling(window=5).mean()
        sh_index["MA20"] = sh_index["close"].rolling(window=20).mean()

        # 绘制K线图和均线
        plt.figure(figsize=(15, 8))

        # 获取最近100个交易日的数据，如果数据不足则使用全部数据
        plot_length = min(100, len(sh_index))

        plt.plot(
            sh_index.index[-plot_length:],
            sh_index["close"].iloc[-plot_length:],
            label="收盘价",
            linewidth=2,
        )
        plt.plot(
            sh_index.index[-plot_length:],
            sh_index["MA5"].iloc[-plot_length:],
            label="5日均线",
            alpha=0.8,
        )
        plt.plot(
            sh_index.index[-plot_length:],
            sh_index["MA20"].iloc[-plot_length:],
            label="20日均线",
            alpha=0.8,
        )

        plt.title("上证指数走势图", fontsize=16)
        plt.xlabel("日期", fontsize=12)
        plt.ylabel("指数", fontsize=12)
        plt.legend(fontsize=12)
        plt.grid(True, alpha=0.3)
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.show()

        # 打印一些统计信息
        print(f"\n上证指数统计信息（最近{plot_length}个交易日）：")
        print(f"最高点: {sh_index['close'].iloc[-plot_length:].max():.2f}")
        print(f"最低点: {sh_index['close'].iloc[-plot_length:].min():.2f}")
        print(f"当前价格: {sh_index['close'].iloc[-1]:.2f}")
        print(f"5日均线: {sh_index['MA5'].iloc[-1]:.2f}")
        print(f"20日均线: {sh_index['MA20'].iloc[-1]:.2f}")

    except Exception as e:
        print(f"获取市场指数数据时发生错误: {e}")
        # 尝试其他指数API
        try:
            print("尝试使用备用API获取指数数据...")
            sh_index_alt = ak.index_zh_a_hist(
                symbol="000001",
                period="daily",
                start_date="20240101",
                end_date="20241231",
            )
            print("备用API获取成功，数据前5行：")
            print(sh_index_alt.head())
        except Exception as e2:
            print(f"备用API也失败: {e2}")


def test_available_apis():
    """
    测试可用的akshare API函数
    """
    print("=== 测试可用的akshare API ===")

    # 测试北向资金相关API
    print("\n1. 测试北向资金相关API:")
    north_apis = [
        "stock_hsgt_north_net_flow_in_em",
        "stock_hsgt_fund_flow_summary_em",
        "stock_hsgt_hist_em",
        "stock_hsgt_north_acc_flow_in_em",
        "stock_hsgt_south_net_flow_in_em",
    ]

    for api_name in north_apis:
        if hasattr(ak, api_name):
            print(f"✓ {api_name} - 可用")
            try:
                # 尝试调用API（某些可能需要参数）
                if api_name == "stock_hsgt_north_net_flow_in_em":
                    result = getattr(ak, api_name)(indicator="沪股通")
                elif api_name == "stock_hsgt_hist_em":
                    result = getattr(ak, api_name)(symbol="北向资金")
                else:
                    result = getattr(ak, api_name)()
                print(
                    f"  数据形状: {result.shape if hasattr(result, 'shape') else 'N/A'}"
                )
                if hasattr(result, "columns"):
                    print(f"  列名: {list(result.columns)[:5]}...")  # 只显示前5列
            except Exception as e:
                print(f"  调用失败: {str(e)[:100]}...")
        else:
            print(f"✗ {api_name} - 不可用")

    # 测试融资融券相关API
    print("\n2. 测试融资融券相关API:")
    margin_apis = [
        "stock_margin_sz_summary",
        "stock_margin_detail_fund_flow_em",
        "stock_margin_underlying_info_szse",
        "stock_margin_underlying_info_sse",
        "stock_margin_sse",
        "stock_margin_szse",
    ]

    for api_name in margin_apis:
        if hasattr(ak, api_name):
            print(f"✓ {api_name} - 可用")
            try:
                result = getattr(ak, api_name)()
                print(
                    f"  数据形状: {result.shape if hasattr(result, 'shape') else 'N/A'}"
                )
                if hasattr(result, "columns"):
                    print(f"  列名: {list(result.columns)[:5]}...")
            except Exception as e:
                print(f"  调用失败: {str(e)[:100]}...")
        else:
            print(f"✗ {api_name} - 不可用")

    # 测试指数相关API
    print("\n3. 测试指数相关API:")
    index_apis = [
        "stock_zh_index_daily",
        "index_zh_a_hist",
        "stock_zh_index_hist",
        "index_zh_a_hist_min_em",
    ]

    for api_name in index_apis:
        if hasattr(ak, api_name):
            print(f"✓ {api_name} - 可用")
            try:
                if api_name == "stock_zh_index_daily":
                    result = getattr(ak, api_name)(symbol="sh000001")
                elif api_name == "index_zh_a_hist":
                    result = getattr(ak, api_name)(
                        symbol="000001",
                        period="daily",
                        start_date="20241201",
                        end_date="20241209",
                    )
                elif api_name == "stock_zh_index_hist":
                    result = getattr(ak, api_name)(
                        symbol="000001",
                        period="daily",
                        start_date="20241201",
                        end_date="20241209",
                    )
                else:
                    result = getattr(ak, api_name)()
                print(
                    f"  数据形状: {result.shape if hasattr(result, 'shape') else 'N/A'}"
                )
                if hasattr(result, "columns"):
                    print(f"  列名: {list(result.columns)[:5]}...")
            except Exception as e:
                print(f"  调用失败: {str(e)[:100]}...")
        else:
            print(f"✗ {api_name} - 不可用")


def main():
    # 简单测试中文字体显示
    # print("=== 测试中文字体显示 ===")

    # # 创建一个简单的测试图表
    # fig, ax = plt.subplots(figsize=(10, 6))
    # ax.plot([1, 2, 3, 4], [1, 4, 2, 3], marker="o", label="测试数据")
    # ax.set_title("测试中文标题：上证指数走势图", fontsize=16)
    # ax.set_xlabel("日期", fontsize=12)
    # ax.set_ylabel("指数", fontsize=12)
    # ax.legend()
    # ax.grid(True)
    # plt.tight_layout()
    # plt.show()
    # print("如果图表中的中文显示正常，则字体设置成功！")

    # 首先测试可用的API
    # print("\n=== 测试可用的API ===")
    # test_available_apis()

    # 运行股票开户数据分析
    # print("\n=== 运行股票开户数据分析 ===")
    # test_stock_account_statistics_em()

    # 运行各个分析函数
    print("\n=== 开始市场数据分析 ===")

    # print("\n1. 分析行业数据")
    # analyze_stock_industry()

    # print("\n2. 分析基金数据")
    # analyze_fund_data()

    # print("\n3. 分析宏观经济数据")
    # analyze_macro_economy()

    # print("\n4. 分析市场情绪")
    # analyze_market_sentiment()

    print("\n5. 分析市场指数")
    analyze_market_index()


if __name__ == "__main__":
    main()
