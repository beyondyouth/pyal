'''
@Author: dong.zhili
@Date: 1970-01-01 08:00:00
@LastEditors  : dong.zhili
@LastEditTime : 2020-01-17 18:48:52
@Description: 
'''
from urllib import response
import tushare as ts
import pandas as pd
import os
import requests
 
def download_csv(code, start_date, end_date, filepath):
    data = ts.get_hist_data(code, start=start_date, end=end_date)

    # 数据存盘
    data.to_csv('temp.csv')

    # 读出数据，DataFrame格式
    df = pd.read_csv('temp.csv')

    # 从df中选取数据段，改变段名；新段'Adj Close'使用原有段'close'的数据  
    df2 = pd.DataFrame({'Date' : df['date'], 'Open' : df['open'],
                        'High' : df['high'],'Close' : df['close'],
                        'Low' : df['low'],'Volume' : df['volume'],
                        'Adj Close':df['close']})

    # 按照Yahoo格式的要求，调整df2各段的顺序
    dt = df2.pop('Date')
    df2.insert(0,'Date',dt)
    o = df2.pop('Open')
    df2.insert(1,'Open',o)
    h = df2.pop('High')
    df2.insert(2,'High',h)
    l = df2.pop('Low')
    df2.insert(3,'Low',l)
    c = df2.pop('Close')
    df2.insert(4,'Close',c)
    v = df2.pop('Volume')
    df2.insert(5,'Volume',v)

    param = {"Referer": "https://finance.sina.com.cn"}
    resp = requests.get("https://hq.sinajs.cn/list=sz%s,s_sz%s" % (code, code), headers=param)
    data = resp.content.decode(encoding='gb2312')
    
    lines = data.splitlines()
    list1 = lines[0].split("\"")[1].split(',')
    list2 = lines[1].split("\"")[1].split(',')
    print(list1)
    print(list2)
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
    # print(new)
    if new.iat[0, 0] != df2.iat[0, 0]:
        df2 = pd.concat([new,df2], axis=0 ,ignore_index=True)
    # df2=df2.append(new,ignore_index=True)

    # 新格式数据存盘，不保存索引编号  
    df2.to_csv(filepath, index=False)
    os.remove("temp.csv")
