"""调试Polymarket API响应结构"""

import json

import requests

# 测试API响应结构
config = {"api_base_url": "https://clob.polymarket.com", "timeout": 10}

session = requests.Session()
session.headers.update({"Accept": "application/json"})

try:
    print("测试API响应结构...")

    # 测试市场列表API
    url = f"{config['api_base_url']}/markets"
    params = {"limit": 3, "active": "true"}

    response = session.get(url, params=params, timeout=config["timeout"])
    print(f"响应状态码: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print("响应数据结构:")
        print(json.dumps(data, indent=2, ensure_ascii=False)[:1000] + "...")

        if "data" in data and data["data"]:
            first_market = data["data"][0]
            print("\n第一个市场的字段:")
            for key in first_market.keys():
                print(f"  {key}: {type(first_market[key])}")
    else:
        print(f"API请求失败: {response.text}")

except Exception as e:
    print(f"错误: {e}")
