import requests
import time
import json
import pandas as pd

def create_dataframe(code: str):
    resp = requests.get("http://fund.eastmoney.com/pingzhongdata/%s.js?v=%s" % (code, time.strftime('%Y%m%d%H%M%S', time.localtime())))
    data = resp.content.decode()
    name_start = data.find('fS_name = ')
    name_end = data.find(';', name_start)
    name = data[name_start+len('fS_name = '):name_end]

    start = data.find('Data_netWorthTrend')
    start = data.find('[', start)
    end = data.find(';', start)
    # print(data[start:end])
    arr = json.loads(data[start:end]) # d list
    for dic in arr:
        timeStamp = dic['x'] / 1000
        timeArray = time.localtime(timeStamp)
        date = time.strftime("%Y-%m-%d", timeArray)
        dic['x'] = date
        dic.pop('equityReturn')
        dic.pop('unitMoney')

    resp = requests.get("http://fundgz.1234567.com.cn/js/%s.js?rt=%s" % (code, time.strftime('%Y%m%d%H%M%S', time.localtime())))
    data = resp.content.decode()
    start = data.find('{')
    if start != -1:
        end = data.rfind('}')+1
        dic = json.loads(data[start:end]) # d list
        # print(dic)
        new = dict()
        # new['x'] = dic['jzrq']
        new['x'] = time.strftime('%Y-%m-%d', time.localtime())
        new['y'] = dic['gsz']
        if arr[-1]['x'] != new['x']:
            arr.append(new)

    date_list = list()
    close_list = list()
    open_list = list()
    for item in arr:
        date_list.append(item['x'])
        if len(close_list) == 0:
            open_list.append(0.0)
        else:
            open_list.append(close_list[-1])
        close_list.append(item['y'])
        

    merge_dict = {'Date':date_list,
                'Open': close_list,
                'High': close_list,
                'Low': close_list,
                'Close': close_list,
                'Volume': close_list,
                'Adj Close': close_list}

    df = pd.DataFrame(merge_dict)
    # print(df)
    # print(dic)
    df.to_csv(code+".csv", index=False)
    return name, df

def strategy(code: str, name: str, df: pd.DataFrame, lastday=10):
    print(code, name)
    date_index = df['Date']
    sma_df = pd.DataFrame({'Date':df['Date'], 'sma21':df['Close'].rolling(21).mean(), 'sma23':df['Close'].rolling(23).mean(), 'close': df['Close'], 'max20': df['Close'].rolling(23).max()}).tail(lastday+2)
    # print(sma_df)
    buy_flag_count = 0
    sell_flag_count = 0
    cur_flag = ""

    # share = 0.0
    # lirun = 0.0

    for i in range(2, sma_df.shape[0]):
        # self.__sma23[-1] > self.__sma23[-2] > self.__sma23[-3] and self.__sma23[-1] - self.__sma23[-2] > self.__sma23[-2] - self.__sma23[-3] and bar.getClose() >= self.__maxN[-1]:
        date = sma_df.iloc[i, 0]
        cur_sma21 = sma_df.iloc[i, 1]
        pre_sma21 = sma_df.iloc[i-1, 1]
        pre_pre_sma21 = sma_df.iloc[i-2, 1]
        close = sma_df.iloc[i, 3]
        max20 = sma_df.iloc[i-1, 4]

        cur_sma23 = sma_df.iloc[i, 2]
        pre_sma23 = sma_df.iloc[i-1, 2]
        pre_pre_sma23 = sma_df.iloc[i-2, 2]

        if i == sma_df.shape[0] - 1:
            cur_flag = "-> "

        if cur_sma23 > pre_sma23 > pre_pre_sma23 and cur_sma23 - pre_sma23 > pre_sma23 - pre_pre_sma23 and close > max20:
            buy_flag_count += 1
            print(cur_flag + "Buy at %s %s %d" % (date, close, buy_flag_count))
            # share = float(close)
            continue
        if cur_sma21 < pre_sma21 < pre_pre_sma21 and pre_sma21 - cur_sma21 > pre_pre_sma21 - pre_sma21:
            sell_flag_count += 1
            print(cur_flag + "Sell at %s %s %d" % (date, close, sell_flag_count))
            # lirun += (float(close) - share)/share
            # share = 0
            # print(lirun)
            continue
        buy_flag_count = 0
        sell_flag_count = 0
    # print(lirun)

if __name__ == "__main__":
    arr_code = ["001632"]#, "006479", "006229", "501010", "005585", "007301", "004813", "006928"] 
    for code in arr_code:
        try:
            name, df = create_dataframe(code)
            if name == None:
                continue
            strategy(code, name, df, 200)
        except Exception as e:
            print("error happend", e)