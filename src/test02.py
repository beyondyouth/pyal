'''
@Author: dong.zhili
@Date: 1970-01-01 08:00:00
@LastEditors  : dong.zhili
@LastEditTime : 2020-01-17 18:48:52
@Description: 
'''
import time
import requests
from dateutil.relativedelta import relativedelta
import datetime
import json
import pandas as pd
import requests

def get_hist(code, start, end, timeout = 10,
                    retry_count=3, pause=0.001):
    '''
    code 股票代码
    '''
    def _code_to_symbol(code):
        '''
            生成 symbol 代码标志
        '''
        if len(code) != 6 :
            return code
        else:
            return 'sh%s'%code if code[:1] in ['5', '6', '9'] or code[:2] in ['11', '13'] else 'sz%s'%code
    code = _code_to_symbol(code)
    url = "http://api.finance.ifeng.com/akdaily/?code=%s&type=last" % code
    
    for _ in range(retry_count):
        time.sleep(pause)
        try:
            text = requests.get(url, timeout=timeout).text
            if len(text) < 15: #no data
                return None
        except Exception as e:
            print(e)
        else:
            js = json.loads(text)
            cols = ['date', 'open', 'high', 'close', 'low', 'volume',
                        'price_change', 'p_change', 'ma5', 'ma10', 'ma20', 'v_ma5', 'v_ma10', 'v_ma20']
            df = pd.DataFrame(js['record'], columns=cols)
            df = df.applymap(lambda x: x.replace(u',', u''))
            df[df==''] = 0
            for col in cols[1:]:
                df[col] = df[col].astype(float)
            if start is not None:
                df = df[df.date >= start]
            if end is not None:
                df = df[df.date <= end]
            df = df.set_index('date')
            df = df.sort_index()
            df = df.reset_index(drop=False)
            return df
    raise IOError('获取失败 请检查网络')

def create_dataframe2(code):
    today = datetime.datetime.now() # .strftime("%Y%m%d")
    two_month_ago = today - relativedelta(months=2)
    df = get_hist(code, two_month_ago.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d"))
    
    df2 = pd.DataFrame({'Date' : df['date'], 'Open' : df['open'],
                        'High' : df['high'], 'Low' : df['low'],
                        'Close' : df['close'],'Volume' : df['volume'],
                        'Adj Close':df['close']})
    
    param = {"Referer": "https://finance.sina.com.cn"}
    resp = requests.get("https://hq.sinajs.cn/list=sz%s,s_sz%s" % (code, code), headers=param)
    data = resp.content.decode(encoding='gb2312')
    
    lines = data.splitlines()
    list1 = lines[0].split("\"")[1].split(',')
    list2 = lines[1].split("\"")[1].split(',')
    # print(list1)
    # print(list2)
    date = list1[30]
    open = list1[1]
    high = list1[4]
    low = list1[5]
    close = list1[3]
    volume = list2[4]
    new=pd.DataFrame({'Date':date,
                  'Open':round(float(open),2),
                  'High':round(float(high),2),
                  'Low':round(float(low),2),
                  'Close':round(float(close),2),
                  'Volume':round(float(volume),1),
                  'Adj Close':round(float(close),2)},index=[1])
    
    if new.iat[0, 0] != df2.iat[-1, 0]:
        df2 = pd.concat([df2,new], axis=0 ,ignore_index=True)
    return list1[0], df2

def strategy(code: str, name: str, df: pd.DataFrame, lastday=10):
    print(code, name)
    date_index = df['Date']
    sma_df = pd.DataFrame({'Date':df['Date'], 'sma21':df['Close'].rolling(21).mean(), 'sma23':df['Close'].rolling(23).mean(), 'close': df['Close'], 'max20': df['Close'].rolling(23).max()}).tail(lastday+2)
    sma_df['sma21diff'] = sma_df['sma21'].diff()
    sma_df['sma23diff'] = sma_df['sma23'].diff()
    # print(sma_df)
    buy_flag_count = 0
    sell_flag_count = 0
    cur_flag = ""

    for i in range(2, sma_df.shape[0]):
        # self.__sma23[-1] > self.__sma23[-2] > self.__sma23[-3] and self.__sma23[-1] - self.__sma23[-2] > self.__sma23[-2] - self.__sma23[-3] and bar.getClose() >= self.__maxN[-1]:
        date = sma_df.iloc[i, 0]
        cur_sma21 = sma_df.iloc[i, 1]
        pre_sma21 = sma_df.iloc[i-1, 1]
        pre_pre_sma21 = sma_df.iloc[i-2, 1]
        close = sma_df.iloc[i, 3]
        max20 = sma_df.iloc[i-1, 4] # 去上一行的max20值，用于与过去20天的最大值比较

        cur_sma23 = sma_df.iloc[i, 2]
        pre_sma23 = sma_df.iloc[i-1, 2]
        pre_pre_sma23 = sma_df.iloc[i-2, 2]

        if i == sma_df.shape[0] - 1:
            cur_flag = "-> "

        if cur_sma23 > pre_sma23 > pre_pre_sma23 and cur_sma23 - pre_sma23 > pre_sma23 - pre_pre_sma23 and close > max20:
            buy_flag_count += 1
            print(cur_flag + "Buy at %s %s %d" % (date, close, buy_flag_count))
            continue
        if cur_sma21 < pre_sma21 < pre_pre_sma21 and pre_sma21 - cur_sma21 > pre_pre_sma21 - pre_sma21:
            sell_flag_count += 1
            print(cur_flag + "Sell at %s %s %d" % (date, close, sell_flag_count))
            continue
        buy_flag_count = 0
        sell_flag_count = 0
'''
def strategy2(code: str, name: str, df: pd.DataFrame, lastday=10):
    print(code, name)
    date_index = df['Date']
    sma_df = pd.DataFrame({'Date':df['Date'], 'sma21':df['Close'].rolling(21).mean(), 'sma23':df['Close'].rolling(23).mean(), 'close': df['Close'], 'max20': df['Close'].rolling(23).max()}).tail(lastday+2)
    sma_df['sma21diff'] = sma_df['sma21'].diff()
    sma_df['sma23diff'] = sma_df['sma23'].diff()
    # print(sma_df)
    buy_flag_count = 0
    sell_flag_count = 0
    cur_flag = ""

    for i in range(2, sma_df.shape[0]):
        # self.__sma23[-1] > self.__sma23[-2] > self.__sma23[-3] and self.__sma23[-1] - self.__sma23[-2] > self.__sma23[-2] - self.__sma23[-3] and bar.getClose() >= self.__maxN[-1]:
        date_list = sma_df['Date']
        date = date_list[i-1]

        close_list = sma_df['close']
        close = close_list[i-1]

        max20_list = sma_df['max20']
        max20 = max20_list[i-1]

        sma21_list = sma_df['sma21']
        sma23_list = sma_df['sma23']

        sma21diff_list = sma_df['sma21diff']
        sma23diff_list = sma_df['sma23diff']

        if i == sma_df.shape[0] - 1:
            cur_flag = "-> "

        if sma23_list[i] > pre_sma23 > pre_pre_sma23 and cur_sma23 - pre_sma23 > pre_sma23 - pre_pre_sma23 and close > max20:
            buy_flag_count += 1
            print(cur_flag + "Buy at %s %s %d" % (date, close, buy_flag_count))
            continue
        if cur_sma21 < pre_sma21 < pre_pre_sma21 and pre_sma21 - cur_sma21 > pre_pre_sma21 - pre_sma21:
            sell_flag_count += 1
            print(cur_flag + "Sell at %s %s %d" % (date, close, sell_flag_count))
            continue
        buy_flag_count = 0
        sell_flag_count = 0
'''

if __name__ == "__main__":
    arr_code = ["399006", "399300", "399363", "399997", "399933", "399417", "399935", "399989"]
    for code in arr_code:
        try:
            name, df = create_dataframe2(code)
            if name == None:
                continue
            strategy(code, name, df, 10)
        except Exception as e:
            print("error happend", e)
