import akshare as ak
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy.stats as stats
import statsmodels.api as sm

from trade.utils import setup_chinese_font

# 初始化matplotlib,使其能够正确显示中文字符,避免乱码问题.
setup_chinese_font()


def fetch_stock_data(symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
    """
    使用 akshare 获取A股历史行情数据.

    Args:
        symbol (str): 股票代码, 例如 '603138'.
        start_date (str): 开始日期, 格式为 'YYYYMMDD'.
        end_date (str): 结束日期, 格式为 'YYYYMMDD'.

    Returns:
        pd.DataFrame: 包含股票历史数据的DataFrame. 如果获取失败则返回空的DataFrame.
    """
    print(f"开始获取股票代码 {symbol} 的历史数据...")
    try:
        stock_zh_a_hist_df = ak.stock_zh_a_hist(
            symbol=symbol,
            period="daily",
            start_date=start_date,
            end_date=end_date,
            # adjust="qfq" 表示前复权, 用于消除分红,配股等事件对股价的影响, 保证价格序列的可比性.
            adjust="qfq",
        )
        if stock_zh_a_hist_df.empty:
            raise ValueError("获取的数据为空, 请检查股票代码和日期范围.")
        print("数据获取成功!")
        # 为了方便后续处理, 将列名 '日期' 和 '收盘' 分别重命名为 'date' 和 'close'.
        stock_zh_a_hist_df.rename(
            columns={"日期": "date", "收盘": "close"}, inplace=True
        )
        # 将日期字符串转换为 datetime 对象, 以便进行时间序列分析.
        stock_zh_a_hist_df["date"] = pd.to_datetime(stock_zh_a_hist_df["date"])
        # 将 'date' 列设置成索引, 这是时间序列处理的标准做法.
        stock_zh_a_hist_df.set_index("date", inplace=True)
        return stock_zh_a_hist_df
    except Exception as e:
        print(f"数据获取失败: {e}")
        return pd.DataFrame()


def calculate_returns(data: pd.DataFrame) -> pd.Series:
    """
    计算日对数收益率.

    对数收益率在金融分析中被广泛使用, 因为它们具有良好的统计特性,
    例如时间可加性(一段时期内的总收益率等于各子时期收益率之和).

    Args:
        data (pd.DataFrame): 包含 'close' 收盘价列的DataFrame.

    Returns:
        pd.Series: 日对数收益率序列.
    """
    print("计算日对数收益率...")
    # 对数收益率计算公式: ln(P_t / P_{t-1}), 其中P_t是当日收盘价, P_{t-1}是前一日收盘价.
    log_returns = np.log(data["close"] / data["close"].shift(1))
    # 由于第一个交易日没有前一日的数据, 计算结果为NaN, 在此将其移除.
    return log_returns.dropna()


def plot_qq_normality_test(returns: pd.Series):
    """
    使用 Q-Q (Quantile-Quantile) 图来检验日收益率是否服从正态分布.

    Q-Q图通过比较样本数据的分位数与理论分布(此处为正态分布)的分位数,
    来判断样本数据是否符合理论分布.

    Args:
        returns (pd.Series): 日对数收益率序列.
    """
    print("生成QQ图以检验收益率的正态性...")
    plt.figure(figsize=(10, 6))
    # 使用statsmodels生成QQ图.
    # line="s" 表示在图上绘制一条标准化的45度参考线.
    # dist=stats.norm 指定理论分布为正态分布.
    sm.qqplot(returns, line="s", dist=stats.norm)
    plt.title("收益率正态分布QQ图")
    plt.xlabel("理论分位数 (正态分布)")
    plt.ylabel("样本分位数")
    plt.grid(True)
    plt.show()
    print("QQ图说明: 如果数据点大致落在红色的45度线上, 说明样本数据符合正态分布.")
    print(
        "观察结果: 许多点, 尤其是在两端(尾部), 偏离了直线, 表明真实收益率分布比正态分布有更厚的尾部(即极端事件发生的概率更高)."
    )


def fit_distributions_and_compare_tails(returns: pd.Series):
    """
    使用 t-分布 和 正态分布 拟合收益率数据, 并比较它们对尾部概率的估计.

    金融资产收益率通常表现出 "尖峰厚尾" (leptokurtosis) 的特性,
    即相比正态分布, 峰值更高更尖, 尾部更厚. t-分布由于其自由度参数,
    能更好地捕捉这种厚尾现象.

    Args:
        returns (pd.Series): 日对数收益率序列.
    """
    print("\n使用t分布和正态分布拟合收益率数据...")

    # 使用最大似然估计法拟合正态分布, 得到均值和标准差.
    norm_params = stats.norm.fit(returns)
    norm_mean, norm_std = norm_params
    print(f"正态分布拟合结果: 平均值 = {norm_mean:.6f}, 标准差 = {norm_std:.6f}")

    # 使用最大似然估计法拟合t分布, 得到自由度(df), 位置(loc)和尺度(scale)参数.
    t_params = stats.t.fit(returns)
    t_df, t_loc, t_scale = t_params
    print(
        f"t分布拟合结果: 自由度 = {t_df:.2f}, 位置 = {t_loc:.6f}, 尺度 = {t_scale:.6f}"
    )

    # 定义一个极端事件的阈值, 这里使用正态分布下的3个标准差作为例子.
    threshold = norm_mean - 3 * norm_std

    # 计算在正态分布下, 收益率低于阈值的累积概率.
    norm_tail_prob = stats.norm.cdf(threshold, loc=norm_mean, scale=norm_std)
    # 计算在t分布下, 收益率低于阈值的累积概率.
    t_tail_prob = stats.t.cdf(threshold, df=t_df, loc=t_loc, scale=t_scale)

    # 计算在实际样本数据中, 收益率低于阈值的经验概率(即实际发生的频率).
    empirical_prob = (returns < threshold).mean()

    print(f"\n比较尾部概率 (收益率 < {threshold:.4f}):")
    print(f"  - 基于正态分布的估计: {norm_tail_prob:.6%}")
    print(f"  - 基于t分布的估计: {t_tail_prob:.6%}")
    print(f"  - 样本中的实际频率 (经验概率): {empirical_prob:.6%}")
    print(
        "比较说明: t分布由于其'厚尾'特性, 通常能更好地捕捉极端市场事件的概率, 其估计值更接近经验概率."
    )

    # 可视化比较
    plt.figure(figsize=(12, 7))
    # 绘制收益率的直方图, density=True 将其标准化为概率密度, 以便与PDF曲线比较.
    plt.hist(returns, bins=100, density=True, alpha=0.6, label="收益率直方图")

    # 生成用于绘制PDF曲线的x轴坐标点.
    xmin, xmax = plt.xlim()
    x = np.linspace(xmin, xmax, 100)

    # 计算并绘制正态分布的概率密度函数(PDF).
    p_norm = stats.norm.pdf(x, norm_mean, norm_std)
    plt.plot(x, p_norm, "k", linewidth=2, label="正态分布拟合")

    # 计算并绘制t分布的概率密度函数(PDF).
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
    (进阶) 基于几何布朗运动(Geometric Brownian Motion, GBM)模型进行蒙特卡洛模拟.

    GBM是金融数学中用于模拟股价路径的经典模型. 它假设股价的连续复利收益率服从一个带有漂移的正态分布.
    此函数通过模拟大量的随机路径, 来预测未来股价的可能分布.

    Args:
        data (pd.DataFrame): 包含 'close' 收盘价列的DataFrame.
        n_simulations (int): 模拟路径的数量.
        n_days (int): 向未来模拟的天数.
    """
    print("\n(进阶) 使用蒙特卡洛模拟生成未来股价路径...")
    # 计算对数收益率, np.log(1 + pct_change) 等价于 np.log(P_t / P_{t-1}).
    log_returns = np.log(1 + data["close"].pct_change()).dropna()

    # 从历史数据中估计模型参数
    # 计算历史对数收益率的均值, 作为模型中的漂移项(drift).
    mu = log_returns.mean()
    # 计算历史对数收益率的标准差, 作为模型中的波动率(volatility).
    sigma = log_returns.std()

    # 获取最新的收盘价作为模拟的起始价格.
    S0 = data["close"].iloc[-1]

    # 设置模拟参数
    dt = 1  # 设定时间步长为1天.

    # 初始化模拟路径矩阵
    simulation_paths = np.zeros((n_days + 1, n_simulations))
    simulation_paths[0] = S0

    # 执行模拟
    for t in range(1, n_days + 1):
        # 生成标准正态分布的随机数, 代表模型中的随机冲击.
        Z = np.random.standard_normal(n_simulations)
        # GBM的离散时间表达式: S(t) = S(t-1) * exp((mu - 0.5 * sigma^2) * dt + sigma * sqrt(dt) * Z).
        # (mu - 0.5 * sigma^2) * dt 是漂移项, 描述了股价的预期增长.
        # sigma * np.sqrt(dt) * Z 是随机项(扩散项), 描述了股价的随机波动.
        simulation_paths[t] = simulation_paths[t - 1] * np.exp(
            (mu - 0.5 * sigma**2) * dt + sigma * np.sqrt(dt) * Z
        )

    # 可视化模拟结果
    plt.figure(figsize=(12, 7))
    plt.plot(simulation_paths)
    plt.title(f"几何布朗运动蒙特卡洛模拟 ({n_simulations}条路径)")
    plt.xlabel("未来交易日数 (天)")
    plt.ylabel("模拟股价")
    plt.grid(True)
    # 绘制起始价格参考线.
    plt.axhline(y=S0, color="r", linestyle="--", label=f"起始价格: {S0:.2f}")
    plt.legend()
    plt.show()
    print("蒙特卡洛模拟说明: 该图展示了基于历史波动率和收益率的多种可能的未来股价路径.")
    print("这对于评估投资组合的未来风险.期权定价等场景非常有用.")


def main():
    """主函数, 用于按顺序执行整个分析流程."""
    # --- 步骤 1: 获取并处理股票数据 ---
    stock_symbol = "603138"  # 以 海量数据 为例.
    start_date = "20200101"
    end_date = "20250501"
    stock_data = fetch_stock_data(stock_symbol, start_date, end_date)

    if stock_data.empty:
        print("没有获取到数据, 程序终止.")
        return

    # --- 步骤 2: 计算对数收益率 ---
    log_returns = calculate_returns(stock_data)

    # --- 步骤 3: 使用QQ图检验收益率的正态性 ---
    plot_qq_normality_test(log_returns)

    # --- 步骤 4: 拟合t分布和正态分布并比较尾部风险 ---
    fit_distributions_and_compare_tails(log_returns)

    # --- 步骤 5: (进阶) 使用蒙特卡洛方法模拟未来股价路径 ---
    monte_carlo_gbm(stock_data, n_simulations=100, n_days=252)


if __name__ == "__main__":
    main()
