import operator

import DyCommon.DyTalib as DyTalib
from ..DyStockCtaTemplate import *
from ....Data.Utility.DyStockDataUtility import *


class DyST_BBands(DyStockCtaTemplate):

    name = 'DyST_BBands'
    chName = '布林线'

    backTestingMode = 'bar1d'

    broker = 'simu4'

    curCodeBuyMaxNbr = 1

    # 策略实盘参数
    param = OrderedDict\
                ([
                    ('周期', '22')
                ])
    
    longMas = [20, 30, 60] # 均线多头排列
    prepareDaysSize = 10 # 需要准备的日线数据的天数

    # 实盘参数
    bbPeriod = 22
    

    # UI
    dataHeader = [
                  '代码',
                  '名称',
                  '现价',
                  '涨幅(%)',
                  '最高涨幅(%)'
                  ]


    def __init__(self, ctaEngine, info, state, strategyParam=None):
        super().__init__(ctaEngine, info, state, strategyParam)

        if strategyParam is None: # 实盘参数
            pass
        else: # 回测参数
            self._bbPeriod = self._strategyParam['周期']

        self._curInit()

    def _onOpenConfig(self):
        self._monitoredStocks.extend(list(self._preparedData['preClose']))

    def _curInit(self, date=None):
        self._marketData = []

    @DyStockCtaTemplate.onOpenWrapper
    def onOpen(self, date, codes=None):
        # 当日初始化
        self._curInit(date)
        self._onOpenConfig()

        return True

    @DyStockCtaTemplate.onCloseWrapper
    def onClose(self):
        """
            策略每天收盘后的数据处理（由用户选择继承实现）
            持仓数据由策略模板类负责保存
            其他收盘后的数据，则必须由子类实现（即保存到@self._curSavedData）
        """
        #self._curSavedData['focus'] = self._focusInfoPool
        pass

    @DyStockCtaTemplate.processPreparedDataAdjWrapper
    def _processPreparedDataAdj(self, tick, preClose=None):
        """
            处理准备数据除复权
            @preClose: 数据库里的前一日收盘价，由装饰器传入。具体策略无需关注。
        """
        #print('in _processPreparedDataAdj() -- tick = ', tick)
        self.processOhlcvDataAdj(tick, preClose, self._preparedData, 'days')

    @DyStockCtaTemplate.processPreparedPosDataAdjWrapper
    def _processPreparedPosDataAdj(self, tick, preClose=None):
        """
            处理准备数据除复权
            @preClose: 数据库里的前一日收盘价，由装饰器传入。具体策略无需关注。
        """
        self.processDataAdj(tick, preClose, self._preparedPosData, ['upper', 'middle', 'lower'], keyCodeFormat=False)

    def _processAdj(self, tick):
        """ 处理除复权 """
        return self._processPreparedDataAdj(tick) and self._processPreparedPosDataAdj(tick)

    def _calcBuySignal(self, ticks):
        """
            计算买入信号
            @return: [buy code]
        """
        buyCodes = {}
        buyCodes1 = {}

        count = 0
        for code, tick in ticks.items():
            #print('in _calcBuySignal() -- code, tick = ', code, tick)
            if tick.time < '14:55:00':
                continue

            if tick.volume > self._preparedData['days'][code][-1][-1]:
                continue

            ## 当日价格穿价游走均线
            #if tick.low <= walkMa and tick.price > walkMa:
            #    buyCodes[code] = (tick.low - walkMa)/walkMa

            #elif tick.high > tick.low:
            #    buyCodes1[code] = (min(tick.open, tick.price) - tick.low)/(tick.high - tick.low)
            if self._preparedPosData.get(code): #preparedData['bbandsData']
                upper = self._preparedPosData[code]['upper']
                middle = self._preparedPosData[code]['middle']
                lower = self._preparedPosData[code]['lower']
                #if upper[-1] > upper[-2] and upper[-2] > upper[-3] \
                #    and middle[-1] > middle[-2] and middle[-2] > middle[-3] \
                #    and lower[-1] > lower[-2] and lower[-2] > lower[-3] \
                #    and tick.close > middle[-1]:
                if upper[-1] > upper[-2] and upper[-2] > upper[-3] \
                    and middle[-1] > middle[-2]:
                    buyCodes[code] = tick.close
            else:
                #info.print('股票{}不存在于_preparedPosData中。_preparedPosData的长度为{}'.format(code, len(self._preparedData) ), DyLogData.ind)
                #print('股票{}不存在于_preparedPosData中。_preparedPosData的长度为{}'.format(code, len(self._preparedData) ) )
                continue

        buyCodes = sorted(buyCodes, key=lambda k: buyCodes[k], reverse=True)
        buyCodes1 = sorted(buyCodes1, key=lambda k: buyCodes1[k], reverse=True)

        buyCodes.extend(buyCodes1)

        return buyCodes

    def _calcSellSignal(self, ticks):
        """
            计算卖出信号
        """
        sellCodes = []
        for code, pos in self._curPos.items():
            if pos.availVolume == 0:
                continue

            tick = ticks.get(code)
            if tick is None:
                continue

            if tick.volume == 0:
                continue

            pnlRatio = (tick.price - pos.cost)/pos.cost*100

            if pnlRatio < -5 or pnlRatio > 10:
                sellCodes.append(code)
                continue

            if pos.holdingPeriod > 5 and pnlRatio > 5:
                sellCodes.append(code)
                continue

            if upper[-1] < upper[-2] and middle[-1] < middle[-2] and lower[-1] < lower[-2] \
                or bar.close < middle[-1]:
                sellCodes.append(code)
                continue

            """
            if pnlRatio < -5:
                sellCodes.append(code)
            elif pnlRatio > 10:
                pos.reserved = True

            if pos.reserved:
                if tick.price < self._preparedPosData[code]['ma10']:
                    sellCodes.append(code)
            """

        return sellCodes

    def _procSignal(self, ticks):
        """
            处理买入和卖出信号
        """
        buyCodes, sellCodes = self._calcSignal(ticks)

        self._execSignal(buyCodes, sellCodes, ticks)

    def _calcSignal(self, ticks):
        """
            计算信号
            @return: [buy code], [sell code]
        """
        return self._calcBuySignal(ticks), self._calcSellSignal(ticks)

    def _execBuySignal(self, buyCodes, ticks):
        """
            执行买入信号
        """
        for code in buyCodes:
            if code in self._curPos:
                continue

            tick = ticks.get(code)
            if tick is None:
                continue

            self.buyByRatio(tick, 20, self.cAccountCapital)

    def _execSellSignal(self, sellCodes, ticks):
        """
            执行卖出信号
        """
        for code in sellCodes:
            self.closePos(ticks.get(code))

    def _execSignal(self, buyCodes, sellCodes, ticks):
        """
            执行信号
            先卖后买，对于日线级别的回测，可以有效利用仓位。
        """
        self._execSellSignal(sellCodes, ticks)
        self._execBuySignal(buyCodes, ticks)

    def onTicks(self, ticks):
        """
            收到行情TICKs推送
            @ticks: {code: DyStockCtaTickData}
        """
        self._marketData = []
        for code, tick in ticks.items():
            # 停牌
            if tick.volume == 0:
                continue

            # 处理除复权
            if not self._processAdj(tick):
                continue

        # 处理信号
        self._procSignal(ticks)

        # put market data to UI
        self._marketData.sort(key=operator.itemgetter(3))
        self.putStockMarketMonitorUiEvent(data=self._marketData, newData=True, datetime_=self.marketDatetime)

    def onBars(self, bars):
        self.onTicks(bars)


    #################### 开盘前的数据准备 ####################
    @classmethod
    def prepare(cls, date, dataEngine, info, codes=None, errorDataEngine=None, strategyParam=None, isBackTesting=False):
        """
            @date: 回测或者实盘时，此@date为前一交易日
            @return: {'preClose': {code: preClose},
                      'days': {code: [[OHLCV]]}
                     }
        """
        if isBackTesting:
            bbPeriod = strategyParam['周期']
        else:
            bbPeriod = cls.bbPeriod

        daysEngine = dataEngine.daysEngine
        errorDaysEngine = errorDataEngine.daysEngine

        if not daysEngine.loadCodeTable(codes=codes):
            return None
        codes = daysEngine.stockCodes

        info.print('开始计算{0}只股票的指标...'.format(len(codes)), DyLogData.ind)
        progress = DyProgress(info)
        progress.init(len(codes), 100, 10)

        maxPeriod = max(DyST_BBands.longMas[-1], DyST_BBands.bbPeriod)

        preparedData = {}
        preCloseData = {}
        daysData = {}
        bbandsData = {}
        print('in prepare() -- codes({})'.format(len(codes) ) )
        print(date)
        for code in codes:
            if not errorDaysEngine.loadCode(code, [date, -200], latestAdjFactorInDb=False):
                progress.update()
                continue

            # make sure enough periods
            df = errorDaysEngine.getDataFrame(code)
            if df.shape[0] < maxPeriod:
                progress.update()
                continue

            close = df['close'][-1]
            #-------------------- set prepared data for each code --------------------
            preCloseData[code] = close # preClose
            daysData[code] = df.ix[-DyST_BBands.prepareDaysSize:, ['open', 'high', 'low', 'close', 'volume']].values.tolist() # 日线OHLCV

            # calc the bbands
            #print(code)
            upper, middle, lower = DyST_BBands._bbands(df)
            #print(upper, middle, lower)
            if middle is None: return

            bbandsData[code] = {'preClose': close, # 为了除复权
                          'upper': upper,
                          'middle': middle,
                          'lower': lower
                          }

            progress.update()

        preparedData['preClose'] = preCloseData
        preparedData['days'] = daysData
        preparedData['bbandsData'] = bbandsData
        print('in prepare() -- bbandsData({})'.format(len(bbandsData) ) )

        info.print('计算{}只股票的指标完成, 共选出{}只股票'.format(len(codes), len(preCloseData)), DyLogData.ind)

        return preparedData

    @classmethod
    def preparePos(cls, date, dataEngine, info, posCodes=None, errorDataEngine=None, strategyParam=None, isBackTesting=False):
        """
            策略开盘前持仓准备数据
            @date: 前一交易日
            @return:
        """
        if not posCodes: # not positions
            return {}

        errorDaysEngine = errorDataEngine.daysEngine

        data = {}
        print('in preparePos() -- posCodes({})'.format(len(posCodes) ) )
        for code in posCodes:
            if not errorDaysEngine.loadCode(code, [date, -200], latestAdjFactorInDb=False):
                return None

            df = errorDaysEngine.getDataFrame(code)

            highs, lows, closes = df['high'].values, df['low'].values, df['close'].values

            # calc the bbands
            upper, middle, lower = DyST_BBands._bbands(df)
            if middle is None: return

            data[code] = {'preClose': closes[-1], # 为了除复权
                          'upper': upper,
                          'middle': middle,
                          'lower': lower
                          }

        return data

    @classmethod
    def _bbands(cls, df):
        try:
            #close = df['close']
            close = df['close']
        except Exception as ex:
            print(ex)
            return None, None, None

        #if close.shape[0] != DyST_BBands.bbPeriod:
        #    print(ex)
        #    return None, None, None

        try:
            upper, middle, lower = talib.BBANDS(
                                close.values, 
                                timeperiod=DyST_BBands.bbPeriod,
                                # number of non-biased standard deviations from the mean
                                nbdevup=1,
                                nbdevdn=1,
                                # Moving average type: simple moving average here
                                matype=0)
        except Exception as ex:
            print(ex)
            return None, None, None

        return upper, middle, lower
