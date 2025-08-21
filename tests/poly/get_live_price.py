import logging
import os
import time

from dotenv import load_dotenv
from py_clob_client.client import ClobClient

# 设置日志记录
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger()

# 从.env文件加载环境变量
load_dotenv()

# 获取环境变量
API_KEY = os.getenv("API_KEY")
host = "https://clob.polymarket.com"
chain_id = 137  # Polygon主网

print(f"Using API key: {API_KEY}")

# 初始化ClobClient客户端
client = ClobClient(host, chain_id=chain_id)

# 用于缓存实时价格的字典
live_price_cache: dict[str, tuple[float, float]] = {}
CACHE_DURATION = 60  # 缓存实时价格1分钟


def get_live_price(token_id):
    """
    获取指定代币ID的实时价格

    Args:
        token_id (str): 需要获取实时价格的代币ID

    Returns:
        float: 指定代币ID的实时价格
    """
    cache_key = f"{token_id}"
    current_time = time.time()

    # 检查缓存中是否有价格数据且仍然有效
    if cache_key in live_price_cache:
        cached_price, timestamp = live_price_cache[cache_key]
        if current_time - timestamp < CACHE_DURATION:
            logger.info(f"Returning cached price for {cache_key}: {cached_price}")
            return cached_price
        else:
            logger.info(f"Cache expired for {cache_key}. Fetching a new price.")

    # 从API获取新价格
    try:
        response = client.get_last_trade_price(token_id=token_id)
        price = response.get("price")

        # 缓存价格和当前时间戳
        live_price_cache[cache_key] = (price, current_time)
        logger.info(f"Fetched live price for {cache_key}: {price}")
        return price
    except Exception as e:
        logger.error(f"Failed to fetch live price for token {token_id}: {e!s}")
        return None


# 如果直接执行此脚本,可以通过命令行参数来测试实时价格获取功能
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python get_live_price.py <token_id>")
        sys.exit(1)

    token_id = sys.argv[1]

    live_price = get_live_price(token_id)
    if live_price is not None:
        print(f"Live price for token {token_id}: {live_price}")
    else:
        print(f"Could not fetch the live price for token {token_id}.")
