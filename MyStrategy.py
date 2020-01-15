'''
@Author: dong.zhili
@Date: 1970-01-01 08:00:00
@LastEditors  : dong.zhili
@LastEditTime : 2020-01-15 15:50:36
@Description: 
'''
from pyalgotrade import strategy, broker, plotter
from pyalgotrade.barfeed import quandlfeed
from pyalgotrade.stratanalyzer import returns, sharpe
from pyalgotrade.technical import ma, rsi, bollinger


class MyStrategy(strategy.BacktestingStrategy):
    def __init__(self, feed, instrument, smaPeriod, rsiPeriod, bBandsPeriod):
        super(MyStrategy, self).__init__(feed)
        self.__position = None
        self.__instrument = instrument
        # 使用调整后的数据
        if feed.barsHaveAdjClose():
            self.setUseAdjustedValues(True)
        # 统计收盘价
        self.__priceDS = feed[instrument].getPriceDataSeries()
        # 计算SMA均线
        self.__sma = ma.SMA(self.__priceDS, smaPeriod)
        # 计算rsi指标
        self.__rsi = rsi.RSI(self.__priceDS, rsiPeriod)
        # 计算布林线
        self.__bbands = bollinger.BollingerBands(self.__priceDS, bBandsPeriod, 2)

    def getPriceDS(self):
        return self.__priceDS
        
    def getSMA(self):
        return self.__sma

    def getRSI(self):
        return self.__rsi
    
    def getBollingerBands(self):
        return self.__bbands
    
    def onEnterOk(self, position):
        execInfo = position.getEntryOrder().getExecutionInfo()
        self.info("BUY at $%.2f" % (execInfo.getPrice()))

    def onEnterCanceled(self, position):
        self.__position = None

    def onExitOk(self, position):
        execInfo = position.getExitOrder().getExecutionInfo()
        self.info("SELL at $%.2f" % (execInfo.getPrice()))
        self.__position = None

    def onExitCanceled(self, position):
        self.__position.exitMarket()

    def onBars(self, bars):
        lower = self.__bbands.getLowerBand()[-1]
        upper = self.__bbands.getUpperBand()[-1]
        if lower is None:
            return

        bar = bars[self.__instrument]
        # 股价
        price = bar.getPrice()
    	
        if self.__position is None:
            # 计算加仓份额
            shares = int(self.getBroker().getCash()*0.9 / bar.getClose())
            # 下穿布林线则加仓
            if bar.getClose() < lower:
            # 收盘价大于15日均线则加仓
            # if bar.getPrice() > self.__sma[-1]:
                self.__position = self.enterLong(self.__instrument, shares, True)
        else:
            # 上穿布林线则减仓
            if bar.getClose() > upper:
            # if bar.getPrice() < self.__sma[-1]:
            # 收盘价小于15日均线则减仓
                self.__position.exitMarket()

def run_strategy():
    smaPeriod = 15
    rsiPeriod = 15
    bBandsPeriod = 21
    instrument = "zxtx"
    
    # 从CSV文件加载bar feed
    feed = quandlfeed.Feed()
    feed.addBarsFromCSV(instrument, "SZ000063.csv")
    
    # 创建MyStrategy实例
    myStrategy = MyStrategy(feed, instrument, smaPeriod, rsiPeriod, bBandsPeriod)

    # 计算夏普比率
    sharpeRatioAnalyzer = sharpe.SharpeRatio()
    myStrategy.attachAnalyzer(sharpeRatioAnalyzer)

    plt = plotter.StrategyPlotter(myStrategy, True, True, True)

    # 图例添加布林线
    plt.getInstrumentSubplot(instrument).addDataSeries("upper", myStrategy.getBollingerBands().getUpperBand())
    plt.getInstrumentSubplot(instrument).addDataSeries("middle", myStrategy.getBollingerBands().getMiddleBand())
    plt.getInstrumentSubplot(instrument).addDataSeries("lower", myStrategy.getBollingerBands().getLowerBand())
    # 图例添加SMA均线
    plt.getOrCreateSubplot("sma").addDataSeries("SMA", myStrategy.getSMA())
    plt.getOrCreateSubplot("sma").addDataSeries("zxtx", myStrategy.getPriceDS())

    plt.getOrCreateSubplot("rsi").addDataSeries("RSI", myStrategy.getRSI())
    # 设置超卖线
    plt.getOrCreateSubplot("rsi").addLine("Overbought", 70)
    # 设置超买线
    plt.getOrCreateSubplot("rsi").addLine("Oversold", 30)

    # 策略部署回测
    # returnsAnalyzer = returns.Returns()
    # myStrategy.attachAnalyzer(returnsAnalyzer)
    # plt.getOrCreateSubplot("returns").addDataSeries("Simple returns", returnsAnalyzer.getReturns())

    # 运行策略
    myStrategy.run()
    
    # 输出夏普比率
    print("夏普比率: %.2f" % sharpeRatioAnalyzer.getSharpeRatio(0.05))
    
    # 输出最终资产总值
    print("Final portfolio value: $%.2f" % myStrategy.getBroker().getEquity())
    
    # 展示折线图
    plt.plot()

run_strategy()
