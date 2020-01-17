# curl 'https://finance.pae.baidu.com/selfselect/getstockquotation?code=IXIC&all=1&ktype=1&isIndex=true&isBk=false&isBlock=false&stockType=us&market_type=us&group=quotation_index_kline'

# curl 'https://finance.pae.baidu.com/selfselect/getstockquotation?code=399006&all=1&ktype=1&isIndex=true&isBk=false&isBlock=false&stockType=ab&market_type=ab&group=quotation_index_kline'

# curl 'https://finance.pae.baidu.com/selfselect/getstockquotation?code=000016&all=1&ktype=1&isIndex=true&isBk=false&isBlock=false&stockType=ab&market_type=ab&group=quotation_index_kline
import datetime
import json
import sys
from typing import Tuple
import pandas as pd
import requests
from dateutil.relativedelta import relativedelta


FORECAST = 1
REGRESSION = 2
mode = FORECAST

class bcolors:
    SELL = '\033[32m'
    BUY = '\033[31m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def get_real_time_dataframe(code) -> Tuple[str, pd.DataFrame]:
    def _code_to_symbol(code) -> str:
        '''
            生成 symbol 代码标志
        '''
        if len(code) != 6 :
            return code
        else:
            return 'sh%s'%code if code[:1] in ['5', '6', '9'] or code[:2] in ['11', '13'] else 'sz%s'%code
    code = _code_to_symbol(code)
    # print(code)
    param = {"Referer": "https://finance.sina.com.cn"}
    resp = requests.get("https://hq.sinajs.cn/list=%s" % code, headers=param)
    data = resp.content.decode(encoding='gb2312')
    
    lines = data.splitlines()
    list1 = lines[0].split("\"")[1].split(',')
    # print(list1)
    name = list1[0]
    date = list1[30].replace(u'-', u'')
    open = round(float(list1[1]),2)
    high = round(float(list1[4]),2)
    low = round(float(list1[5]),2)
    close = round(float(list1[3]),2)
    volume = round(float(list1[9]),1)
    amount = float(list1[8]) // 100
    new=pd.DataFrame({'date': date,
                    'close': close,
                  'open': open,
                  'high': high,
                  'low': low,
                  'volume': volume,
                  'amount': amount}, index=[1])
    
    # if new.iat[0, 0] != df2.iat[-1, 0]:
    # df2 = pd.concat([df,new], axis=0 ,ignore_index=True)
    # return list1[0], df2
    return name, new

def get_hist_dataframe(code: str, start=datetime.datetime.now()-relativedelta(months=2), end=None) -> pd.DataFrame:
    st = 'ab'
    if code in ['IXIC', 'SPX', 'DJI']:
        st = 'us'
    elif code in ['HSI']:
        st = 'hk'
    url = 'https://finance.pae.baidu.com/selfselect/getstockquotation?code=%s&all=1&ktype=1&isIndex=true&isBk=false&isBlock=false&stockType=%s&market_type=%s&group=quotation_index_kline' % (code, st, st)
    try:
        text = requests.get(url, timeout=10).text
    except Exception as e:
            print(e)
    else:
        # print(text)
        js = json.loads(text)
        if js['ResultCode'] != '0':
            raise Exception
        res = js['Result']
        for item in res:
            item['close'] = item['kline']['close']
            item['open'] = item['kline']['open']
            item['high'] = item['kline']['high']
            item['low'] = item['kline']['low']
            item['volume'] = item['kline']['volume']
            item['amount'] = item['kline']['amount']
        cols = ['date', 'close', 'open', 'high', 'low', 'volume', 'amount']
        df = pd.DataFrame(res, columns=cols)
        # df = df.applymap(lambda x: x.replace(u',', u''))
        df[df==''] = 0
        for col in cols[1:]:
            df[col] = df[col].astype(float)
        if start is not None:
            df = df[df.date >= start.strftime("%Y%m%d")]
        if end is not None:
            df = df[df.date <= end.strftime("%Y%m%d")]
        df = df.set_index('date')
        df = df.sort_index()
        df = df.reset_index(drop=False)
        # print(df)
    return df

def create_dataframe2(code) -> Tuple[str, pd.DataFrame]:
    try:
        df_res = get_hist_dataframe(code)
    except Exception as e:
        return None, None
    if len(code) != 6:
        return None, df_res
    try:
        name, df_real_time = get_real_time_dataframe(code)
    except Exception as e:
        print("Error on line %d" % sys._getframe().f_lineno, e)
        return code, None
    else:
        # 如果历史数据中已经含有今天的数据则不合并实时数据
        if df_real_time.iat[0, 0] != df_res.iat[-1, 0]:
            df_res = pd.concat([df_res, df_real_time], axis=0 ,ignore_index=True)
    # print(name)
    # print(df_res)
    return name, df_res

def strategy(code: str, name: str, df: pd.DataFrame, lastday=10):
    print(code, name)
    date_index = df['date']
    sma_df = pd.DataFrame({'Date':df['date'],
                        'sma21':df['close'].rolling(21).mean(),
                        'sma23':df['close'].rolling(23).mean(),
                        'close': df['close'],
                        'max20': df['close'].rolling(23).max()}).tail(lastday+2)
    sma_df['sma21diff'] = sma_df['sma21'].diff()
    sma_df['sma23diff'] = sma_df['sma23'].diff()
    # print(sma_df)
    buy_flag_count = 0
    sell_flag_count = 0
    cur_flag = ""

    for i in range(2, sma_df.shape[0]):
        date = sma_df.iloc[i, 0]
        cur_sma21 = sma_df.iloc[i, 1]
        pre_sma21 = sma_df.iloc[i-1, 1]
        pre_pre_sma21 = sma_df.iloc[i-2, 1]
        close = sma_df.iloc[i, 3]
        max20 = sma_df.iloc[i-1, 4] # 去上一行的max20值，用于与过去20天的最大值比较

        cur_sma23 = sma_df.iloc[i, 2]
        pre_sma23 = sma_df.iloc[i-1, 2]
        pre_pre_sma23 = sma_df.iloc[i-2, 2]

        if date == datetime.datetime.now().strftime("%Y%m%d"):
            cur_flag = "-> "

        if cur_sma23 > pre_sma23 > pre_pre_sma23 and cur_sma23 - pre_sma23 > pre_sma23 - pre_pre_sma23 and close > max20:
            buy_flag_count += 1
            if cur_flag == "-> ":
                print(bcolors.BUY + cur_flag + "Buy at %s %s %d" % (date, close, buy_flag_count) + bcolors.ENDC)
            else:
                print("Buy at %s %s %d" % (date, close, buy_flag_count))
            continue
        if cur_sma21 < pre_sma21 < pre_pre_sma21 and pre_sma21 - cur_sma21 > pre_pre_sma21 - pre_sma21:
            sell_flag_count += 1
            if cur_flag == "-> ":
                print(bcolors.SELL + cur_flag + "Sell at %s %s %d" % (date, close, sell_flag_count) + bcolors.ENDC)
            else:
                print("Sell at %s %s %d" % (date, close, sell_flag_count))
            continue
        buy_flag_count = 0
        sell_flag_count = 0

if __name__ == "__main__":
    mode = FORECAST
    arr_code = ["SPX", "DJI", "IXIC", "399006", "399300", "399363", "399997", "399933", "399417", "399989"]
    for code in arr_code:
        name, df = create_dataframe2(code)
        if df is None:
            continue
        strategy(code, name, df, 10)
