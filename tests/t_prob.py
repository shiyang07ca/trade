import akshare as ak
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy.stats as stats
import statsmodels.api as sm

from trade.utils import setup_chinese_font

# 设置中文字体
setup_chinese_font()


def fetch_stock_data(symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
    """
    Fetch historical stock data using akshare.

    Args:
        symbol (str): Stock symbol, e.g., '603138'.
        start_date (str): Start date in 'YYYYMMDD' format.
        end_date (str): End date in 'YYYYMMDD' format.

    Returns:
        pd.DataFrame: DataFrame with historical stock data.
    """
    print(f"开始获取股票代码 {symbol} 的历史数据...")
    try:
        stock_zh_a_hist_df = ak.stock_zh_a_hist(
            symbol=symbol,
            period="daily",
            start_date=start_date,
            end_date=end_date,
            adjust="qfq",
        )
        if stock_zh_a_hist_df.empty:
            raise ValueError("获取的数据为空, 请检查股票代码和日期范围。")
        print("数据获取成功！")
        # Rename columns for clarity, especially the date column.
        stock_zh_a_hist_df.rename(
            columns={"日期": "date", "收盘": "close"}, inplace=True
        )
        stock_zh_a_hist_df["date"] = pd.to_datetime(stock_zh_a_hist_df["date"])
        stock_zh_a_hist_df.set_index("date", inplace=True)
        return stock_zh_a_hist_df
    except Exception as e:
        print(f"数据获取失败: {e}")
        return pd.DataFrame()


def calculate_returns(data: pd.DataFrame) -> pd.Series:
    """
    Calculate daily logarithmic returns.

    Args:
        data (pd.DataFrame): DataFrame with a 'close' price column.

    Returns:
        pd.Series: A series of daily log returns.
    """
    print("计算日对数收益率...")
    log_returns = np.log(data["close"] / data["close"].shift(1))
    return log_returns.dropna()  # Remove the first NaN value


def plot_qq_normality_test(returns: pd.Series):
    """
    Use a Q-Q plot to test if daily returns follow a normal distribution.

    Args:
        returns (pd.Series): A series of daily log returns.
    """
    print("生成QQ图以检验收益率的正态性...")
    plt.figure(figsize=(10, 6))
    sm.qqplot(returns, line="s", dist=stats.norm)
    plt.title("收益率正态分布QQ图")
    plt.xlabel("理论分位数 (正态分布)")
    plt.ylabel("样本分位数")
    plt.grid(True)
    plt.show()
    print("QQ图说明：如果数据点大致落在红色的45度线上，说明样本数据符合正态分布。")
    print(
        "观察结果：许多点，尤其是在两端（尾部），偏离了直线，表明真实收益率分布比正态分布有更厚的尾部（即极端事件发生的概率更高）。"
    )


def fit_distributions_and_compare_tails(returns: pd.Series):
    """
    Fit t-distribution and normal distribution to the returns data and
    compare their estimates of tail probabilities.

    Args:
        returns (pd.Series): A series of daily log returns.
    """
    print("\n使用t分布和正态分布拟合收益率数据...")

    # Fit a normal distribution
    norm_params = stats.norm.fit(returns)
    norm_mean, norm_std = norm_params
    print(f"正态分布拟合结果: 平均值 = {norm_mean:.6f}, 标准差 = {norm_std:.6f}")

    # Fit a t-distribution
    t_params = stats.t.fit(returns)
    t_df, t_loc, t_scale = t_params
    print(
        f"t分布拟合结果: 自由度 = {t_df:.2f}, 位置 = {t_loc:.6f}, 尺度 = {t_scale:.6f}"
    )

    # Compare tail probabilities
    # We define an extreme event as a return below a certain threshold,
    # for example, 3 standard deviations of the normal fit.
    threshold = norm_mean - 3 * norm_std

    # Calculate probability from the fitted distributions
    norm_tail_prob = stats.norm.cdf(threshold, loc=norm_mean, scale=norm_std)
    t_tail_prob = stats.t.cdf(threshold, df=t_df, loc=t_loc, scale=t_scale)

    # Calculate empirical probability
    empirical_prob = (returns < threshold).mean()

    print(f"\n比较尾部概率 (收益率 < {threshold:.4f}):")
    print(f"  - 基于正态分布的估计: {norm_tail_prob:.6%}")
    print(f"  - 基于t分布的估计: {t_tail_prob:.6%}")
    print(f"  - 样本中的实际频率 (经验概率): {empirical_prob:.6%}")
    print(
        "比较说明：t分布由于其'厚尾'特性，通常能更好地捕捉极端市场事件的概率，其估计值更接近经验概率。"
    )

    # Plot the PDFs of the fitted distributions against the histogram of the returns
    plt.figure(figsize=(12, 7))
    plt.hist(returns, bins=100, density=True, alpha=0.6, label="收益率直方图")

    # Generate x-axis values for the PDF plots
    xmin, xmax = plt.xlim()
    x = np.linspace(xmin, xmax, 100)

    # Plot Normal PDF
    p_norm = stats.norm.pdf(x, norm_mean, norm_std)
    plt.plot(x, p_norm, "k", linewidth=2, label="正态分布拟合")

    # Plot t-distribution PDF
    p_t = stats.t.pdf(x, t_df, t_loc, t_scale)
    plt.plot(x, p_t, "r--", linewidth=2, label="t分布拟合")

    plt.title("收益率分布与拟合")
    plt.xlabel("日对数收益率")
    plt.ylabel("概率密度")
    plt.legend()
    plt.grid(True)
    plt.show()


def monte_carlo_gbm(data: pd.DataFrame, n_simulations: int = 100, n_days: int = 252):
    """
    (Advanced) Perform Monte Carlo simulation based on Geometric Brownian Motion.

    Args:
        data (pd.DataFrame): DataFrame with a 'close' price column.
        n_simulations (int): Number of simulation paths.
        n_days (int): Number of future days to simulate.
    """
    print("\n(进阶) 使用蒙特卡洛模拟生成未来股价路径...")
    log_returns = np.log(1 + data["close"].pct_change()).dropna()

    # Calculate drift and volatility
    mu = log_returns.mean()
    sigma = log_returns.std()

    # Last closing price
    S0 = data["close"].iloc[-1]

    dt = 1  # Daily simulation

    # Generate random paths
    simulation_paths = np.zeros((n_days + 1, n_simulations))
    simulation_paths[0] = S0

    for t in range(1, n_days + 1):
        # Z is a random number from a standard normal distribution
        Z = np.random.standard_normal(n_simulations)
        # Geometric Brownian Motion formula
        # S(t) = S(t-1) * exp((mu - 0.5 * sigma^2) * dt + sigma * sqrt(dt) * Z)
        simulation_paths[t] = simulation_paths[t - 1] * np.exp(
            (mu - 0.5 * sigma**2) * dt + sigma * np.sqrt(dt) * Z
        )

    plt.figure(figsize=(12, 7))
    plt.plot(simulation_paths)
    plt.title(f"几何布朗运动蒙特卡洛模拟 ({n_simulations}条路径)")
    plt.xlabel("未来交易日数 (天)")
    plt.ylabel("模拟股价")
    plt.grid(True)
    # Add a line for the starting price for reference
    plt.axhline(y=S0, color="r", linestyle="--", label=f"起始价格: {S0:.2f}")
    plt.legend()
    plt.show()
    print(
        "蒙特卡洛模拟说明：该图展示了基于历史波动率和收益率的多种可能的未来股价路径。"
    )
    print("这对于评估投资组合的未来风险、期权定价等场景非常有用。")


def main():
    """Main function to run the analysis."""
    # --- 1. 获取数据 ---
    stock_symbol = "603138"  # 海量数据
    start_date = "20200101"
    end_date = "20240101"
    stock_data = fetch_stock_data(stock_symbol, start_date, end_date)

    if stock_data.empty:
        return

    # --- 2. 计算收益率 ---
    log_returns = calculate_returns(stock_data)

    # --- 3. QQ图检验正态性 ---
    plot_qq_normality_test(log_returns)

    # --- 4. t分布拟合与比较 ---
    fit_distributions_and_compare_tails(log_returns)

    # --- 5. (进阶) 蒙特卡洛模拟 ---
    monte_carlo_gbm(stock_data, n_simulations=100, n_days=252)


if __name__ == "__main__":
    main()
