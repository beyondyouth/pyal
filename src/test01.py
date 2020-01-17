'''
@Author: dong.zhili
@Date: 1970-01-01 08:00:00
@LastEditors: dong.zhili
@LastEditTime: 2020-05-25 12:51:53
@Description: 
'''
from pyalgotrade import strategy, broker, plotter
from pyalgotrade.barfeed import quandlfeed
from pyalgotrade.stratanalyzer import returns, sharpe
from pyalgotrade.technical import ma, macd, rsi, stoch, bollinger
from pyalgotrade import broker as basebroker

import MyDownload

class MyStrategy(strategy.BacktestingStrategy):
    def __init__(self, feed, instrument, bBandsPeriod):
        super(MyStrategy, self).__init__(feed)
        self.__instrument = instrument
        # 使用调整后的数据
        if feed.barsHaveAdjClose():
            self.setUseAdjustedValues(True)
        # 持有仓位
        self.__holdPosition = 0.0
        # 空闲仓位
        self.__emptyPosition = 10.0
        # 单元持仓金额
        self.__unit = self.getBroker().getCash(False) / 10
        # 统计收盘价
        self.__priceDS = feed[instrument].getPriceDataSeries()
        # 计算macd指标
        self.__macd = macd.MACD(self.__priceDS, 12, 26, 9)
        # 计算KD指标
        self.__stoch = stoch.StochasticOscillator(feed[instrument], 9, 3)
        # 计算rsi指标
        self.__rsi7 = rsi.RSI(self.__priceDS, 7)
        self.__rsi14 = rsi.RSI(self.__priceDS, 14)
        # 计算布林线
        self.__bbands = bollinger.BollingerBands(self.__priceDS, bBandsPeriod, 2)
 
    def getPriceDS(self):
        return self.__priceDS
        
    def getMACD(self):
        return self.__macd
 
    def getStoch(self):
        return self.__stoch
        
    def getRSI7(self):
        return self.__rsi7
        
    def getRSI14(self):
        return self.__rsi14
 
    def getBollingerBands(self):
        return self.__bbands
    
    def onOrderUpdated(self, order):
        if order.isBuy():
            orderType = "Buy"
        else:
            orderType = "Sell"
        self.info("%s order %d updated - Status: %s" % (
            orderType, order.getId(), basebroker.Order.State.toString(order.getState())
        ))
 
    def onBars(self, bars):
        lower = self.__bbands.getLowerBand()[-1]
        middle = self.__bbands.getMiddleBand()[-1]
        upper = self.__bbands.getUpperBand()[-1]
        
        if lower is None:
            return
 
        bar = bars[self.__instrument]
        # 持有股票份额
        shares = self.getBroker().getShares(self.__instrument)
        # 最新股价
        price = bar.getPrice()
        
        # 买入策略
        if self.__macd.getHistogram()[-1] is None or self.__macd.getHistogram()[-2] is None:
            return
        # 金叉形成
        if self.__macd.getHistogram()[-2] < 0 and self.__macd.getHistogram()[-1] > 0:
            PositionToBuy = 0
            if self.__emptyPosition >= 3:
                PositionToBuy = 3
            else:
                PositionToBuy = self.__emptyPosition
            sharesToBuy = int(PositionToBuy * self.__unit / price)
            if(self.marketOrder(self.__instrument, sharesToBuy)):
                self.__holdPosition += PositionToBuy
                self.__emptyPosition -= PositionToBuy
                self.info("Placing buy market order for %s shares" % sharesToBuy)
        # 死叉形成
        elif self.__macd.getHistogram()[-2] > 0 and self.__macd.getHistogram()[-1] < 0:
            PositionToSell = 0
            if self.__holdPosition >= 3:
                PositionToSell = -3
            else:
                PositionToSell = self.__holdPosition
            sharesToSell = int(PositionToSell * self.__unit / price)
            if(self.marketOrder(self.__instrument, sharesToSell)):
                self.__holdPosition += PositionToSell
                self.__emptyPosition -= PositionToSell
                self.info("Placing sell market order for %s shares" % sharesToSell)

def run_strategy():
    bBandsPeriod = 21
    instrument = "399300"
    
    # 下载股票数据
    MyDownload.download_csv(instrument, "2017-01-01", "2020-01-01", instrument+".csv")
    # 从CSV文件加载bar feed
    feed = quandlfeed.Feed()
    feed.addBarsFromCSV(instrument, instrument+".csv")
    
    # 创建MyStrategy实例
    myStrategy = MyStrategy(feed, instrument, bBandsPeriod)

    plt = plotter.StrategyPlotter(myStrategy, True, True, True)
    # 图例添加BOLL
    plt.getInstrumentSubplot(instrument).addDataSeries("upper", myStrategy.getBollingerBands().getUpperBand())
    plt.getInstrumentSubplot(instrument).addDataSeries("middle", myStrategy.getBollingerBands().getMiddleBand())
    plt.getInstrumentSubplot(instrument).addDataSeries("lower", myStrategy.getBollingerBands().getLowerBand())

    # test = myStrategy.getBollingerBands().getUpperBand() - myStrategy.getBollingerBands().getLowerBand()
    # plt.getOrCreateSubplot("test").addDataSeries("test", test)

    # 图例添加MACD
    plt.getOrCreateSubplot("macd").addDataSeries("DIF", myStrategy.getMACD())
    plt.getOrCreateSubplot("macd").addDataSeries("DEA", myStrategy.getMACD().getSignal())
    plt.getOrCreateSubplot("macd").addDataSeries("MACD", myStrategy.getMACD().getHistogram())

    # 图例添加KD
    plt.getOrCreateSubplot("stoch").addDataSeries("K", myStrategy.getStoch())
    plt.getOrCreateSubplot("stoch").addDataSeries("D", myStrategy.getStoch().getD())

    # 图例添加RSI
    plt.getOrCreateSubplot("rsi").addDataSeries("RSI7", myStrategy.getRSI7())
    plt.getOrCreateSubplot("rsi").addDataSeries("RSI14", myStrategy.getRSI14())
    plt.getOrCreateSubplot("rsi").addLine("Overbought", 70)
    plt.getOrCreateSubplot("rsi").addLine("Oversold", 30)

    # 添加回测分析
    returnsAnalyzer = returns.Returns()
    myStrategy.attachAnalyzer(returnsAnalyzer)

    # 添加夏普比率分析
    sharpeRatioAnalyzer = sharpe.SharpeRatio()
    myStrategy.attachAnalyzer(sharpeRatioAnalyzer)

    # 运行策略
    myStrategy.run()
    
    # 输出投资组合的最终资产总值
    print("最终资产总值: $%.2f" % myStrategy.getBroker().getEquity())
    # 输出年度收益
    print("年度收益: %.2f %%" % (returnsAnalyzer.getCumulativeReturns()[-1] * 100))
    # 输出夏普比率
    print("夏普比率: %.2f" % sharpeRatioAnalyzer.getSharpeRatio(0))
    
    # 展示折线图
    plt.plot()

run_strategy()