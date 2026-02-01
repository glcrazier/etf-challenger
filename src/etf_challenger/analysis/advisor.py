"""交易信号和建议模块"""

from dataclasses import dataclass
from typing import List, Dict, Optional
from enum import Enum
import pandas as pd


class SignalType(Enum):
    """信号类型"""
    STRONG_BUY = "强烈买入"
    BUY = "买入"
    HOLD = "持有"
    SELL = "卖出"
    STRONG_SELL = "强烈卖出"


class IndicatorSignal(Enum):
    """指标信号"""
    BULLISH = "看涨"
    NEUTRAL = "中性"
    BEARISH = "看跌"


@dataclass
class TradingSignal:
    """交易信号"""
    signal_type: SignalType
    confidence: float  # 0-100，信号置信度
    reasons: List[str]  # 建议原因
    indicators: Dict[str, str]  # 各指标的状态
    risk_level: str  # 风险等级：低/中/高
    price_target: Optional[float] = None  # 目标价位
    stop_loss: Optional[float] = None  # 止损价位


class TradingAdvisor:
    """交易建议分析器"""

    def __init__(self):
        self.weights = {
            'ma_cross': 20,      # 均线交叉
            'rsi': 15,           # RSI
            'macd': 20,          # MACD
            'bollinger': 15,     # 布林带
            'trend': 15,         # 趋势
            'volume': 10,        # 成交量
            'premium': 5,        # 溢价率
        }

    def analyze(
        self,
        df: pd.DataFrame,
        premium_rate: Optional[float] = None
    ) -> TradingSignal:
        """
        综合分析生成交易建议

        Args:
            df: 包含技术指标的历史数据
            premium_rate: 当前溢价率

        Returns:
            交易信号
        """
        signals = {}
        scores = []

        # 1. 均线交叉信号
        ma_signal, ma_score = self._analyze_ma_cross(df)
        signals['均线'] = ma_signal
        scores.append(ma_score * self.weights['ma_cross'])

        # 2. RSI信号
        rsi_signal, rsi_score = self._analyze_rsi(df)
        signals['RSI'] = rsi_signal
        scores.append(rsi_score * self.weights['rsi'])

        # 3. MACD信号
        macd_signal, macd_score = self._analyze_macd(df)
        signals['MACD'] = macd_signal
        scores.append(macd_score * self.weights['macd'])

        # 4. 布林带信号
        bb_signal, bb_score = self._analyze_bollinger(df)
        signals['布林带'] = bb_signal
        scores.append(bb_score * self.weights['bollinger'])

        # 5. 趋势信号
        trend_signal, trend_score = self._analyze_trend(df)
        signals['趋势'] = trend_signal
        scores.append(trend_score * self.weights['trend'])

        # 6. 成交量信号
        volume_signal, volume_score = self._analyze_volume(df)
        signals['成交量'] = volume_signal
        scores.append(volume_score * self.weights['volume'])

        # 7. 溢价率信号（如果有）
        if premium_rate is not None:
            premium_signal, premium_score = self._analyze_premium(premium_rate)
            signals['溢价率'] = premium_signal
            scores.append(premium_score * self.weights['premium'])

        # 计算综合得分 (-100 到 +100)
        total_weight = sum(self.weights.values())
        if premium_rate is None:
            total_weight -= self.weights['premium']

        final_score = sum(scores) / total_weight

        # 生成建议
        signal_type, confidence = self._get_signal_type(final_score)
        reasons = self._generate_reasons(signals, df, premium_rate)
        risk_level = self._assess_risk(df)

        # 计算目标价位和止损位
        current_price = df['收盘'].iloc[-1]
        price_target, stop_loss = self._calculate_price_levels(
            current_price, signal_type, df
        )

        return TradingSignal(
            signal_type=signal_type,
            confidence=confidence,
            reasons=reasons,
            indicators={k: v.value for k, v in signals.items()},
            risk_level=risk_level,
            price_target=price_target,
            stop_loss=stop_loss
        )

    def _analyze_ma_cross(self, df: pd.DataFrame) -> tuple[IndicatorSignal, float]:
        """分析均线交叉"""
        if 'MA5' not in df.columns or 'MA20' not in df.columns:
            return IndicatorSignal.NEUTRAL, 0

        ma5 = df['MA5'].iloc[-1]
        ma20 = df['MA20'].iloc[-1]
        ma5_prev = df['MA5'].iloc[-2] if len(df) > 1 else ma5
        ma20_prev = df['MA20'].iloc[-2] if len(df) > 1 else ma20

        # 金叉：短期均线上穿长期均线
        if ma5_prev <= ma20_prev and ma5 > ma20:
            return IndicatorSignal.BULLISH, 1.0

        # 死叉：短期均线下穿长期均线
        if ma5_prev >= ma20_prev and ma5 < ma20:
            return IndicatorSignal.BEARISH, -1.0

        # 多头排列
        if ma5 > ma20:
            return IndicatorSignal.BULLISH, 0.5

        # 空头排列
        if ma5 < ma20:
            return IndicatorSignal.BEARISH, -0.5

        return IndicatorSignal.NEUTRAL, 0

    def _analyze_rsi(self, df: pd.DataFrame) -> tuple[IndicatorSignal, float]:
        """分析RSI"""
        if 'RSI' not in df.columns:
            return IndicatorSignal.NEUTRAL, 0

        rsi = df['RSI'].iloc[-1]

        if pd.isna(rsi):
            return IndicatorSignal.NEUTRAL, 0

        # 超卖区域 (< 30)
        if rsi < 30:
            return IndicatorSignal.BULLISH, 0.8

        # 严重超卖 (< 20)
        if rsi < 20:
            return IndicatorSignal.BULLISH, 1.0

        # 超买区域 (> 70)
        if rsi > 70:
            return IndicatorSignal.BEARISH, -0.8

        # 严重超买 (> 80)
        if rsi > 80:
            return IndicatorSignal.BEARISH, -1.0

        # 中性区域
        if 40 <= rsi <= 60:
            return IndicatorSignal.NEUTRAL, 0

        # 偏多
        if 30 <= rsi < 40:
            return IndicatorSignal.BULLISH, 0.3

        # 偏空
        if 60 < rsi <= 70:
            return IndicatorSignal.BEARISH, -0.3

        return IndicatorSignal.NEUTRAL, 0

    def _analyze_macd(self, df: pd.DataFrame) -> tuple[IndicatorSignal, float]:
        """分析MACD"""
        if 'MACD' not in df.columns or 'Signal' not in df.columns:
            return IndicatorSignal.NEUTRAL, 0

        macd = df['MACD'].iloc[-1]
        signal = df['Signal'].iloc[-1]
        histogram = df['Histogram'].iloc[-1] if 'Histogram' in df.columns else macd - signal

        macd_prev = df['MACD'].iloc[-2] if len(df) > 1 else macd
        signal_prev = df['Signal'].iloc[-2] if len(df) > 1 else signal

        # 金叉：MACD上穿信号线
        if macd_prev <= signal_prev and macd > signal:
            return IndicatorSignal.BULLISH, 1.0

        # 死叉：MACD下穿信号线
        if macd_prev >= signal_prev and macd < signal:
            return IndicatorSignal.BEARISH, -1.0

        # MACD在零轴上方且柱状图为正
        if macd > 0 and histogram > 0:
            return IndicatorSignal.BULLISH, 0.6

        # MACD在零轴下方且柱状图为负
        if macd < 0 and histogram < 0:
            return IndicatorSignal.BEARISH, -0.6

        return IndicatorSignal.NEUTRAL, 0

    def _analyze_bollinger(self, df: pd.DataFrame) -> tuple[IndicatorSignal, float]:
        """分析布林带"""
        if 'BB_Upper' not in df.columns or 'BB_Lower' not in df.columns:
            return IndicatorSignal.NEUTRAL, 0

        price = df['收盘'].iloc[-1]
        bb_upper = df['BB_Upper'].iloc[-1]
        bb_lower = df['BB_Lower'].iloc[-1]
        bb_middle = df['BB_Middle'].iloc[-1] if 'BB_Middle' in df.columns else (bb_upper + bb_lower) / 2

        # 价格突破下轨（超卖）
        if price <= bb_lower:
            return IndicatorSignal.BULLISH, 0.8

        # 价格突破上轨（超买）
        if price >= bb_upper:
            return IndicatorSignal.BEARISH, -0.8

        # 价格在中轨下方
        if price < bb_middle:
            return IndicatorSignal.BULLISH, 0.3

        # 价格在中轨上方
        if price > bb_middle:
            return IndicatorSignal.BEARISH, -0.3

        return IndicatorSignal.NEUTRAL, 0

    def _analyze_trend(self, df: pd.DataFrame) -> tuple[IndicatorSignal, float]:
        """分析趋势"""
        # 使用最近20天的价格判断趋势
        recent_days = min(20, len(df))
        prices = df['收盘'].tail(recent_days).values

        # 计算线性回归斜率
        import numpy as np
        x = np.arange(recent_days)
        slope = np.polyfit(x, prices, 1)[0]

        # 计算涨跌幅
        price_change_pct = (prices[-1] - prices[0]) / prices[0] * 100

        # 强上升趋势
        if slope > 0 and price_change_pct > 5:
            return IndicatorSignal.BULLISH, 0.8

        # 上升趋势
        if slope > 0 and price_change_pct > 0:
            return IndicatorSignal.BULLISH, 0.5

        # 强下降趋势
        if slope < 0 and price_change_pct < -5:
            return IndicatorSignal.BEARISH, -0.8

        # 下降趋势
        if slope < 0 and price_change_pct < 0:
            return IndicatorSignal.BEARISH, -0.5

        return IndicatorSignal.NEUTRAL, 0

    def _analyze_volume(self, df: pd.DataFrame) -> tuple[IndicatorSignal, float]:
        """分析成交量"""
        if '成交量' not in df.columns:
            return IndicatorSignal.NEUTRAL, 0

        recent_volume = df['成交量'].tail(5).mean()
        avg_volume = df['成交量'].mean()

        if recent_volume == 0 or avg_volume == 0:
            return IndicatorSignal.NEUTRAL, 0

        volume_ratio = recent_volume / avg_volume

        price_change = df['收盘'].iloc[-1] - df['收盘'].iloc[-2] if len(df) > 1 else 0

        # 放量上涨
        if volume_ratio > 1.5 and price_change > 0:
            return IndicatorSignal.BULLISH, 0.7

        # 放量下跌
        if volume_ratio > 1.5 and price_change < 0:
            return IndicatorSignal.BEARISH, -0.7

        # 缩量上涨（可能后续乏力）
        if volume_ratio < 0.7 and price_change > 0:
            return IndicatorSignal.NEUTRAL, 0.2

        return IndicatorSignal.NEUTRAL, 0

    def _analyze_premium(self, premium_rate: float) -> tuple[IndicatorSignal, float]:
        """分析溢价率"""
        # 高折价（可能低估）
        if premium_rate < -3:
            return IndicatorSignal.BULLISH, 0.8

        # 折价
        if premium_rate < -1:
            return IndicatorSignal.BULLISH, 0.5

        # 高溢价（可能高估）
        if premium_rate > 3:
            return IndicatorSignal.BEARISH, -0.8

        # 溢价
        if premium_rate > 1:
            return IndicatorSignal.BEARISH, -0.5

        # 正常范围
        return IndicatorSignal.NEUTRAL, 0

    def _get_signal_type(self, score: float) -> tuple[SignalType, float]:
        """根据得分获取信号类型"""
        confidence = abs(score)

        if score >= 0.6:
            return SignalType.STRONG_BUY, min(confidence * 100, 95)
        elif score >= 0.2:
            return SignalType.BUY, min(confidence * 100, 80)
        elif score <= -0.6:
            return SignalType.STRONG_SELL, min(confidence * 100, 95)
        elif score <= -0.2:
            return SignalType.SELL, min(confidence * 100, 80)
        else:
            return SignalType.HOLD, 50

    def _generate_reasons(
        self,
        signals: Dict[str, IndicatorSignal],
        df: pd.DataFrame,
        premium_rate: Optional[float]
    ) -> List[str]:
        """生成建议原因"""
        reasons = []

        # 均线信号
        if signals.get('均线') == IndicatorSignal.BULLISH:
            if 'MA5' in df.columns and 'MA20' in df.columns:
                ma5 = df['MA5'].iloc[-1]
                ma20 = df['MA20'].iloc[-1]
                if df['MA5'].iloc[-2] <= df['MA20'].iloc[-2] and ma5 > ma20:
                    reasons.append("✓ 短期均线金叉，买入信号")
                else:
                    reasons.append("✓ 短期均线在长期均线上方，多头排列")
        elif signals.get('均线') == IndicatorSignal.BEARISH:
            reasons.append("✗ 短期均线在长期均线下方，空头排列")

        # RSI信号
        if signals.get('RSI') == IndicatorSignal.BULLISH:
            rsi = df['RSI'].iloc[-1] if 'RSI' in df.columns else None
            if rsi and rsi < 30:
                reasons.append(f"✓ RSI={rsi:.1f}，处于超卖区域")
        elif signals.get('RSI') == IndicatorSignal.BEARISH:
            rsi = df['RSI'].iloc[-1] if 'RSI' in df.columns else None
            if rsi and rsi > 70:
                reasons.append(f"✗ RSI={rsi:.1f}，处于超买区域")

        # MACD信号
        if signals.get('MACD') == IndicatorSignal.BULLISH:
            if 'MACD' in df.columns and 'Signal' in df.columns:
                if df['MACD'].iloc[-2] <= df['Signal'].iloc[-2] and df['MACD'].iloc[-1] > df['Signal'].iloc[-1]:
                    reasons.append("✓ MACD金叉，动能转强")
                else:
                    reasons.append("✓ MACD处于多头状态")
        elif signals.get('MACD') == IndicatorSignal.BEARISH:
            reasons.append("✗ MACD处于空头状态")

        # 趋势信号
        if signals.get('趋势') == IndicatorSignal.BULLISH:
            recent_change = (df['收盘'].iloc[-1] - df['收盘'].iloc[-20]) / df['收盘'].iloc[-20] * 100 if len(df) >= 20 else 0
            if recent_change > 5:
                reasons.append(f"✓ 近期上涨{recent_change:.1f}%，强势上升趋势")
            else:
                reasons.append("✓ 处于上升趋势")
        elif signals.get('趋势') == IndicatorSignal.BEARISH:
            reasons.append("✗ 处于下降趋势")

        # 溢价率信号
        if premium_rate is not None:
            if signals.get('溢价率') == IndicatorSignal.BULLISH:
                reasons.append(f"✓ 折价{abs(premium_rate):.2f}%，价格可能被低估")
            elif signals.get('溢价率') == IndicatorSignal.BEARISH:
                reasons.append(f"✗ 溢价{premium_rate:.2f}%，价格可能被高估")

        if not reasons:
            reasons.append("• 各项指标处于中性区域，建议观望")

        return reasons

    def _assess_risk(self, df: pd.DataFrame) -> str:
        """评估风险等级"""
        # 计算波动率
        returns = df['收盘'].pct_change().dropna()
        if len(returns) == 0:
            return "中"

        import numpy as np
        volatility = returns.std() * np.sqrt(252) * 100

        if volatility > 30:
            return "高"
        elif volatility > 20:
            return "中"
        else:
            return "低"

    def _calculate_price_levels(
        self,
        current_price: float,
        signal_type: SignalType,
        df: pd.DataFrame
    ) -> tuple[Optional[float], Optional[float]]:
        """计算目标价位和止损位"""
        # 计算ATR (平均真实波幅)
        if len(df) < 14:
            return None, None

        high = df['最高'].tail(14)
        low = df['最低'].tail(14)
        close = df['收盘'].tail(14)

        import numpy as np
        tr = np.maximum(high - low, np.abs(high - close.shift(1)))
        tr = np.maximum(tr, np.abs(low - close.shift(1)))
        atr = tr.mean()

        if signal_type in [SignalType.STRONG_BUY, SignalType.BUY]:
            # 买入建议：目标价 = 当前价 + 2*ATR，止损 = 当前价 - ATR
            price_target = current_price + 2 * atr
            stop_loss = current_price - atr
        elif signal_type in [SignalType.STRONG_SELL, SignalType.SELL]:
            # 卖出建议：目标价 = 当前价 - 2*ATR，止损 = 当前价 + ATR
            price_target = current_price - 2 * atr
            stop_loss = current_price + atr
        else:
            return None, None

        return round(price_target, 3), round(stop_loss, 3)
