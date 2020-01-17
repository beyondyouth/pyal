'''
@Author: dong.zhili
@Date: 1970-01-01 08:00:00
@LastEditors: dong.zhili
@LastEditTime: 2020-05-25 12:51:53
@Description: 
'''
import datetime
import os
from pyalgotrade import strategy, broker, plotter
from pyalgotrade.barfeed import quandlfeed
from pyalgotrade.stratanalyzer import returns, sharpe
from pyalgotrade.technical import ma, macd, rsi, stoch, bollinger
from pyalgotrade import broker as basebroker
from pyalgotrade.technical import cross, highlow

import MyDownload

class MyStrategy(strategy.BacktestingStrategy):
    def __init__(self, feed, instrument, bBandsPeriod):
        super(MyStrategy, self).__init__(feed)
        self.__instrument = instrument
        # 使用调整后的数据
        if feed.barsHaveAdjClose():
            self.setUseAdjustedValues(True)
        
        # 统计收盘价
        self.__price = feed[instrument].getPriceDataSeries()
        # 计算macd指标
        self.__macd = macd.MACD(self.__price, 12, 26, 9)
        # 计算KD指标
        self.__stoch = stoch.StochasticOscillator(feed[instrument], 9, 3)
        # 计算rsi指标
        self.__rsi7 = rsi.RSI(self.__price, 7)
        self.__rsi23 = rsi.RSI(self.__price, 23)
        # 计算布林线
        self.__bbands = bollinger.BollingerBands(self.__price, bBandsPeriod, 2)

        self.__maxN = highlow.High(self.__price, 20)

        self.__sma21 = ma.SMA(self.__price, 21)
        self.__sma23 = ma.SMA(self.__price, 23)
        self.setDebugMode(False)
        self.__date = self.getCurrentDateTime()
        self.__realDate = datetime.datetime.now().strftime("%Y-%m-%d 00:00:00")
 
    def getPriceDS(self):
        return self.__price
    
    def getSMA21(self):
        return self.__sma21
    
    def getSMA23(self):
        return self.__sma23
    
    def getRSI23(self):
        return self.__rsi23
    
    def onOrderUpdated(self, order):
        if order.isBuy():
            orderType = "Buy"
        else:
            orderType = "Sell"
        # self.info("%s order %d updated - Status: %s" % (
        #     orderType, order.getId(), basebroker.Order.State.toString(order.getState())
        # ))
 
    def onBars(self, bars):
        if self.__sma23[-1] is None:
            return
        shares = self.getBroker().getShares(self.__instrument)
        # print("shares:", shares)
        bar = bars[self.__instrument]
        if self.__bbands.getMiddleBand()[-3] is None:
            return
        if self.__sma23[-1] > self.__sma23[-2] > self.__sma23[-3] and self.__sma23[-1] - self.__sma23[-2] > self.__sma23[-2] - self.__sma23[-3] and bar.getClose() > self.__maxN[-2]:
            # if str(self.getCurrentDateTime()) == self.__realDate:
            # print("Buy at %s, %.2f" % (self.getCurrentDateTime(), bar.getClose()))
            if shares == 0: 
                sharesToBuy = int(self.getBroker().getCash(False) / bar.getClose())
                print("sharesToBuy", sharesToBuy)
                self.info("Placing buy market order for %s shares" % sharesToBuy)
                self.marketOrder(self.__instrument, sharesToBuy, onClose=True)
        elif self.__sma21[-1] < self.__sma21[-2] < self.__sma21[-3] and self.__sma21[-2] - self.__sma21[-1] > self.__sma21[-3] - self.__sma21[-2] or bar.getClose() < self.__maxN[-2]*0.95:
            
            # print(str(self.getCurrentDateTime()))
            # if str(self.getCurrentDateTime()) == self.__realDate:
            # print("Sell at %s, %.2f" % (self.getCurrentDateTime(), bar.getClose()))
            if shares > 0: 
                self.info("Placing sell market order for %s shares" % shares)
                self.marketOrder(self.__instrument, -1*shares, onClose=True)
        # print(self.getBroker().getShares())
        # print(self.getBroker().getCash())

def run_strategy(instrument):
    bBandsPeriod = 23
    # instrument = "399003"
    
    # 下载股票数据
    # if not os.path.isfile(instrument+".csv"):
    # if os.path.isfile(instrument+".csv"):
    #     os.remove(instrument+".csv")
    # MyDownload.download_csv(instrument, None, None, instrument+".csv") # "2022-01-01"
    # 从CSV文件加载bar feed
    feed = quandlfeed.Feed()
    feed.addBarsFromCSV(instrument, instrument+".csv")
    
    # 创建MyStrategy实例
    myStrategy = MyStrategy(feed, instrument, bBandsPeriod)
    myStrategy.setDebugMode(False)

    plt = plotter.StrategyPlotter(myStrategy, True, True, True)
    # 图例添加BOLL
    plt.getInstrumentSubplot(instrument).addDataSeries("sma21", myStrategy.getSMA21())
    plt.getInstrumentSubplot(instrument).addDataSeries("sma23", myStrategy.getSMA23())

    plt.getOrCreateSubplot("rsi").addDataSeries("rsi", myStrategy.getRSI23())

    # 添加回测分析
    returnsAnalyzer = returns.Returns()
    myStrategy.attachAnalyzer(returnsAnalyzer)

    # 添加夏普比率分析
    sharpeRatioAnalyzer = sharpe.SharpeRatio()
    myStrategy.attachAnalyzer(sharpeRatioAnalyzer)

    # 运行策略
    myStrategy.run()
    
    # 输出投资组合的最终资产总值
    print(instrument)
    print("最终资产总值: $%.2f" % myStrategy.getBroker().getEquity())
    # 输出年度收益
    print("年度收益: %.2f %%" % (returnsAnalyzer.getCumulativeReturns()[-1] * 100))
    # 输出夏普比率
    print("夏普比率: %.2f" % sharpeRatioAnalyzer.getSharpeRatio(0))
    # return (returnsAnalyzer.getCumulativeReturns()[-1] * 100)
    # 展示折线图
    plt.plot()
# run_strategy("399006")
sum = 0
test = ["399363"]#["399363", "399935", "399989", "399006", "399300", "399997", "399933", "399417"]
for instrument in test:
    sum += run_strategy(instrument)//len(test)
print("总收益率: ", sum)

                                                                                                                          
'''
def onBars(self, bars):
        if self.__sma23[-1] is None:
            return
        shares = self.getBroker().getShares(self.__instrument)
        bar = bars[self.__instrument]
        if self.__bbands.getMiddleBand()[-3] is None:
            return
        if self.__sma23[-1] > self.__sma23[-2] > self.__sma23[-3] and self.__sma23[-1] - self.__sma23[-2] > self.__sma23[-2] - self.__sma23[-3] and bar.getClose() >= self.__maxN[-1]:
            # if str(self.getCurrentDateTime()) == self.__realDate:
            print("Buy at %s, %.2f" % (self.getCurrentDateTime(), bar.getClose()))
            if shares == 0: 
                sharesToBuy = int(self.getBroker().getCash(False) / bar.getClose())
                # self.info("Placing buy market order for %s shares" % sharesToBuy)
                self.marketOrder(self.__instrument, sharesToBuy)
        elif self.__sma21[-1] < self.__sma21[-2] < self.__sma21[-3] and self.__sma21[-2] - self.__sma21[-1] > self.__sma21[-3] - self.__sma21[-2]:
            # self.info("Placing sell market order for %s shares" % shares)
            # print(str(self.getCurrentDateTime()))
            # if str(self.getCurrentDateTime()) == self.__realDate:
            print("Sell at %s, %.2f" % (self.getCurrentDateTime(), bar.getClose()))
            if shares > 0: 
                self.marketOrder(self.__instrument, -1*shares)
'''