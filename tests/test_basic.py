"""
本脚本用于下载A股指定股票的历史数据，并进行详细的量化分析。
主要分析内容包括：
1. 计算日对数收益率。
2. 计算收益率的核心统计指标（均值、年化波动率、偏度、峰度）。
3. 绘制收益率的直方图，并与正态分布曲线进行对比，以观察金融时间序列数据常见的"尖峰厚尾"特征。
4. 计算在95%置信水平下的单日风险价值（Value at Risk, VaR）。

使用前请确保已安装所需库:
pip install akshare pandas numpy matplotlib scipy
"""

import akshare as ak
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import norm

from trade.utils import setup_chinese_font

# 设置中文字体
setup_chinese_font()


# 设置中文显示的全局字体大小
plt.rcParams["font.size"] = 12


print(f"最终字体设置: {plt.rcParams['font.sans-serif']}")


def analyze_stock_returns(stock_code: str, stock_name: str):
    """
    下载并分析指定A股股票的日收益率。

    :param stock_code: 股票代码, 例如 '603138'
    :param stock_name: 股票名称, 例如 '海量数据'
    """
    try:
        # --- 1. 下载股票历史数据 ---
        # 使用 akshare 的 stock_zh_a_hist 接口获取A股的日线历史数据。
        # symbol: 股票代码
        # period: 数据周期，"daily" 表示日线
        # adjust: 复权类型，"qfq" 表示前复权，可以消除分红、配股等对股价的影响，更真实地反映股价走势。
        print(f"正在下载 {stock_name}({stock_code}) 的历史数据...")
        stock_hist_df = ak.stock_zh_a_hist(
            symbol=stock_code, period="daily", adjust="qfq"
        )

        if stock_hist_df.empty:
            print(f"未能获取到股票 {stock_code} 的数据，请检查代码或网络连接。")
            return

        print("数据下载完成，开始进行分析...")
        # 将'日期'列转换为datetime对象，并设为索引，便于时间序列分析
        stock_hist_df["日期"] = pd.to_datetime(stock_hist_df["日期"])
        stock_hist_df.set_index("日期", inplace=True)

        # --- 2. 计算日对数收益率 ---
        # 对数收益率公式: ln(t_day_close / (t-1)_day_close)
        # 相比简单收益率，对数收益率具有时间可加性，在金融分析中更常用。
        stock_hist_df["log_return"] = np.log(
            stock_hist_df["收盘"] / stock_hist_df["收盘"].shift(1)
        )

        # 删除计算收益率后产生的第一个NaN值
        returns = stock_hist_df["log_return"].dropna()

        # --- 3. 计算关键统计指标 ---
        # 均值: 反映收益率的平均水平
        mean_return = returns.mean()
        # 年化波动率: 衡量收益率的波动风险。日标准差 * sqrt(252)，因为A股一年大约有252个交易日。
        annualized_volatility = returns.std() * np.sqrt(252)
        # 偏度: 衡量收益率分布的对称性。正偏态表示右侧尾部更长，负偏态表示左侧尾部更长。
        skewness = returns.skew()
        # 峰度: 衡量收益率分布的尖峭程度。"尖峰厚尾" (Leptokurtic) 是指峰度大于3（或超额峰度大于0）的分布。
        kurtosis = (
            returns.kurtosis()
        )  # Pandas计算的是超额峰度 (Excess Kurtosis)，正态分布的峰度为0。

        print("\n--- 收益率分析指标 ---")
        print(f"日对数收益率均值: {mean_return:.6f}")
        print(f"年化波动率: {annualized_volatility:.4f}")
        print(f"偏度 (Skewness): {skewness:.4f}")
        print(f"峰度 (Kurtosis): {kurtosis:.4f}")

        # --- 4. 计算95%分位数的单日VaR ---
        # VaR (Value at Risk) - 在险价值，是衡量金融风险的常用指标。
        # 95%置信水平下的VaR，意味着在正常的市场波动下，有95%的把握，未来一个交易日的损失不会超过这个数值。
        # 这通常通过计算收益率分布的5%分位数得到。
        var_95 = returns.quantile(0.05)
        print(f"95% 置信水平单日 VaR: {var_95:.4f}")
        print(f"这意味着，我们有95%的信心认为明天的亏损不会超过 {-var_95 * 100:.2f}%.")

        # --- 5. 绘制收益率直方图与正态分布曲线 ---
        plt.figure(figsize=(14, 7))
        # 绘制直方图。bins是柱子的数量，density=True将其标准化为概率密度。
        returns.hist(bins=100, density=True, alpha=0.6, color="b", label="日对数收益率")

        # 拟合正态分布曲线，用于对比
        mu, std = returns.mean(), returns.std()
        # 生成x轴上的点
        x = np.linspace(returns.min(), returns.max(), 200)
        # 计算对应x点的正态分布概率密度
        p = norm.pdf(x, mu, std)
        plt.plot(x, p, "r-", linewidth=2, label="正态分布曲线")

        plt.title(f"{stock_name}({stock_code}) 日对数收益率分布图", fontsize=16)
        plt.xlabel("日对数收益率", fontsize=12)
        plt.ylabel("概率密度", fontsize=12)
        plt.legend()
        plt.grid(True)

        # 在图表中添加统计指标的文本框，方便查看
        text_str = (
            f"均值: {mean_return:.4f}\n"
            f"标准差: {std:.4f}\n"
            f"偏度: {skewness:.4f}\n"
            f"峰度: {kurtosis:.4f}\n\n"
            f"观察: 相比正态分布（红线），\n"
            f"实际收益率（蓝柱）呈现出\n"
            f"更尖的峰值和更厚的尾部（特别是左尾），\n"
            f"这是典型的'尖峰厚尾'现象。"
        )
        # 使用transAxes坐标系，(0,0)是左下角, (1,1)是右上角
        plt.text(
            0.02,
            0.98,
            text_str,
            transform=plt.gca().transAxes,
            fontsize=10,
            verticalalignment="top",
            bbox=dict(boxstyle="round,pad=0.5", fc="wheat", alpha=0.7),
        )

        print("\n正在生成收益率分布图...")
        plt.show()
        print("分析完成。")

    except Exception as e:
        print(f"处理过程中发生错误: {e}")


if __name__ == "__main__":
    # 设置要分析的股票信息
    # stock_code_hailiang = "603138"
    # stock_name_hailiang = "海量数据"
    # analyze_stock_returns(stock_code_hailiang, stock_name_hailiang)

    stock_code_hailiang = "601319"
    stock_name_hailiang = "中国人保"
    analyze_stock_returns(stock_code_hailiang, stock_name_hailiang)
