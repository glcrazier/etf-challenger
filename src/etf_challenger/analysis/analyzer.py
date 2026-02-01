"""ETF分析功能模块"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from ..models.etf import ETFHolding


class ETFAnalyzer:
    """ETF分析器"""

    @staticmethod
    def calculate_returns(df: pd.DataFrame, column: str = '收盘') -> pd.DataFrame:
        """
        计算收益率

        Args:
            df: 历史数据DataFrame
            column: 用于计算的列名

        Returns:
            添加了收益率列的DataFrame
        """
        result = df.copy()

        # 日收益率
        result['日收益率'] = result[column].pct_change() * 100

        # 累计收益率
        result['累计收益率'] = ((result[column] / result[column].iloc[0]) - 1) * 100

        return result

    @staticmethod
    def calculate_volatility(df: pd.DataFrame, window: int = 20, column: str = '收盘') -> pd.DataFrame:
        """
        计算波动率

        Args:
            df: 历史数据DataFrame
            window: 滚动窗口大小
            column: 用于计算的列名

        Returns:
            添加了波动率列的DataFrame
        """
        result = df.copy()

        # 计算日收益率
        returns = result[column].pct_change()

        # 滚动波动率（年化）
        result[f'{window}日波动率'] = returns.rolling(window=window).std() * np.sqrt(252) * 100

        return result

    @staticmethod
    def calculate_moving_averages(
        df: pd.DataFrame,
        windows: List[int] = [5, 10, 20, 60],
        column: str = '收盘'
    ) -> pd.DataFrame:
        """
        计算移动平均线

        Args:
            df: 历史数据DataFrame
            windows: 移动平均窗口列表
            column: 用于计算的列名

        Returns:
            添加了移动平均线的DataFrame
        """
        result = df.copy()

        for window in windows:
            result[f'MA{window}'] = result[column].rolling(window=window).mean()

        return result

    @staticmethod
    def calculate_rsi(df: pd.DataFrame, period: int = 14, column: str = '收盘') -> pd.DataFrame:
        """
        计算相对强弱指标(RSI)

        Args:
            df: 历史数据DataFrame
            period: RSI周期
            column: 用于计算的列名

        Returns:
            添加了RSI列的DataFrame
        """
        result = df.copy()

        # 计算价格变动
        delta = result[column].diff()

        # 分离上涨和下跌
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)

        # 计算平均涨跌幅
        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()

        # 计算RS和RSI
        rs = avg_gain / avg_loss
        result['RSI'] = 100 - (100 / (1 + rs))

        return result

    @staticmethod
    def calculate_macd(
        df: pd.DataFrame,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9,
        column: str = '收盘'
    ) -> pd.DataFrame:
        """
        计算MACD指标

        Args:
            df: 历史数据DataFrame
            fast: 快线周期
            slow: 慢线周期
            signal: 信号线周期
            column: 用于计算的列名

        Returns:
            添加了MACD相关列的DataFrame
        """
        result = df.copy()

        # 计算EMA
        ema_fast = result[column].ewm(span=fast, adjust=False).mean()
        ema_slow = result[column].ewm(span=slow, adjust=False).mean()

        # MACD线
        result['MACD'] = ema_fast - ema_slow

        # 信号线
        result['Signal'] = result['MACD'].ewm(span=signal, adjust=False).mean()

        # 柱状图
        result['Histogram'] = result['MACD'] - result['Signal']

        return result

    @staticmethod
    def calculate_bollinger_bands(
        df: pd.DataFrame,
        window: int = 20,
        num_std: float = 2.0,
        column: str = '收盘'
    ) -> pd.DataFrame:
        """
        计算布林带

        Args:
            df: 历史数据DataFrame
            window: 移动平均窗口
            num_std: 标准差倍数
            column: 用于计算的列名

        Returns:
            添加了布林带列的DataFrame
        """
        result = df.copy()

        # 中轨（移动平均线）
        result['BB_Middle'] = result[column].rolling(window=window).mean()

        # 标准差
        std = result[column].rolling(window=window).std()

        # 上轨和下轨
        result['BB_Upper'] = result['BB_Middle'] + (std * num_std)
        result['BB_Lower'] = result['BB_Middle'] - (std * num_std)

        return result

    @staticmethod
    def analyze_performance(df: pd.DataFrame, column: str = '收盘') -> Dict[str, float]:
        """
        分析ETF表现

        Args:
            df: 历史数据DataFrame
            column: 用于分析的列名

        Returns:
            包含各项表现指标的字典
        """
        # 计算收益率
        returns = df[column].pct_change().dropna()

        # 总收益率
        total_return = ((df[column].iloc[-1] / df[column].iloc[0]) - 1) * 100

        # 年化收益率（假设252个交易日）
        days = len(df)
        annualized_return = ((1 + total_return / 100) ** (252 / days) - 1) * 100

        # 波动率（年化）
        volatility = returns.std() * np.sqrt(252) * 100

        # 最大回撤
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = drawdown.min() * 100

        # 夏普比率（假设无风险利率为3%）
        risk_free_rate = 0.03
        sharpe_ratio = (annualized_return - risk_free_rate * 100) / volatility if volatility > 0 else 0

        return {
            '总收益率(%)': round(total_return, 2),
            '年化收益率(%)': round(annualized_return, 2),
            '年化波动率(%)': round(volatility, 2),
            '最大回撤(%)': round(max_drawdown, 2),
            '夏普比率': round(sharpe_ratio, 2),
            '交易天数': days
        }

    @staticmethod
    def analyze_holdings(holdings: List[ETFHolding]) -> Dict[str, any]:
        """
        分析持仓结构

        Args:
            holdings: 持仓列表

        Returns:
            持仓分析结果
        """
        if not holdings:
            return {}

        total_weight = sum(h.weight for h in holdings)
        top_holdings = sorted(holdings, key=lambda x: x.weight, reverse=True)[:10]

        # 计算集中度
        top5_weight = sum(h.weight for h in top_holdings[:5])
        top10_weight = sum(h.weight for h in top_holdings[:10])

        return {
            '持仓数量': len(holdings),
            '总权重(%)': round(total_weight, 2),
            '前5大持仓权重(%)': round(top5_weight, 2),
            '前10大持仓权重(%)': round(top10_weight, 2),
            '前10大持仓': [
                {
                    '代码': h.stock_code,
                    '名称': h.stock_name,
                    '权重(%)': round(h.weight, 2)
                }
                for h in top_holdings
            ]
        }

    @staticmethod
    def find_support_resistance(
        df: pd.DataFrame,
        column: str = '收盘',
        window: int = 20
    ) -> Tuple[float, float]:
        """
        寻找支撑位和压力位

        Args:
            df: 历史数据DataFrame
            column: 用于分析的列名
            window: 窗口大小

        Returns:
            (支撑位, 压力位)
        """
        # 简单方法：使用最近N天的最低价作为支撑位，最高价作为压力位
        recent_data = df.tail(window)

        support = recent_data['最低价'].min()
        resistance = recent_data['最高价'].max()

        return support, resistance
