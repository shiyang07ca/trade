"""
TA-Lib (Technical Analysis Library) 常见使用实例

本文件展示了如何使用TA-Lib库进行技术分析，包括：
1. 趋势指标 (移动平均线、MACD、ADX)
2. 动量指标 (RSI、随机指标、威廉指标)
3. 波动率指标 (布林带、ATR)
4. 成交量指标 (OBV、AD)
5. 价格模式识别
6. 支撑阻力指标
"""

import os
import sys
import warnings

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from trade.utils import setup_chinese_font

warnings.filterwarnings("ignore")

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import talib

    print("TA-Lib 版本:", talib.__version__)
except ImportError:
    print("请先安装 TA-Lib: pip install TA-Lib")
    sys.exit(1)


# 设置中文字体
setup_chinese_font()


def load_sample_data():
    """
    加载示例数据 - 从CSV文件读取或生成模拟数据

    Returns:
        pd.DataFrame: 包含OHLCV数据的DataFrame
    """
    # 尝试从现有数据文件加载
    data_files = [
        "data/btc_usdt_1d_20200122_to_20250714.csv",
        "data/eth_usdt_1d_20200122_to_20250714.csv",
        "data/sample_data.csv",
    ]

    for file_path in data_files:
        if os.path.exists(file_path):
            print(f"加载数据文件: {file_path}")
            df = pd.read_csv(file_path)

            # 数据预处理
            if "datetime" in df.columns:
                df["date"] = pd.to_datetime(df["datetime"])
            elif "date" in df.columns:
                df["date"] = pd.to_datetime(df["date"])
            else:
                df["date"] = pd.date_range(
                    start="2020-01-01", periods=len(df), freq="D"
                )

            # 确保必要的列存在
            required_columns = ["open", "high", "low", "close", "volume"]
            for col in required_columns:
                if col not in df.columns:
                    print(f"缺少必要列: {col}")
                    continue

            # 转换数据类型
            for col in required_columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

            # 移除缺失值
            df = df.dropna()

            # 取最近500个交易日的数据
            df = df.tail(500).copy()
            df.reset_index(drop=True, inplace=True)

            print(f"数据加载完成，共 {len(df)} 条记录")
            print(f"时间范围: {df['date'].min()} 至 {df['date'].max()}")
            return df

    # 如果没有找到数据文件，生成模拟数据
    print("未找到数据文件，生成模拟数据...")
    return generate_mock_data()


def generate_mock_data():
    """
    生成模拟的OHLCV数据用于测试

    Returns:
        pd.DataFrame: 模拟的OHLCV数据
    """
    np.random.seed(42)

    # 生成500个交易日的数据
    dates = pd.date_range(start="2020-01-01", periods=500, freq="D")

    # 模拟价格走势（几何布朗运动）
    initial_price = 100
    returns = np.random.normal(0.001, 0.02, len(dates))  # 日收益率
    prices = [initial_price]

    for i in range(1, len(dates)):
        price = prices[-1] * (1 + returns[i])
        prices.append(price)

    # 生成OHLCV数据
    data = []
    for i, date in enumerate(dates):
        close = prices[i]
        # 模拟日内价格波动
        daily_volatility = np.random.uniform(0.01, 0.05)
        high = close * (1 + np.random.uniform(0, daily_volatility))
        low = close * (1 - np.random.uniform(0, daily_volatility))
        open_price = low + np.random.uniform(0, 1) * (high - low)
        volume = np.random.uniform(1000000, 10000000)

        data.append(
            {
                "date": date,
                "open": open_price,
                "high": high,
                "low": low,
                "close": close,
                "volume": volume,
            }
        )

    df = pd.DataFrame(data)
    print(f"生成模拟数据完成，共 {len(df)} 条记录")
    return df


def calculate_trend_indicators(df):
    """
    计算趋势指标

    Args:
        df (pd.DataFrame): 包含OHLCV数据的DataFrame

    Returns:
        pd.DataFrame: 添加了趋势指标的DataFrame
    """
    print("计算趋势指标...")

    # 转换为numpy数组（TA-Lib需要）
    high = df["high"].values
    low = df["low"].values
    close = df["close"].values
    volume = df["volume"].values

    # 1. 移动平均线 (Moving Averages)
    # 简单移动平均线
    df["SMA_5"] = talib.SMA(close, timeperiod=5)  # 5日简单移动平均
    df["SMA_20"] = talib.SMA(close, timeperiod=20)  # 20日简单移动平均
    df["SMA_50"] = talib.SMA(close, timeperiod=50)  # 50日简单移动平均

    # 指数移动平均线
    df["EMA_12"] = talib.EMA(close, timeperiod=12)  # 12日指数移动平均
    df["EMA_26"] = talib.EMA(close, timeperiod=26)  # 26日指数移动平均

    # 加权移动平均线
    df["WMA_10"] = talib.WMA(close, timeperiod=10)  # 10日加权移动平均

    # 2. MACD (Moving Average Convergence Divergence)
    # MACD线 = 12日EMA - 26日EMA
    # 信号线 = MACD线的9日EMA
    # 柱状图 = MACD线 - 信号线
    macd, macd_signal, macd_hist = talib.MACD(
        close, fastperiod=12, slowperiod=26, signalperiod=9
    )
    df["MACD"] = macd
    df["MACD_Signal"] = macd_signal
    df["MACD_Hist"] = macd_hist

    # 3. ADX (Average Directional Index) - 趋势强度指标
    df["ADX"] = talib.ADX(high, low, close, timeperiod=14)
    df["PLUS_DI"] = talib.PLUS_DI(high, low, close, timeperiod=14)  # 正方向指标
    df["MINUS_DI"] = talib.MINUS_DI(high, low, close, timeperiod=14)  # 负方向指标

    # 4. 抛物线SAR (Parabolic SAR)
    df["SAR"] = talib.SAR(high, low, acceleration=0.02, maximum=0.2)

    print("趋势指标计算完成")
    return df


def calculate_momentum_indicators(df):
    """
    计算动量指标

    Args:
        df (pd.DataFrame): 包含OHLCV数据的DataFrame

    Returns:
        pd.DataFrame: 添加了动量指标的DataFrame
    """
    print("计算动量指标...")

    high = df["high"].values
    low = df["low"].values
    close = df["close"].values

    # 1. RSI (Relative Strength Index) - 相对强弱指数
    # RSI = 100 - (100 / (1 + RS))
    # RS = 平均上涨幅度 / 平均下跌幅度
    df["RSI_14"] = talib.RSI(close, timeperiod=14)
    df["RSI_21"] = talib.RSI(close, timeperiod=21)

    # 2. 随机指标 (Stochastic Oscillator)
    # %K = (当前收盘价 - 最低价) / (最高价 - 最低价) * 100
    # %D = %K的移动平均
    slowk, slowd = talib.STOCH(
        high,
        low,
        close,
        fastk_period=5,
        slowk_period=3,
        slowk_matype=0,
        slowd_period=3,
        slowd_matype=0,
    )
    df["STOCH_K"] = slowk
    df["STOCH_D"] = slowd

    # 3. 威廉指标 (Williams %R)
    # %R = (最高价 - 当前收盘价) / (最高价 - 最低价) * -100
    df["WILLR"] = talib.WILLR(high, low, close, timeperiod=14)

    # 4. 动量指标 (Momentum)
    df["MOM"] = talib.MOM(close, timeperiod=10)

    # 5. 变化率 (Rate of Change)
    df["ROC"] = talib.ROC(close, timeperiod=10)

    # 6. 商品通道指数 (Commodity Channel Index)
    df["CCI"] = talib.CCI(high, low, close, timeperiod=14)

    print("动量指标计算完成")
    return df


def calculate_volatility_indicators(df):
    """
    计算波动率指标

    Args:
        df (pd.DataFrame): 包含OHLCV数据的DataFrame

    Returns:
        pd.DataFrame: 添加了波动率指标的DataFrame
    """
    print("计算波动率指标...")

    high = df["high"].values
    low = df["low"].values
    close = df["close"].values

    # 1. 布林带 (Bollinger Bands)
    # 中轨 = 20日简单移动平均
    # 上轨 = 中轨 + 2 * 标准差
    # 下轨 = 中轨 - 2 * 标准差
    upper, middle, lower = talib.BBANDS(
        close, timeperiod=20, nbdevup=2, nbdevdn=2, matype=0
    )
    df["BB_Upper"] = upper
    df["BB_Middle"] = middle
    df["BB_Lower"] = lower

    # 布林带宽度 (Bollinger Band Width)
    df["BB_Width"] = (upper - lower) / middle

    # 布林带位置 (%B)
    df["BB_Percent"] = (close - lower) / (upper - lower)

    # 2. ATR (Average True Range) - 平均真实波幅
    # 真实波幅 = max(高-低, abs(高-昨收), abs(低-昨收))
    df["ATR"] = talib.ATR(high, low, close, timeperiod=14)

    # 3. 标准差 (Standard Deviation)
    df["STDDEV"] = talib.STDDEV(close, timeperiod=20, nbdev=1)

    # 4. 真实波幅 (True Range)
    df["TRANGE"] = talib.TRANGE(high, low, close)

    print("波动率指标计算完成")
    return df


def calculate_volume_indicators(df):
    """
    计算成交量指标

    Args:
        df (pd.DataFrame): 包含OHLCV数据的DataFrame

    Returns:
        pd.DataFrame: 添加了成交量指标的DataFrame
    """
    print("计算成交量指标...")

    high = df["high"].values
    low = df["low"].values
    close = df["close"].values
    volume = df["volume"].values

    # 1. OBV (On-Balance Volume) - 能量潮
    # 如果收盘价上涨，OBV = 前日OBV + 今日成交量
    # 如果收盘价下跌，OBV = 前日OBV - 今日成交量
    df["OBV"] = talib.OBV(close, volume)

    # 2. AD (Accumulation/Distribution) - 聚散指标
    # AD = 前日AD + 今日CLV * 成交量
    # CLV = ((收盘价 - 最低价) - (最高价 - 收盘价)) / (最高价 - 最低价)
    df["AD"] = talib.AD(high, low, close, volume)

    # 3. ADOSC (Chaikin A/D Oscillator) - 佳庆指标
    df["ADOSC"] = talib.ADOSC(high, low, close, volume, fastperiod=3, slowperiod=10)

    print("成交量指标计算完成")
    return df


def calculate_pattern_recognition(df):
    """
    计算价格模式识别指标

    Args:
        df (pd.DataFrame): 包含OHLCV数据的DataFrame

    Returns:
        pd.DataFrame: 添加了模式识别指标的DataFrame
    """
    print("计算价格模式识别指标...")

    open_price = df["open"].values
    high = df["high"].values
    low = df["low"].values
    close = df["close"].values

    # 常见的K线模式识别
    # 1. 锤子线 (Hammer)
    df["HAMMER"] = talib.CDLHAMMER(open_price, high, low, close)

    # 2. 上吊线 (Hanging Man)
    df["HANGINGMAN"] = talib.CDLHANGINGMAN(open_price, high, low, close)

    # 3. 十字星 (Doji)
    df["DOJI"] = talib.CDLDOJI(open_price, high, low, close)

    # 4. 吞没模式 (Engulfing Pattern)
    df["ENGULFING"] = talib.CDLENGULFING(open_price, high, low, close)

    # 5. 晨星 (Morning Star)
    df["MORNINGSTAR"] = talib.CDLMORNINGSTAR(open_price, high, low, close)

    # 6. 暮星 (Evening Star)
    df["EVENINGSTAR"] = talib.CDLEVENINGSTAR(open_price, high, low, close)

    # 7. 纺锤线 (Spinning Top)
    df["SPINNINGTOP"] = talib.CDLSPINNINGTOP(open_price, high, low, close)

    print("价格模式识别指标计算完成")
    return df


def calculate_support_resistance(df):
    """
    计算支撑阻力相关指标

    Args:
        df (pd.DataFrame): 包含OHLCV数据的DataFrame

    Returns:
        pd.DataFrame: 添加了支撑阻力指标的DataFrame
    """
    print("计算支撑阻力指标...")

    high = df["high"].values
    low = df["low"].values
    close = df["close"].values

    # 1. 枢轴点 (Pivot Points) - 使用前一日的高低收价格计算
    # 标准枢轴点 = (高 + 低 + 收) / 3
    # 支撑1 = 2 * 枢轴点 - 高
    # 阻力1 = 2 * 枢轴点 - 低
    df["PP"] = (df["high"].shift(1) + df["low"].shift(1) + df["close"].shift(1)) / 3
    df["R1"] = 2 * df["PP"] - df["low"].shift(1)
    df["S1"] = 2 * df["PP"] - df["high"].shift(1)
    df["R2"] = df["PP"] + (df["high"].shift(1) - df["low"].shift(1))
    df["S2"] = df["PP"] - (df["high"].shift(1) - df["low"].shift(1))

    # 2. 最高价和最低价 (Highest High, Lowest Low)
    df["HH_20"] = talib.MAX(high, timeperiod=20)  # 20日最高价
    df["LL_20"] = talib.MIN(low, timeperiod=20)  # 20日最低价

    # 3. 最高价和最低价的位置
    df["MAXINDEX"] = talib.MAXINDEX(high, timeperiod=20)  # 最高价位置
    df["MININDEX"] = talib.MININDEX(low, timeperiod=20)  # 最低价位置

    print("支撑阻力指标计算完成")
    return df


def plot_trend_indicators(df):
    """
    绘制趋势指标图表

    Args:
        df (pd.DataFrame): 包含技术指标的DataFrame
    """
    fig, axes = plt.subplots(3, 1, figsize=(15, 12))

    # 1. 价格和移动平均线
    ax1 = axes[0]
    ax1.plot(df["date"], df["close"], label="收盘价", linewidth=1)
    ax1.plot(df["date"], df["SMA_5"], label="SMA(5)", alpha=0.7)
    ax1.plot(df["date"], df["SMA_20"], label="SMA(20)", alpha=0.7)
    ax1.plot(df["date"], df["SMA_50"], label="SMA(50)", alpha=0.7)
    ax1.plot(df["date"], df["EMA_12"], label="EMA(12)", alpha=0.7, linestyle="--")
    ax1.plot(df["date"], df["EMA_26"], label="EMA(26)", alpha=0.7, linestyle="--")
    ax1.set_title("价格与移动平均线", fontsize=14)
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # 2. MACD
    ax2 = axes[1]
    ax2.plot(df["date"], df["MACD"], label="MACD", linewidth=1)
    ax2.plot(df["date"], df["MACD_Signal"], label="信号线", linewidth=1)
    ax2.bar(df["date"], df["MACD_Hist"], label="MACD柱状图", alpha=0.3)
    ax2.axhline(y=0, color="black", linestyle="-", alpha=0.3)
    ax2.set_title("MACD指标", fontsize=14)
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    # 3. ADX
    ax3 = axes[2]
    ax3.plot(df["date"], df["ADX"], label="ADX", linewidth=2)
    ax3.plot(df["date"], df["PLUS_DI"], label="+DI", linewidth=1)
    ax3.plot(df["date"], df["MINUS_DI"], label="-DI", linewidth=1)
    ax3.axhline(y=25, color="red", linestyle="--", alpha=0.5, label="强趋势线(25)")
    ax3.set_title("ADX趋势强度指标", fontsize=14)
    ax3.legend()
    ax3.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.show()


def plot_momentum_indicators(df):
    """
    绘制动量指标图表

    Args:
        df (pd.DataFrame): 包含技术指标的DataFrame
    """
    fig, axes = plt.subplots(3, 1, figsize=(15, 12))

    # 1. RSI
    ax1 = axes[0]
    ax1.plot(df["date"], df["RSI_14"], label="RSI(14)", linewidth=2)
    ax1.axhline(y=70, color="red", linestyle="--", alpha=0.5, label="超买线(70)")
    ax1.axhline(y=30, color="green", linestyle="--", alpha=0.5, label="超卖线(30)")
    ax1.axhline(y=50, color="black", linestyle="-", alpha=0.3)
    ax1.set_title("RSI相对强弱指数", fontsize=14)
    ax1.set_ylim(0, 100)
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # 2. 随机指标
    ax2 = axes[1]
    ax2.plot(df["date"], df["STOCH_K"], label="%K", linewidth=1)
    ax2.plot(df["date"], df["STOCH_D"], label="%D", linewidth=1)
    ax2.axhline(y=80, color="red", linestyle="--", alpha=0.5, label="超买线(80)")
    ax2.axhline(y=20, color="green", linestyle="--", alpha=0.5, label="超卖线(20)")
    ax2.set_title("随机指标(KD)", fontsize=14)
    ax2.set_ylim(0, 100)
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    # 3. 威廉指标
    ax3 = axes[2]
    ax3.plot(df["date"], df["WILLR"], label="Williams %R", linewidth=2)
    ax3.axhline(y=-20, color="red", linestyle="--", alpha=0.5, label="超买线(-20)")
    ax3.axhline(y=-80, color="green", linestyle="--", alpha=0.5, label="超卖线(-80)")
    ax3.set_title("威廉指标(%R)", fontsize=14)
    ax3.set_ylim(-100, 0)
    ax3.legend()
    ax3.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.show()


def plot_volatility_indicators(df):
    """
    绘制波动率指标图表

    Args:
        df (pd.DataFrame): 包含技术指标的DataFrame
    """
    fig, axes = plt.subplots(2, 1, figsize=(15, 10))

    # 1. 布林带
    ax1 = axes[0]
    ax1.plot(df["date"], df["close"], label="收盘价", linewidth=1)
    ax1.plot(df["date"], df["BB_Upper"], label="布林上轨", alpha=0.7)
    ax1.plot(df["date"], df["BB_Middle"], label="布林中轨", alpha=0.7)
    ax1.plot(df["date"], df["BB_Lower"], label="布林下轨", alpha=0.7)
    ax1.fill_between(df["date"], df["BB_Upper"], df["BB_Lower"], alpha=0.1)
    ax1.set_title("布林带指标", fontsize=14)
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # 2. ATR
    ax2 = axes[1]
    ax2.plot(df["date"], df["ATR"], label="ATR(14)", linewidth=2)
    ax2.set_title("平均真实波幅(ATR)", fontsize=14)
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.show()


def plot_volume_indicators(df):
    """
    绘制成交量指标图表

    Args:
        df (pd.DataFrame): 包含技术指标的DataFrame
    """
    fig, axes = plt.subplots(3, 1, figsize=(15, 12))

    # 1. 价格和成交量
    ax1 = axes[0]
    ax1.plot(df["date"], df["close"], label="收盘价", linewidth=1)
    ax1.set_title("收盘价", fontsize=14)
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # 2. OBV
    ax2 = axes[1]
    ax2.plot(df["date"], df["OBV"], label="OBV", linewidth=2, color="orange")
    ax2.set_title("能量潮(OBV)", fontsize=14)
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    # 3. AD
    ax3 = axes[2]
    ax3.plot(df["date"], df["AD"], label="A/D Line", linewidth=2, color="purple")
    ax3.set_title("聚散指标(A/D)", fontsize=14)
    ax3.legend()
    ax3.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.show()


def analyze_trading_signals(df):
    """
    分析交易信号

    Args:
        df (pd.DataFrame): 包含技术指标的DataFrame

    Returns:
        pd.DataFrame: 包含交易信号的DataFrame
    """
    print("分析交易信号...")

    # 1. 移动平均线交叉信号
    df["MA_Signal"] = 0
    df.loc[
        (df["SMA_5"] > df["SMA_20"]) & (df["SMA_5"].shift(1) <= df["SMA_20"].shift(1)),
        "MA_Signal",
    ] = 1  # 金叉
    df.loc[
        (df["SMA_5"] < df["SMA_20"]) & (df["SMA_5"].shift(1) >= df["SMA_20"].shift(1)),
        "MA_Signal",
    ] = -1  # 死叉

    # 2. MACD信号
    df["MACD_Signal_Trade"] = 0
    df.loc[
        (df["MACD"] > df["MACD_Signal"])
        & (df["MACD"].shift(1) <= df["MACD_Signal"].shift(1)),
        "MACD_Signal_Trade",
    ] = 1  # 金叉
    df.loc[
        (df["MACD"] < df["MACD_Signal"])
        & (df["MACD"].shift(1) >= df["MACD_Signal"].shift(1)),
        "MACD_Signal_Trade",
    ] = -1  # 死叉

    # 3. RSI信号
    df["RSI_Signal"] = 0
    df.loc[df["RSI_14"] < 30, "RSI_Signal"] = 1  # 超卖买入
    df.loc[df["RSI_14"] > 70, "RSI_Signal"] = -1  # 超买卖出

    # 4. 布林带信号
    df["BB_Signal"] = 0
    df.loc[df["close"] < df["BB_Lower"], "BB_Signal"] = 1  # 价格跌破下轨买入
    df.loc[df["close"] > df["BB_Upper"], "BB_Signal"] = -1  # 价格突破上轨卖出

    # 5. 综合信号 (多个指标确认)
    df["Combined_Signal"] = 0

    # 买入信号: 至少2个指标同时发出买入信号
    buy_conditions = (
        (df["MA_Signal"] == 1)
        + (df["MACD_Signal_Trade"] == 1)
        + (df["RSI_Signal"] == 1)
        + (df["BB_Signal"] == 1)
    )
    df.loc[buy_conditions >= 2, "Combined_Signal"] = 1

    # 卖出信号: 至少2个指标同时发出卖出信号
    sell_conditions = (
        (df["MA_Signal"] == -1)
        + (df["MACD_Signal_Trade"] == -1)
        + (df["RSI_Signal"] == -1)
        + (df["BB_Signal"] == -1)
    )
    df.loc[sell_conditions >= 2, "Combined_Signal"] = -1

    # 统计信号数量
    buy_signals = (df["Combined_Signal"] == 1).sum()
    sell_signals = (df["Combined_Signal"] == -1).sum()

    print("交易信号统计:")
    print(f"  买入信号: {buy_signals} 次")
    print(f"  卖出信号: {sell_signals} 次")

    return df


def plot_trading_signals(df):
    """
    绘制交易信号图表

    Args:
        df (pd.DataFrame): 包含交易信号的DataFrame
    """
    fig, ax = plt.subplots(figsize=(15, 8))

    # 绘制价格
    ax.plot(df["date"], df["close"], label="收盘价", linewidth=1)

    # 绘制移动平均线
    ax.plot(df["date"], df["SMA_5"], label="SMA(5)", alpha=0.7)
    ax.plot(df["date"], df["SMA_20"], label="SMA(20)", alpha=0.7)

    # 标记买入信号
    buy_signals = df[df["Combined_Signal"] == 1]
    ax.scatter(
        buy_signals["date"],
        buy_signals["close"],
        color="green",
        marker="^",
        s=100,
        label="买入信号",
        zorder=5,
    )

    # 标记卖出信号
    sell_signals = df[df["Combined_Signal"] == -1]
    ax.scatter(
        sell_signals["date"],
        sell_signals["close"],
        color="red",
        marker="v",
        s=100,
        label="卖出信号",
        zorder=5,
    )

    ax.set_title("交易信号图表", fontsize=14)
    ax.legend()
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.show()


def generate_report(df):
    """
    生成技术分析报告

    Args:
        df (pd.DataFrame): 包含技术指标的DataFrame
    """
    print("\n" + "=" * 50)
    print("技术分析报告")
    print("=" * 50)

    # 基本信息
    print(
        f"数据期间: {df['date'].min().strftime('%Y-%m-%d')} 至 {df['date'].max().strftime('%Y-%m-%d')}"
    )
    print(f"总交易日: {len(df)} 天")
    print(f"起始价格: {df['close'].iloc[0]:.2f}")
    print(f"结束价格: {df['close'].iloc[-1]:.2f}")
    print(
        f"期间涨跌幅: {((df['close'].iloc[-1] / df['close'].iloc[0]) - 1) * 100:.2f}%"
    )
    print(f"最高价: {df['high'].max():.2f}")
    print(f"最低价: {df['low'].min():.2f}")

    # 当前技术指标状态
    last_row = df.iloc[-1]
    print("\n当前技术指标状态:")
    print(
        f"RSI(14): {last_row['RSI_14']:.2f} - {'超买' if last_row['RSI_14'] > 70 else '超卖' if last_row['RSI_14'] < 30 else '中性'}"
    )
    print(f"MACD: {last_row['MACD']:.4f}")
    print(
        f"ADX: {last_row['ADX']:.2f} - {'强趋势' if last_row['ADX'] > 25 else '弱趋势'}"
    )
    print(
        f"布林带位置: {last_row['BB_Percent']:.2f} - {'上轨附近' if last_row['BB_Percent'] > 0.8 else '下轨附近' if last_row['BB_Percent'] < 0.2 else '中轨附近'}"
    )

    # 趋势分析
    print("\n趋势分析:")
    sma_5 = last_row["SMA_5"]
    sma_20 = last_row["SMA_20"]
    sma_50 = last_row["SMA_50"]

    if sma_5 > sma_20 > sma_50:
        trend = "上升趋势"
    elif sma_5 < sma_20 < sma_50:
        trend = "下降趋势"
    else:
        trend = "震荡趋势"

    print(f"短期趋势: {trend}")
    print(f"SMA(5): {sma_5:.2f}")
    print(f"SMA(20): {sma_20:.2f}")
    print(f"SMA(50): {sma_50:.2f}")

    # 波动率分析
    print("\n波动率分析:")
    print(f"ATR(14): {last_row['ATR']:.2f}")
    print(f"布林带宽度: {last_row['BB_Width']:.4f}")

    # 成交量分析
    print("\n成交量分析:")
    print(f"OBV: {last_row['OBV']:.0f}")
    print(f"A/D: {last_row['AD']:.0f}")

    # 模式识别
    print("\n最近识别的K线模式:")
    pattern_columns = [
        "HAMMER",
        "HANGINGMAN",
        "DOJI",
        "ENGULFING",
        "MORNINGSTAR",
        "EVENINGSTAR",
    ]
    recent_patterns = df[pattern_columns].tail(5)

    pattern_names = {
        "HAMMER": "锤子线",
        "HANGINGMAN": "上吊线",
        "DOJI": "十字星",
        "ENGULFING": "吞没模式",
        "MORNINGSTAR": "晨星",
        "EVENINGSTAR": "暮星",
    }

    for i, (_, row) in enumerate(recent_patterns.iterrows()):
        date = df.iloc[-(5 - i)]["date"]
        patterns = []
        for col in pattern_columns:
            if row[col] != 0:
                patterns.append(f"{pattern_names[col]}({row[col]})")
        if patterns:
            print(f"{date.strftime('%Y-%m-%d')}: {', '.join(patterns)}")

    print("\n" + "=" * 50)


def main():
    """
    主函数 - 执行完整的技术分析流程
    """
    print("开始TA-Lib技术分析...")

    # 1. 加载数据
    df = load_sample_data()

    # 2. 计算各类技术指标
    df = calculate_trend_indicators(df)
    df = calculate_momentum_indicators(df)
    df = calculate_volatility_indicators(df)
    df = calculate_volume_indicators(df)
    df = calculate_pattern_recognition(df)
    df = calculate_support_resistance(df)

    # 3. 分析交易信号
    df = analyze_trading_signals(df)

    # 4. 生成图表
    print("\n生成技术分析图表...")
    plot_trend_indicators(df)
    plot_momentum_indicators(df)
    plot_volatility_indicators(df)
    plot_volume_indicators(df)
    plot_trading_signals(df)

    # 5. 生成报告
    generate_report(df)

    print("\n技术分析完成!")

    return df


if __name__ == "__main__":
    # 执行完整的技术分析
    result_df = main()

    # 可选: 保存结果到CSV
    output_file = "technical_analysis_results.csv"
    result_df.to_csv(output_file, index=False)
    print(f"\n分析结果已保存至: {output_file}")
