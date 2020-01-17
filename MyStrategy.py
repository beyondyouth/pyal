'''
@Author: dong.zhili
@Date: 1970-01-01 08:00:00
@LastEditors  : dong.zhili
@LastEditTime : 2020-01-17 19:00:01
@Description: 
'''
from pyalgotrade import strategy, broker, plotter
from pyalgotrade.barfeed import quandlfeed
from pyalgotrade.stratanalyzer import returns, sharpe
from pyalgotrade.technical import ma, rsi, bollinger
from pyalgotrade import broker as basebroker

import numpy as np
import MyDownload

# 计算近num天的线性回归线斜率
def getLinearRegression(dataDS , num):
    count = 0
    temp = []
    for i in range(num):
        if dataDS[i-num] is not None:
            tmp = float(dataDS[i-num])
            temp.append(tmp)
            count += 1
    x = np.array([i for i in range(count)])
    y = np.array(temp)
    if len(x) != len(y):
        return
    numerator = 0.0
    denominator = 0.0
    x_mean = np.mean(x)
    y_mean = np.mean(y)
    for i in range(len(x)):
        numerator += (x[i]-x_mean)*(y[i]-y_mean)
        denominator += np.square((x[i]-x_mean))
    # print('numerator:',numerator,'denominator:',denominator)
    b0 = numerator/denominator
    b1 = y_mean - b0*x_mean
    # print("b0 = %.2f" % b0)
    return b0

class MyStrategy(strategy.BacktestingStrategy):
    def __init__(self, feed, instrument, smaPeriod, rsiPeriod, bBandsPeriod):
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
        # 计算SMA均线
        self.__sma = ma.SMA(self.__priceDS, smaPeriod)
        # 计算rsi指标
        self.__rsi = rsi.RSI(self.__priceDS, rsiPeriod)
        # 计算布林线
        self.__bbands = bollinger.BollingerBands(self.__priceDS, bBandsPeriod, 2)
        self.flag = True

    def getPriceDS(self):
        return self.__priceDS
        
    def getSMA(self):
        return self.__sma

    def getRSI(self):
        return self.__rsi
    
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
        # 持有份额
        shares = self.getBroker().getShares(self.__instrument)
        # 最新股价
        price = bar.getPrice()
        # 买卖策略

        '''
        若布林线包络扩张根据upper和lower的最近3日的线性回归斜率及rsi指标决定加仓层数并置标志位
        若布林线包络缩紧重置标志位，用于测量下次包络扩张
        '''
        # 计算线性回归线斜率
        rsiLinear = getLinearRegression(self.getRSI(), 7)
        upperLinear = getLinearRegression(self.__bbands.getUpperBand(), 3)
        lowerLinear = getLinearRegression(self.__bbands.getLowerBand(), 3)
        
        # 买入策略
        if upperLinear - lowerLinear > 0.3:          # 包络扩张
            if rsiLinear > 0.3 and self.flag:        # 上行包络
                PositionToBuy = 0
                if upperLinear - lowerLinear > 0.8 and self.__rsi[-2] < 50:     # 加仓3层
                    if self.__emptyPosition >= 3:
                        PositionToBuy = 3
                    else:
                        PositionToBuy = self.__emptyPosition
                elif upperLinear - lowerLinear > 0.5 and self.__rsi[-2] < 70:   # 加仓2层
                    if self.__emptyPosition >= 2:
                        PositionToBuy = 2
                    else:
                        PositionToBuy = self.__emptyPosition
                else:                                                           # 加仓1层
                    if self.__emptyPosition >= 1:
                        PositionToBuy = 1
                    else:
                        PositionToBuy = self.__emptyPosition
                sharesToBuy = int(PositionToBuy * self.__unit / price)
                if(self.marketOrder(self.__instrument, sharesToBuy)):
                    self.__holdPosition += PositionToBuy
                    self.__emptyPosition -= PositionToBuy
                    self.info("Placing buy market order for %s shares" % sharesToBuy)
                self.flag = False
            elif rsiLinear < -0.3 and self.flag:        # 下行包络
                PositionToSell = 0
                if upperLinear - lowerLinear < -0.8 and self.__rsi[-2] > 50:    # 减仓3层
                    if self.__holdPosition >= 3:
                        PositionToSell = -3
                    else:
                        PositionToSell = self.__holdPosition
                elif upperLinear - lowerLinear > 0.5 and self.__rsi[-2] > 30:   # 减仓2层
                    if self.__holdPosition >= 2:
                        PositionToSell = -2
                    else:
                        PositionToSell = self.__holdPosition
                else:                                                           # 减仓1层
                    if self.__holdPosition >= 1:
                        PositionToSell = -1
                    else:
                        PositionToSell = self.__holdPosition
                sharesToSell = int(PositionToSell * self.__unit / price)
                if(self.marketOrder(self.__instrument, sharesToSell)):
                    self.__holdPosition += PositionToSell
                    self.__emptyPosition -= PositionToSell
                    self.info("Placing sell market order for %s shares" % sharesToSell)
                self.flag = False
        elif upperLinear - lowerLinear < -0.3:       # 包络缩紧
            self.flag = True

def run_strategy():
    smaPeriod = 30
    rsiPeriod = 14
    bBandsPeriod = 21
    instrument = "test"
    
    # 下载股票数据
    MyDownload.download_csv("399975", "2017-01-01", "2020-01-01", "399975.csv")
    # 从CSV文件加载bar feed
    feed = quandlfeed.Feed()
    feed.addBarsFromCSV(instrument, "399975.csv")
    
    # 创建MyStrategy实例
    myStrategy = MyStrategy(feed, instrument, smaPeriod, rsiPeriod, bBandsPeriod)

    plt = plotter.StrategyPlotter(myStrategy, True, True, True)
    # 图例添加布林线
    plt.getInstrumentSubplot(instrument).addDataSeries("upper", myStrategy.getBollingerBands().getUpperBand())
    plt.getInstrumentSubplot(instrument).addDataSeries("middle", myStrategy.getBollingerBands().getMiddleBand())
    plt.getInstrumentSubplot(instrument).addDataSeries("lower", myStrategy.getBollingerBands().getLowerBand())

    # test = myStrategy.getBollingerBands().getUpperBand() - myStrategy.getBollingerBands().getLowerBand()
    # plt.getOrCreateSubplot("test").addDataSeries("test", test)

    # 图例添加SMA均线
    plt.getOrCreateSubplot("sma").addDataSeries("SMA", myStrategy.getSMA())
    plt.getOrCreateSubplot("sma").addDataSeries("zxtx", myStrategy.getPriceDS())

    plt.getOrCreateSubplot("rsi").addDataSeries("RSI", myStrategy.getRSI())
    # 设置超卖线
    plt.getOrCreateSubplot("rsi").addLine("Overbought", 70)
    # 设置超买线
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
