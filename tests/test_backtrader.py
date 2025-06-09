"""
这个脚本使用 backtrader 框架实现了一个简单的量化交易策略回测系统。
主要包含三个部分：
1. 交易策略的定义 (MyStrategy)
2. 策略回测的单元测试 (TestBacktrader)
3. 测试数据准备和测试执行的主程序入口
"""

import datetime
import unittest

import backtrader as bt


# 定义一个简单的交易策略
class MyStrategy(bt.Strategy):
    """
    一个简单的移动平均线交叉策略
    当价格上穿移动平均线时买入，下穿时卖出
    """

    # 定义策略参数：移动平均线周期为15天
    params = (("maperiod", 15),)

    def log(self, txt, dt=None):
        """
        日志记录函数，用于打印策略运行过程中的信息
        Args:
            txt: 要记录的文本信息
            dt: 日期时间，如果为None则使用当前K线的日期
        """
        dt = dt or self.datas[0].datetime.date(0)
        print(f"{dt.isoformat()} {txt}")

    def __init__(self):
        """
        策略初始化函数，在回测开始前调用
        用于初始化指标、变量等
        """
        # 保存收盘价序列的引用，方便后续访问
        self.dataclose = self.datas[0].close

        # 初始化订单相关变量
        self.order = None  # 当前订单对象
        self.buyprice = None  # 买入价格
        self.buycomm = None  # 买入佣金

        # 创建15日简单移动平均线指标
        self.sma = bt.indicators.SimpleMovingAverage(
            self.datas[0], period=self.params.maperiod
        )

    def notify_order(self, order):
        """
        订单状态更新时的回调函数
        当订单状态发生变化时，Cerebro引擎会调用此方法
        Args:
            order: 订单对象
        """
        if order.status in [order.Submitted, order.Accepted]:
            # 订单已提交或已被接受 - 无需操作
            return

        # 检查订单是否已完成
        # 注意：如果现金不足，经纪商可能会拒绝订单
        if order.status in [order.Completed]:
            if order.isbuy():
                # 买入订单执行完成
                self.log(
                    f"BUY EXECUTED, Price: {order.executed.price:.2f}, Cost: {order.executed.value:.2f}, Comm {order.executed.comm:.2f}"
                )
                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
            else:  # 卖出订单执行完成
                self.log(
                    f"SELL EXECUTED, Price: {order.executed.price:.2f}, Cost: {order.executed.value:.2f}, Comm {order.executed.comm:.2f}"
                )

            # 记录订单执行时的K线位置
            self.bar_executed = len(self)

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            # 订单被取消、保证金不足或被拒绝
            self.log("Order Canceled/Margin/Rejected")

        # 重置订单状态
        self.order = None

    def notify_trade(self, trade):
        """
        交易状态更新时的回调函数
        当一笔交易完成时（买入后卖出，或卖出后买入），Cerebro引擎会调用此方法
        Args:
            trade: 交易对象
        """
        if not trade.isclosed:
            return

        # 记录交易盈亏情况
        self.log(f"OPERATION PROFIT, GROSS {trade.pnl:.2f}, NET {trade.pnlcomm:.2f}")

    def next(self):
        """
        策略的核心逻辑函数
        每个新的K线数据到达时，Cerebro引擎会调用此方法一次
        在这里实现具体的交易逻辑
        """
        # 记录当前K线的收盘价
        self.log(f"Close, {self.dataclose[0]:.2f}")

        # 如果有未完成的订单，不执行新的交易逻辑
        if self.order:
            return

        # 检查当前是否持有仓位
        if not self.position:
            # 没有持仓，检查是否满足买入条件
            if self.dataclose[0] > self.sma[0]:  # 价格上穿移动平均线
                self.log(f"BUY CREATE, {self.dataclose[0]:.2f}")
                self.order = self.buy()  # 发出买入指令
        else:
            # 持有仓位，检查是否满足卖出条件
            if self.dataclose[0] < self.sma[0]:  # 价格下穿移动平均线
                self.log(f"SELL CREATE, {self.dataclose[0]:.2f}")
                self.order = self.sell()  # 发出卖出指令


class TestBacktrader(unittest.TestCase):
    """
    对MyStrategy策略进行回测的单元测试类
    """

    def test_simple_strategy_run(self):
        """
        测试策略的基本运行情况
        包括：策略执行、订单处理、资金计算等
        """
        # 创建Cerebro引擎实例
        cerebro = bt.Cerebro()

        # 添加策略到引擎
        cerebro.addstrategy(MyStrategy)

        # 创建数据源
        # 使用GenericCSVData从CSV文件加载数据
        data = bt.feeds.GenericCSVData(
            dataname="tests/sample_data.csv",  # CSV文件路径
            fromdate=datetime.datetime(2023, 1, 1),  # 回测起始日期
            todate=datetime.datetime(2023, 12, 31),  # 回测结束日期
            dtformat=("%Y-%m-%d"),  # 日期格式
            datetime=0,  # 日期列索引
            high=1,  # 最高价列索引
            low=2,  # 最低价列索引
            open=3,  # 开盘价列索引
            close=4,  # 收盘价列索引
            volume=5,  # 成交量列索引
            openinterest=-1,  # 持仓量列索引（-1表示没有该列）
        )

        # 将数据添加到引擎
        cerebro.adddata(data)

        # 设置初始资金为100,000
        cerebro.broker.setcash(100000.0)

        # 设置每笔交易的固定手数为10
        cerebro.addsizer(bt.sizers.SizerFix, stake=10)

        # 设置交易佣金为0.1%
        cerebro.broker.setcommission(commission=0.001)

        # 记录回测开始前的账户价值
        initial_portfolio_value = cerebro.broker.getvalue()

        # 运行回测
        results = cerebro.run()

        # 记录回测结束后的账户价值
        final_portfolio_value = cerebro.broker.getvalue()

        # 基本断言检查
        self.assertIsNotNone(results, "回测结果不应为空")
        self.assertTrue(len(results) > 0, "应至少有一个策略运行结果")
        # 您可以根据策略逻辑添加更具体的断言
        # 例如，如果策略预期盈利，则 final_portfolio_value > initial_portfolio_value
        # self.assertTrue(final_portfolio_value > initial_portfolio_value, "最终投资组合价值应高于初始值")
        print(f"Initial Portfolio Value: {initial_portfolio_value:.2f}")
        print(f"Final Portfolio Value: {final_portfolio_value:.2f}")


if __name__ == "__main__":
    """
    主程序入口
    当脚本直接运行时，会执行以下操作：
    1. 创建测试用的CSV数据文件
    2. 运行单元测试
    """
    # 创建测试用的CSV数据
    sample_csv_content = """Date,High,Low,Open,Close,Volume
2023-01-02,101.0,99.0,100.0,100.5,1000
2023-01-03,102.5,100.0,100.5,102.0,1200
2023-01-04,103.0,101.0,102.0,101.5,1100
2023-01-05,101.5,99.5,101.5,100.0,1300
2023-01-06,100.5,98.5,100.0,99.0,1050
2023-01-09,100.0,98.0,99.0,99.5,1150
2023-01-10,101.0,99.0,99.5,100.8,1250
2023-01-11,102.0,100.5,100.8,101.5,1000
2023-01-12,101.5,100.0,101.5,100.2,900
2023-01-13,100.8,99.0,100.2,99.8,1400
2023-01-16,100.2,98.5,99.8,100.1,1000
2023-01-17,101.5,100.0,100.1,101.0,1200
2023-01-18,102.0,100.5,101.0,101.8,1100
2023-01-19,102.5,101.0,101.8,102.2,1300
2023-01-20,103.0,101.5,102.2,102.5,1050
2023-01-23,102.8,101.2,102.5,102.0,1150
"""
    # 将测试数据写入CSV文件
    with open("tests/sample_data.csv", "w") as f:
        f.write(sample_csv_content)

    # 运行单元测试
    unittest.main()
