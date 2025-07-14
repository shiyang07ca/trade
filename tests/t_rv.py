import os
import time
from datetime import UTC
from datetime import datetime
from datetime import timedelta

import ccxt
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy.stats as stats
import statsmodels.api as sm
from dotenv import load_dotenv

from trade.utils import setup_chinese_font

# 初始化matplotlib,使其能够正确显示中文字符,避免乱码问题
setup_chinese_font()

# 代理配置
proxies = {
    "http": "http://127.0.0.1:7890",
    "https": "http://127.0.0.1:7890",
}

# 数据获取配置
MAX_RETRIES = 5  # 最大重试次数
DELAY = 0.1  # 请求间隔
LIMIT = 1000  # 每次获取的数据条数
DATA_DIR = "data"  # 数据存储目录

# 确保数据目录存在
os.makedirs(DATA_DIR, exist_ok=True)

# Load environment variables from .env file
load_dotenv()


def create_exchange():
    """
    创建交易所实例 (优先使用Binance，因为历史数据更完整).

    Returns:
        ccxt.Exchange: 交易所实例.
    """
    try:
        # 使用Binance，因为它有更完整的历史数据
        exchange = ccxt.binance(
            {
                "proxies": proxies,
                "timeout": 30000,
                "enableRateLimit": True,
            }
        )
        return exchange
    except Exception as e:
        print(f"创建交易所实例失败: {e}")
        return None


def get_csv_path(symbol: str, timeframe: str, days: int) -> str:
    """
    生成CSV文件路径.

    Args:
        symbol (str): 交易对符号.
        timeframe (str): 时间框架.
        days (int): 天数.

    Returns:
        str: CSV文件路径.
    """
    today = datetime.now(UTC).strftime("%Y%m%d")
    start_date = (datetime.now(UTC) - timedelta(days=days)).strftime("%Y%m%d")
    clean_symbol = symbol.lower().replace("/", "_")
    return f"{DATA_DIR}/{clean_symbol}_{timeframe}_{start_date}_to_{today}.csv"


def fetch_ohlcv_since(exchange, symbol: str, timeframe: str, since: int):
    """
    从指定时间开始获取OHLCV数据，带重试机制.

    Args:
        exchange: 交易所实例.
        symbol (str): 交易对符号.
        timeframe (str): 时间框架.
        since (int): 起始时间戳.

    Returns:
        list: OHLCV数据列表.
    """
    for attempt in range(MAX_RETRIES):
        try:
            data = exchange.fetch_ohlcv(
                symbol, timeframe=timeframe, since=since, limit=LIMIT
            )
            return data
        except Exception as e:
            print(f"⚠️ [{symbol}] 第 {attempt + 1} 次重试，错误：{e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(20)  # 等待20秒后重试
    print(f"❌ [{symbol}] 多次重试失败，跳过该段。")
    return []


def fetch_crypto_data_enhanced(
    symbol: str, timeframe: str = "1h", days: int = 365
) -> pd.DataFrame:
    """
    增强版数据获取函数，支持大量历史数据获取、续传和数据持久化.

    Args:
        symbol (str): 交易对符号, 例如 'BTC/USDT'.
        timeframe (str): K线周期, 例如'1h'表示小时线.
        days (int): 获取数据的天数.

    Returns:
        pd.DataFrame: 包含加密货币历史数据的DataFrame.
    """
    print(f"\n📈 开始拉取：{symbol} ({timeframe}, 近{days}天)")

    exchange = create_exchange()
    if not exchange:
        return pd.DataFrame()

    csv_file = get_csv_path(symbol, timeframe, days)

    # 计算时间范围 (确保时间计算正确)
    now = exchange.milliseconds()
    target_start_time = now - (days * 24 * 60 * 60 * 1000)

    print(
        f"目标时间范围: {pd.to_datetime(target_start_time, unit='ms')} 至 {pd.to_datetime(now, unit='ms')}"
    )

    # 检查是否存在已有数据文件 (续传模式)
    existing_df = pd.DataFrame()
    since = target_start_time

    if os.path.exists(csv_file):
        try:
            existing_df = pd.read_csv(csv_file)
            if not existing_df.empty:
                # 转换时间列
                existing_df["datetime"] = pd.to_datetime(existing_df["datetime"])
                last_time = existing_df["datetime"].max()

                # 检查已有数据是否覆盖目标时间范围
                first_time = existing_df["datetime"].min()
                if first_time <= pd.to_datetime(target_start_time, unit="ms"):
                    print("✅ 已有数据覆盖目标时间范围，直接使用现有数据")
                    # 转换为分析用的DataFrame格式
                    result_df = existing_df.copy()
                    result_df["open"] = result_df["open"].astype(float)
                    result_df["high"] = result_df["high"].astype(float)
                    result_df["low"] = result_df["low"].astype(float)
                    result_df["close"] = result_df["close"].astype(float)
                    result_df["volume"] = result_df["volume"].astype(float)
                    result_df.rename(columns={"datetime": "date"}, inplace=True)
                    result_df.set_index("date", inplace=True)
                    result_df = result_df.sort_index()
                    return result_df

                # 计算从何时开始获取新数据
                since = int(last_time.timestamp() * 1000) + (
                    60 * 60 * 1000 if timeframe == "1h" else 24 * 60 * 60 * 1000
                )
                print(f"🔄 续传模式，从 {last_time} 开始")
        except Exception as e:
            print(f"读取已有数据失败: {e}")
            existing_df = pd.DataFrame()

    all_data = []
    batch_count = 0

    # 分批获取数据，直到覆盖目标时间范围
    while since < now:
        batch_count += 1
        print(f"📥 正在获取第 {batch_count} 批数据...")

        ohlcv = fetch_ohlcv_since(exchange, symbol, timeframe, since)
        if not ohlcv:
            print("❌ 获取数据失败，可能已达到历史数据极限")
            break

        # 检查是否获取到了更早的数据
        earliest_time = ohlcv[0][0]
        if earliest_time > target_start_time:
            print(
                f"⚠️ 获取的数据时间 {pd.to_datetime(earliest_time, unit='ms')} 晚于目标开始时间"
            )

        all_data.extend(ohlcv)

        # 如果数据不足限制条数，说明已经获取完所有数据
        if len(ohlcv) < LIMIT:
            print(f"✅ [{symbol}] 获取完成，数据不足 {LIMIT} 条")
            break

        # 更新时间指针
        time_increment = 60 * 60 * 1000 if timeframe == "1h" else 24 * 60 * 60 * 1000
        since = ohlcv[-1][0] + time_increment

        timestamp_seconds = ohlcv[-1][0] / 1000
        latest_time = datetime.fromtimestamp(timestamp_seconds, tz=UTC).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        print(f"📥 拉取到{symbol}: {len(ohlcv)} 条，最新时间（UTC）：{latest_time}")

        time.sleep(DELAY)

        # 如果已经获取了足够的数据，停止获取
        if len(all_data) >= days * (24 if timeframe == "1h" else 1):
            print(f"✅ 已获取足够数据: {len(all_data)} 条")
            break

    if not all_data:
        print(f"⚠️ 没有新数据：{symbol}")
        if not existing_df.empty:
            # 返回已有数据
            result_df = existing_df.copy()
            result_df["open"] = result_df["open"].astype(float)
            result_df["high"] = result_df["high"].astype(float)
            result_df["low"] = result_df["low"].astype(float)
            result_df["close"] = result_df["close"].astype(float)
            result_df["volume"] = result_df["volume"].astype(float)
            result_df.rename(columns={"datetime": "date"}, inplace=True)
            result_df.set_index("date", inplace=True)
            result_df = result_df.sort_index()
            return result_df
        return pd.DataFrame()

    # 转换为DataFrame
    new_df = pd.DataFrame(
        all_data, columns=["timestamp", "open", "high", "low", "close", "volume"]
    )
    new_df["datetime"] = (
        pd.to_datetime(new_df["timestamp"], unit="ms")
        .dt.tz_localize("UTC")
        .dt.tz_convert("Asia/Shanghai")
        .dt.strftime("%Y-%m-%d %H:%M:%S")
    )

    # 调整列顺序
    new_df = new_df[["datetime", "open", "high", "low", "close", "volume"]]

    # 合并新旧数据
    if not existing_df.empty:
        full_df = (
            pd.concat([existing_df, new_df])
            .drop_duplicates("datetime")
            .sort_values("datetime")
        )
    else:
        full_df = new_df.sort_values("datetime")

    # 保存到CSV文件
    full_df.to_csv(csv_file, index=False)
    print(f"✅ 保存成功：{symbol} -> {csv_file}，共 {len(full_df)} 条记录")

    # 转换为分析用的DataFrame格式
    result_df = full_df.copy()
    result_df["datetime"] = pd.to_datetime(result_df["datetime"])
    result_df["open"] = result_df["open"].astype(float)
    result_df["high"] = result_df["high"].astype(float)
    result_df["low"] = result_df["low"].astype(float)
    result_df["close"] = result_df["close"].astype(float)
    result_df["volume"] = result_df["volume"].astype(float)

    # 重命名列并设置索引
    result_df.rename(columns={"datetime": "date"}, inplace=True)
    result_df.set_index("date", inplace=True)

    # 按时间排序
    result_df = result_df.sort_index()

    print(f"最终数据时间范围: {result_df.index.min()} 至 {result_df.index.max()}")
    print(
        f"实际获取 {len(result_df)} 条记录，约 {len(result_df) / (24 if timeframe == '1h' else 1):.1f} 天"
    )

    return result_df


def fetch_crypto_data(
    symbol: str, timeframe: str = "1d", days: int = 365
) -> pd.DataFrame:
    """
    兼容性函数，调用增强版数据获取函数.
    """
    return fetch_crypto_data_enhanced(symbol, timeframe, days)


def fetch_crypto_data_with_pagination(
    symbol: str, timeframe: str = "1d", days: int = 365
) -> pd.DataFrame:
    """
    兼容性函数，调用增强版数据获取函数.
    """
    return fetch_crypto_data_enhanced(symbol, timeframe, days)


def calculate_returns(data: pd.DataFrame, timeframe: str = "1h") -> pd.Series:
    """
    计算对数收益率.

    Args:
        data (pd.DataFrame): 包含 'close' 收盘价列的DataFrame.
        timeframe (str): 时间框架，用于确定收益率类型.

    Returns:
        pd.Series: 对数收益率序列.
    """
    timeframe_name = "小时" if timeframe == "1h" else "日"
    print(f"计算{timeframe_name}对数收益率...")
    log_returns = np.log(data["close"] / data["close"].shift(1))
    return log_returns.dropna()


def calculate_volatility(
    returns: pd.Series, timeframe: str = "1h", annualize: bool = True
) -> float:
    """
    计算波动率.

    Args:
        returns (pd.Series): 对数收益率序列.
        timeframe (str): 时间框架，用于确定年化因子.
        annualize (bool): 是否年化波动率.

    Returns:
        float: 波动率值.
    """
    period_vol = returns.std()
    if annualize:
        # 根据时间框架确定年化因子
        if timeframe == "1h":
            # 小时波动率年化: sqrt(24 * 365) = sqrt(8760)
            return period_vol * np.sqrt(24 * 365)
        elif timeframe == "1d":
            # 日波动率年化: sqrt(365)
            return period_vol * np.sqrt(365)
        elif timeframe == "1w":
            # 周波动率年化: sqrt(52)
            return period_vol * np.sqrt(52)
        elif timeframe == "1m":
            # 月波动率年化: sqrt(12)
            return period_vol * np.sqrt(12)
        else:
            # 默认按日处理
            return period_vol * np.sqrt(365)
    return period_vol


def plot_price_and_returns(data: pd.DataFrame, returns: pd.Series, symbol: str):
    """
    绘制价格走势和收益率分布图.

    Args:
        data (pd.DataFrame): 价格数据.
        returns (pd.Series): 收益率数据.
        symbol (str): 交易对符号.
    """
    # 设置中文字体显示
    plt.rcParams["font.sans-serif"] = [
        "PingFang HK",
        "Hiragino Sans GB",
        "STHeiti",
        "Arial Unicode MS",
    ]
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["font.family"] = "sans-serif"

    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))

    # 1. 价格走势图
    ax1.plot(data.index, data["close"], linewidth=1, color="blue")
    ax1.set_title(f"{symbol} 价格走势", fontsize=14, pad=20)
    ax1.set_xlabel("日期", fontsize=12)
    ax1.set_ylabel("价格 (USDT)", fontsize=12)
    ax1.grid(True, alpha=0.3)
    ax1.tick_params(axis="x", rotation=45)

    # 2. 收益率时间序列
    ax2.plot(returns.index, returns, linewidth=0.8, alpha=0.7, color="green")
    ax2.set_title(f"{symbol} 日收益率", fontsize=14, pad=20)
    ax2.set_xlabel("日期", fontsize=12)
    ax2.set_ylabel("对数收益率", fontsize=12)
    ax2.grid(True, alpha=0.3)
    ax2.axhline(y=0, color="r", linestyle="--", alpha=0.5)
    ax2.tick_params(axis="x", rotation=45)

    # 3. 收益率分布直方图
    ax3.hist(
        returns, bins=50, density=True, alpha=0.7, color="skyblue", edgecolor="black"
    )
    ax3.set_title(f"{symbol} 收益率分布", fontsize=14, pad=20)
    ax3.set_xlabel("对数收益率", fontsize=12)
    ax3.set_ylabel("密度", fontsize=12)
    ax3.grid(True, alpha=0.3)

    # 4. 波动率统计
    daily_vol = calculate_volatility(returns, annualize=False)
    annual_vol = calculate_volatility(returns, annualize=True)

    stats_text = f"""统计信息:
数据期间: {data.index[0].strftime("%Y-%m-%d")} 至 {data.index[-1].strftime("%Y-%m-%d")}
样本数量: {len(returns)}

收益率统计:
均值: {returns.mean():.6f}
标准差(日): {daily_vol:.6f}
标准差(年): {annual_vol:.4f}
偏度: {returns.skew():.4f}
峰度: {returns.kurtosis():.4f}

价格统计:
最高价: {data["close"].max():.2f}
最低价: {data["close"].min():.2f}
期末价: {data["close"].iloc[-1]:.2f}"""

    ax4.text(
        0.05,
        0.95,
        stats_text,
        transform=ax4.transAxes,
        verticalalignment="top",
        fontsize=11,
        fontproperties="PingFang HK",
    )
    ax4.set_xlim(0, 1)
    ax4.set_ylim(0, 1)
    ax4.axis("off")

    plt.tight_layout(pad=3.0)
    plt.show()


def plot_qq_normality_test(returns: pd.Series, symbol: str):
    """
    使用 Q-Q 图检验收益率的正态性.

    Args:
        returns (pd.Series): 日对数收益率序列.
        symbol (str): 交易对符号.
    """
    print(f"生成 {symbol} 的QQ图以检验收益率的正态性...")

    # 设置中文字体显示
    plt.rcParams["font.sans-serif"] = [
        "PingFang HK",
        "Hiragino Sans GB",
        "STHeiti",
        "Arial Unicode MS",
    ]
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["font.family"] = "sans-serif"

    plt.figure(figsize=(10, 7))
    sm.qqplot(returns, line="s", dist=stats.norm)
    plt.title(f"{symbol} 收益率正态分布QQ图", fontsize=14, pad=20)
    plt.xlabel("理论分位数 (正态分布)", fontsize=12)
    plt.ylabel("样本分位数", fontsize=12)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()


def fit_distributions_and_compare_tails(returns: pd.Series, symbol: str):
    """
    使用 t-分布 和 正态分布 拟合收益率数据, 并比较它们对尾部概率的估计.

    Args:
        returns (pd.Series): 日对数收益率序列.
        symbol (str): 交易对符号.
    """
    print(f"\n使用t分布和正态分布拟合 {symbol} 收益率数据...")

    # 拟合正态分布
    norm_params = stats.norm.fit(returns)
    norm_mean, norm_std = norm_params
    print(f"正态分布拟合结果: 平均值 = {norm_mean:.6f}, 标准差 = {norm_std:.6f}")

    # 拟合t分布
    t_params = stats.t.fit(returns)
    t_df, t_loc, t_scale = t_params
    print(
        f"t分布拟合结果: 自由度 = {t_df:.2f}, 位置 = {t_loc:.6f}, 尺度 = {t_scale:.6f}"
    )

    # 计算尾部概率
    threshold = norm_mean - 3 * norm_std
    norm_tail_prob = stats.norm.cdf(threshold, loc=norm_mean, scale=norm_std)
    t_tail_prob = stats.t.cdf(threshold, df=t_df, loc=t_loc, scale=t_scale)
    empirical_prob = (returns < threshold).mean()

    print(f"\n比较尾部概率 (收益率 < {threshold:.4f}):")
    print(f"  - 基于正态分布的估计: {norm_tail_prob:.6%}")
    print(f"  - 基于t分布的估计: {t_tail_prob:.6%}")
    print(f"  - 样本中的实际频率: {empirical_prob:.6%}")

    # 设置中文字体显示
    plt.rcParams["font.sans-serif"] = [
        "PingFang HK",
        "Hiragino Sans GB",
        "STHeiti",
        "Arial Unicode MS",
    ]
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["font.family"] = "sans-serif"

    # 可视化比较
    plt.figure(figsize=(12, 8))
    plt.hist(
        returns,
        bins=100,
        density=True,
        alpha=0.6,
        label=f"{symbol} 收益率直方图",
        color="lightblue",
    )

    xmin, xmax = plt.xlim()
    x = np.linspace(xmin, xmax, 100)

    p_norm = stats.norm.pdf(x, norm_mean, norm_std)
    plt.plot(x, p_norm, "k", linewidth=2, label="正态分布拟合")

    p_t = stats.t.pdf(x, t_df, t_loc, t_scale)
    plt.plot(x, p_t, "r--", linewidth=2, label="t分布拟合")

    plt.title(f"{symbol} 收益率分布与拟合", fontsize=14, pad=20)
    plt.xlabel("日对数收益率", fontsize=12)
    plt.ylabel("概率密度", fontsize=12)
    plt.legend(fontsize=11)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()


def analyze_crypto_volatility(symbol: str, days: int = 365, timeframe: str = "1h"):
    """
    分析单个加密货币的波动率.

    Args:
        symbol (str): 交易对符号.
        days (int): 分析天数.
        timeframe (str): 时间框架.
    """
    print(f"\n{'=' * 50}")
    print(f"开始分析 {symbol} 的波动率 ({timeframe}, {days}天)")
    print(f"{'=' * 50}")

    # 获取数据 (使用增强版数据获取函数)
    data = fetch_crypto_data_enhanced(symbol, timeframe=timeframe, days=days)
    if data.empty:
        print(f"无法获取 {symbol} 的数据")
        return

    # 计算收益率
    returns = calculate_returns(data, timeframe)

    # 生成分析图表
    plot_price_and_returns(data, returns, symbol)
    plot_qq_normality_test(returns, symbol)
    fit_distributions_and_compare_tails(returns, symbol)

    # 计算波动率
    period_vol = calculate_volatility(returns, timeframe, annualize=False)
    annual_vol = calculate_volatility(returns, timeframe, annualize=True)

    timeframe_name = "小时" if timeframe == "1h" else "日"
    print(f"\n{symbol} 波动率分析结果:")
    print(f"  - {timeframe_name}波动率: {period_vol:.6f} ({period_vol * 100:.4f}%)")
    print(f"  - 年化波动率: {annual_vol:.4f} ({annual_vol * 100:.2f}%)")

    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "period_volatility": period_vol,
        "annual_volatility": annual_vol,
        "returns": returns,
        "data": data,
    }


def compare_volatilities(results: list[dict]):
    """
    比较不同加密货币的波动率.

    Args:
        results (list[dict]): 各加密货币的分析结果.
    """
    if len(results) < 2:
        return

    # 设置中文字体显示
    plt.rcParams["font.sans-serif"] = [
        "PingFang HK",
        "Hiragino Sans GB",
        "STHeiti",
        "Arial Unicode MS",
    ]
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["font.family"] = "sans-serif"

    plt.figure(figsize=(16, 12))

    # 波动率对比柱状图
    symbols = [r["symbol"] for r in results]
    period_vols = [r["period_volatility"] * 100 for r in results]
    annual_vols = [r["annual_volatility"] * 100 for r in results]
    timeframe = results[0].get("timeframe", "1h")
    timeframe_name = "小时" if timeframe == "1h" else "日"

    x = np.arange(len(symbols))
    width = 0.35

    plt.subplot(2, 2, 1)
    plt.bar(
        x - width / 2,
        period_vols,
        width,
        label=f"{timeframe_name}波动率",
        alpha=0.8,
        color="lightblue",
    )
    plt.bar(
        x + width / 2,
        annual_vols,
        width,
        label="年化波动率",
        alpha=0.8,
        color="lightcoral",
    )
    plt.xlabel("加密货币", fontsize=12)
    plt.ylabel("波动率 (%)", fontsize=12)
    plt.title("波动率对比", fontsize=14, pad=20)
    plt.xticks(x, symbols)
    plt.legend(fontsize=11)
    plt.grid(True, alpha=0.3)

    # 收益率分布对比
    plt.subplot(2, 2, 2)
    colors = ["lightblue", "lightcoral", "lightgreen", "lightyellow"]
    for i, result in enumerate(results):
        plt.hist(
            result["returns"],
            bins=50,
            alpha=0.6,
            label=f"{result['symbol']} 收益率",
            density=True,
            color=colors[i % len(colors)],
        )
    plt.xlabel("对数收益率", fontsize=12)
    plt.ylabel("密度", fontsize=12)
    plt.title("收益率分布对比", fontsize=14, pad=20)
    plt.legend(fontsize=11)
    plt.grid(True, alpha=0.3)

    # 价格走势对比 (标准化)
    plt.subplot(2, 2, 3)
    colors = ["blue", "red", "green", "orange"]
    for i, result in enumerate(results):
        data = result["data"]
        normalized_price = data["close"] / data["close"].iloc[0]
        plt.plot(
            data.index,
            normalized_price,
            label=f"{result['symbol']} 价格",
            alpha=0.8,
            color=colors[i % len(colors)],
        )
    plt.xlabel("日期", fontsize=12)
    plt.ylabel("标准化价格", fontsize=12)
    plt.title("价格走势对比 (标准化)", fontsize=14, pad=20)
    plt.legend(fontsize=11)
    plt.grid(True, alpha=0.3)
    plt.tick_params(axis="x", rotation=45)

    # 统计信息表
    plt.subplot(2, 2, 4)
    stats_text = "波动率统计对比:\n\n"
    for result in results:
        timeframe = result.get("timeframe", "1h")
        timeframe_name = "小时" if timeframe == "1h" else "日"
        stats_text += f"{result['symbol']}:\n"
        stats_text += (
            f"  {timeframe_name}波动率: {result['period_volatility'] * 100:.4f}%\n"
        )
        stats_text += f"  年化波动率: {result['annual_volatility'] * 100:.2f}%\n"
        stats_text += f"  收益率均值: {result['returns'].mean() * 100:.4f}%\n"
        stats_text += f"  收益率偏度: {result['returns'].skew():.4f}\n"
        stats_text += f"  收益率峰度: {result['returns'].kurtosis():.4f}\n\n"

    plt.text(
        0.05,
        0.95,
        stats_text,
        transform=plt.gca().transAxes,
        verticalalignment="top",
        fontsize=10,
        fontproperties="PingFang HK",
    )
    plt.xlim(0, 1)
    plt.ylim(0, 1)
    plt.axis("off")

    plt.tight_layout(pad=3.0)
    plt.show()


def main():
    """主函数, 分析 BTC 和 ETH 的波动率."""
    print("开始分析 BTC 和 ETH 波动率...")

    # 分析 BTC 和 ETH
    crypto_pairs = ["BTC/USDT", "ETH/USDT"]
    results = []

    for symbol in crypto_pairs:
        try:
            result = analyze_crypto_volatility(symbol, days=3000, timeframe="1d")
            if result:
                results.append(result)
        except Exception as e:
            print(f"分析 {symbol} 时出错: {e}")

    # 比较分析结果
    if len(results) >= 2:
        print(f"\n{'=' * 50}")
        print("综合比较分析")
        print(f"{'=' * 50}")
        compare_volatilities(results)

    print("\n分析完成!")


if __name__ == "__main__":
    main()
