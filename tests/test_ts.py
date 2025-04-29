from devtools import pprint
import tushare as ts
from trade.config.settings import settings


def main():
    pprint(settings)

    ts.set_token(settings.tushare_token)
    pro = ts.pro_api()
    df = pro.daily(ts_code="000001.SZ", start_date="20180701", end_date="20180718")

    pprint(df)


if __name__ == "__main__":
    main()
