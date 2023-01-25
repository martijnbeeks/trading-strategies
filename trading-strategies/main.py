import pandas as pd
import pandas_ta as ta
from backtesting import Strategy
from backtesting import Backtest


class DataPreparation:
    def __init__(self):
        self.df = pd.read_csv("./data/EURUSD_Candlestick_5_M_ASK_30.09.2019-30.09.2022.csv")
        self.backcandles = 15

    def preprocessing(self):
        self.df["Gmt time"] = self.df["Gmt time"].str.replace(".000", "")
        self.df['Gmt time'] = pd.to_datetime(self.df['Gmt time'], format='%d.%m.%Y %H:%M:%S')
        self.df.set_index("Gmt time", inplace=True)

        # Remove days with no trading activity
        self.df = self.df[self.df.High != self.df.Low]

    def add_technical_indicators(self):
        self.df["VWAP"] = ta.vwap(self.df.High, self.df.Low, self.df.Close, self.df.Volume)
        self.df['RSI'] = ta.rsi(self.df.Close, length=16)
        my_bbands = ta.bbands(self.df.Close, length=14, std=2.0)
        self.df = self.df.join(my_bbands)

    def vwap_signal(self):
        """
        VWAP signal stands for volume-weighted average price.
        """
        VWAPsignal = [0] * len(self.df)

        for row in range(self.backcandles, len(self.df)):
            upt = 1
            dnt = 1
            for i in range(row - self.backcandles, row + 1):
                if max(self.df.Open[i], self.df.Close[i]) >= self.df.VWAP[i]:
                    dnt = 0
                if min(self.df.Open[i], self.df.Close[i]) <= self.df.VWAP[i]:
                    upt = 0
            if upt == 1 and dnt == 1:
                VWAPsignal[row] = 3
            elif upt == 1:
                VWAPsignal[row] = 2
            elif dnt == 1:
                VWAPsignal[row] = 1

        self.df['VWAPSignal'] = VWAPsignal

    def strategy(self, df, l):
        if (df.VWAPSignal[l] == 2
                and df.Close[l] <= df['BBL_14_2.0'][l]
                and df.RSI[l] < 45):
            return 2
        if (df.VWAPSignal[l] == 1
                and df.Close[l] >= df['BBU_14_2.0'][l]
                and df.RSI[l] > 55):
            return 1
        return 0


    def result(self):
        TotSignal = [0] * len(self.df)
        for row in range(self.backcandles, len(self.df)):
            TotSignal[row] = self.strategy(self.df, row)
        self.df['TotalSignal'] = TotSignal
        self.df['ATR'] = ta.atr(self.df.High, self.df.Low, self.df.Close, length=7)

    def get_data(self):
        self.preprocessing()
        self.add_technical_indicators()
        self.vwap_signal()
        self.result()
        return self.df


class MyStrat(Strategy):
    initsize = 0.99
    mysize = initsize

    def init(self):
        super().init()
        self.signal1 = self.I(SIGNAL)

    def next(self):
        super().next()
        slatr = 1.2 * self.data.ATR[-1]
        TPSLRatio = 1.5

        if len(self.trades) > 0:
            if self.trades[-1].is_long and self.data.RSI[-1] >= 90:
                self.trades[-1].close()
            elif self.trades[-1].is_short and self.data.RSI[-1] <= 10:
                self.trades[-1].close()

        if self.signal1 == 2 and len(self.trades) == 0:
            sl1 = self.data.Close[-1] - slatr
            tp1 = self.data.Close[-1] + slatr * TPSLRatio
            self.buy(sl=sl1, tp=tp1, size=self.mysize)

        elif self.signal1 == 1 and len(self.trades) == 0:
            sl1 = self.data.Close[-1] + slatr
            tp1 = self.data.Close[-1] - slatr * TPSLRatio
            self.sell(sl=sl1, tp=tp1, size=self.mysize)


data = DataPreparation().get_data()


def SIGNAL():
    return data.TotalSignal

bt = Backtest(data, MyStrat, cash=100, margin=1 / 10, commission=0.0)
stat = bt.run()
print(stat)
