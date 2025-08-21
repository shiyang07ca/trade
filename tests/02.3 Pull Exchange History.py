import ccxt
import pandas as pd
import os
import time
from datetime import datetime, UTC, timedelta  # Python 3.11+


# ==== 配置区 ====
symbols = ['BTC/USDT', 'ETH/USDT','SOL/USDT', 'DOGE/USDT', 'PEPE/USDT', 'PEOPLE/USDT', 'SHIB/USDT']
# symbols = ['BTC/USDT']
timeframe = '1h'
days = 365 * 2
limit = 1000
max_retries = 5
delay = 0.1

proxies = {
    'http': 'http://127.0.0.1:7890',
    'https': 'http://127.0.0.1:7890',
}

exchange = ccxt.binance({
    'enableRateLimit': True,
    'proxies': proxies,
})

# ==== 工具函数 ====
def get_csv_path(symbol):
    # 修复点1：使用 UTC 时区
    today = datetime.now(UTC).strftime("%Y%m%d")
    # 修复点2：使用 UTC 时区
    start_date = (datetime.now(UTC) - timedelta(days=days)).strftime("%Y%m%d")
    return f"{symbol.lower().replace('/', '_')}_{timeframe}_{start_date}_to_{today}.csv"

def fetch_ohlcv_since(symbol, since):
    for attempt in range(max_retries):
        try:
            data = exchange.fetch_ohlcv(symbol, timeframe=timeframe, since=since, limit=limit)
            return data
        except Exception as e:
            print(f"⚠️ [{symbol}] 第 {attempt+1} 次重试，错误：{e}")
            time.sleep(20)
    print(f"❌ [{symbol}] 多次重试失败，跳过该段。")
    return []

# ==== 主逻辑 ====
# 计算时间范围用于文件名 [2](@ref)
start_date = (datetime.now(UTC) - timedelta(days=days)).strftime("%Y%m%d")
end_date = datetime.now(UTC).strftime("%Y%m%d")

for symbol in symbols:
    print(f"\n📈 开始拉取：{symbol}")
    csv_file = get_csv_path(symbol)  # 使用新文件名格式

    now = exchange.milliseconds()
    since = now - days * 24 * 60 * 60 * 1000

    if os.path.exists(csv_file):
        df = pd.read_csv(csv_file)
        if not df.empty:
            last_time = pd.to_datetime(df['datetime'])
            last_time = last_time.max()
            since = int(pd.Timestamp(last_time).tz_localize("Asia/Shanghai").tz_convert("UTC").timestamp() * 1000) + 60 * 1000
            print(f"🔄 续传模式，从 {last_time}（北京时间） 开始")
        else:
            df = pd.DataFrame()
    else:
        df = pd.DataFrame()

    all_data = []

    while since < now:
        ohlcv = fetch_ohlcv_since(symbol, since)
        if not ohlcv:
            break

        if len(ohlcv) < limit:
            print(f"✅ [{symbol}] 拉完，数据不足 {limit} 条，自动结束")
            break

        since = ohlcv[-1][0] + 60 * 1000
        timestamp_seconds = ohlcv[-1][0] / 1000
        latest_time = datetime.fromtimestamp(timestamp_seconds, tz=UTC).strftime('%Y-%m-%d %H:%M:%S')
        print(f"📥 拉取到{symbol}: {len(ohlcv)} 条，最新时间（UTC）：{latest_time}")

        temp_df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
        temp_df["datetime"] = pd.to_datetime(temp_df["timestamp"], unit="ms")\
                                .dt.tz_localize('UTC')\
                                .dt.tz_convert('Asia/Shanghai')\
                                .dt.strftime('%Y-%m-%d %H:%M:%S')

        temp_df = temp_df[["datetime", "open", "high", "low", "close", "volume"]]  # 移除 timestamp，调整列顺序
        all_data.append(temp_df)

        time.sleep(delay)

    if all_data:
        new_df = pd.concat(all_data)
        full_df = pd.concat([df, new_df]).drop_duplicates("datetime").sort_values("datetime")
        full_df.to_csv(csv_file, index=False)
        print(f"✅ 保存成功：{symbol} -> {csv_file}，共 {len(full_df)} 条记录")
    else:
        print(f"⚠️ 没有新数据：{symbol}")