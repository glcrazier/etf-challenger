"""债券ETF分析模块"""

import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from enum import Enum

from .advisor import SignalType, IndicatorSignal, TradingSignal


# 债券品种 → (久期类型, 典型期限, 利率敏感性, 说明)
BOND_TYPE_META = {
    '可转债':  ('中期',  '3-5年',  '中',  '受正股价格影响较大，兼具股债特性'),
    '30年国债': ('超长期', '30年',   '极高', '对利率变动极度敏感，波动远大于短债'),
    '10年国债': ('长期',  '10年',  '高',  '利率基准品种，对货币政策敏感'),
    '5年国债':  ('中期',  '5年',   '中高', '中等利率敏感性，流动性较好'),
    '国开债':  ('中长期', '5-10年', '中高', '政策性银行债，信用风险极低'),
    '政金债':  ('中长期', '3-7年',  '中',  '政策性金融债，收益率略高于国债'),
    '城投债':  ('中期',  '3-5年',  '中',  '地方政府融资平台债，信用风险需关注'),
    '地方债':  ('中长期', '5-10年', '中高', '省级地方政府债，信用风险低'),
    '短债':    ('短期',  '1-3年',  '低',  '短久期，对利率不敏感，波动极小'),
    '信用债':  ('中期',  '3-5年',  '中',  '企业/公司债，需关注信用利差变化'),
    '科创债':  ('中期',  '3-5年',  '中',  '科创板企业债，信用风险略高于普通信用债'),
    '国债':    ('中长期', '5-10年', '中高', '主权信用，无信用风险，对利率敏感'),
}

# 利率敏感性 → 利率上升时的影响描述
RATE_RISE_IMPACT = {
    '极高': '利率每上升100bps，价格约下跌15-20%',
    '高':   '利率每上升100bps，价格约下跌8-12%',
    '中高': '利率每上升100bps，价格约下跌5-8%',
    '中':   '利率每上升100bps，价格约下跌3-5%',
    '低':   '利率变动对价格影响有限（<3%）',
}


@dataclass
class BondAnalysis:
    """债券ETF分析结果"""
    code: str
    name: str
    bond_type: str
    duration_category: str     # 短期/中期/长期/超长期
    typical_maturity: str      # 典型期限
    rate_sensitivity: str      # 低/中/中高/高/极高
    bond_description: str      # 品种说明

    # 价格与收益
    current_price: float
    change_pct: float
    estimated_yield: float     # 年化价格收益率（近似当前持有收益）
    total_return: float        # 区间总收益率
    annual_return: float       # 区间年化收益率

    # 风险指标
    volatility: float          # 年化波动率
    max_drawdown: float        # 最大回撤
    sharpe_ratio: float        # 夏普比率
    risk_level: str            # 低/中/高（债券标准）

    # 溢价
    premium_rate: Optional[float]

    # 交易信号
    signal: TradingSignal
    indicators: Dict[str, str]  # 各项指标状态


class BondAdvisor:
    """债券ETF交易建议分析器（使用债券特定参数）"""

    # 债券RSI阈值（比股票更紧，债券波动小）
    RSI_OVERSOLD = 40
    RSI_OVERBOUGHT = 60
    RSI_EXTREME_OVERSOLD = 30
    RSI_EXTREME_OVERBOUGHT = 70

    # 趋势判断阈值（20天涨跌幅，债券用更小的值）
    TREND_STRONG_UP = 2.0    # 强上升
    TREND_UP = 0.5           # 上升
    TREND_STRONG_DOWN = -2.0 # 强下降
    TREND_DOWN = -0.5        # 下降

    # 债券年化波动率风险等级（股票用30%/20%，债券用8%/3%）
    VOL_HIGH = 8.0
    VOL_MEDIUM = 3.0

    def detect_bond_type(self, etf_name: str) -> str:
        """从ETF名称推断债券品种"""
        priority_patterns = [
            ('可转债', ['可转债', '转债']),
            ('30年国债', ['30年国债', '国债30年', '三十年国债']),
            ('10年国债', ['10年国债', '十年国债']),
            ('5年国债', ['5年国债', '五年国债']),
            ('国开债', ['国开债', '国开行', '国开ETF']),
            ('政金债', ['政金债', '政策性金融债']),
            ('城投债', ['城投债', '城投']),
            ('地方债', ['地债', '地方债']),
            ('短债', ['短债', '短期债', '短融']),
            ('信用债', ['信用债', '企业债', '公司债']),
            ('科创债', ['科创债']),
            ('国债', ['国债']),
        ]
        for bond_type, patterns in priority_patterns:
            for pat in patterns:
                if pat in etf_name:
                    return bond_type
        return '债券'

    def get_bond_meta(self, bond_type: str) -> Tuple[str, str, str, str]:
        """获取债券元数据：(久期类型, 典型期限, 利率敏感性, 说明)"""
        meta = BOND_TYPE_META.get(bond_type)
        if meta:
            return meta
        return ('中期', '3-5年', '中', '债券ETF')

    def analyze(
        self,
        df: pd.DataFrame,
        code: str,
        name: str,
        current_price: float,
        change_pct: float,
        premium_rate: Optional[float] = None,
    ) -> BondAnalysis:
        """
        综合分析债券ETF

        Args:
            df: 历史K线数据（含收盘/最高/最低/成交量等列）
            code: ETF代码
            name: ETF名称
            current_price: 当前价格
            change_pct: 当日涨跌幅
            premium_rate: 溢价率（可选）

        Returns:
            BondAnalysis
        """
        bond_type = self.detect_bond_type(name)
        duration_cat, typical_maturity, rate_sensitivity, bond_desc = self.get_bond_meta(bond_type)

        # 性能指标
        perf = self._calc_performance(df)

        # 技术信号（债券调整参数）
        signal, indicators = self._generate_signal(df, premium_rate, bond_type)

        return BondAnalysis(
            code=code,
            name=name,
            bond_type=bond_type,
            duration_category=duration_cat,
            typical_maturity=typical_maturity,
            rate_sensitivity=rate_sensitivity,
            bond_description=bond_desc,
            current_price=current_price,
            change_pct=change_pct,
            estimated_yield=perf['年化收益率(%)'],
            total_return=perf['总收益率(%)'],
            annual_return=perf['年化收益率(%)'],
            volatility=perf['年化波动率(%)'],
            max_drawdown=perf['最大回撤(%)'],
            sharpe_ratio=perf['夏普比率'],
            risk_level=self._assess_risk(perf['年化波动率(%)']),
            premium_rate=premium_rate,
            signal=signal,
            indicators=indicators,
        )

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    def _calc_performance(self, df: pd.DataFrame) -> Dict[str, float]:
        col = '收盘'
        returns = df[col].pct_change().dropna()
        total_return = (df[col].iloc[-1] / df[col].iloc[0] - 1) * 100
        days = len(df)
        annual_return = ((1 + total_return / 100) ** (252 / max(days, 1)) - 1) * 100
        volatility = returns.std() * np.sqrt(252) * 100 if len(returns) > 1 else 0.0
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = drawdown.min() * 100 if len(drawdown) > 0 else 0.0
        risk_free = 0.015
        sharpe = (annual_return - risk_free * 100) / volatility if volatility > 0 else 0.0
        return {
            '总收益率(%)': round(total_return, 3),
            '年化收益率(%)': round(annual_return, 2),
            '年化波动率(%)': round(volatility, 2),
            '最大回撤(%)': round(max_drawdown, 2),
            '夏普比率': round(sharpe, 2),
        }

    def _assess_risk(self, volatility: float) -> str:
        if volatility > self.VOL_HIGH:
            return '高'
        elif volatility > self.VOL_MEDIUM:
            return '中'
        return '低'

    def _generate_signal(
        self,
        df: pd.DataFrame,
        premium_rate: Optional[float],
        bond_type: str,
    ) -> Tuple[TradingSignal, Dict[str, str]]:
        """生成债券调整后的综合交易信号"""
        # 债券专属权重：提升溢价率和趋势，降低成交量
        weights = {
            'trend':    25,
            'ma_cross': 20,
            'rsi':      15,
            'macd':     15,
            'bollinger': 10,
            'premium':  15,  # 债券溢价率更重要
        }

        scores = {}
        signals = {}

        trend_sig, trend_score = self._analyze_trend(df, bond_type)
        signals['趋势'] = trend_sig
        scores['trend'] = trend_score * weights['trend']

        ma_sig, ma_score = self._analyze_ma(df)
        signals['均线'] = ma_sig
        scores['ma_cross'] = ma_score * weights['ma_cross']

        rsi_sig, rsi_score = self._analyze_rsi(df)
        signals['RSI'] = rsi_sig
        scores['rsi'] = rsi_score * weights['rsi']

        macd_sig, macd_score = self._analyze_macd(df)
        signals['MACD'] = macd_sig
        scores['macd'] = macd_score * weights['macd']

        bb_sig, bb_score = self._analyze_bollinger(df)
        signals['布林带'] = bb_sig
        scores['bollinger'] = bb_score * weights['bollinger']

        total_weight = sum(weights[k] for k in scores)
        if premium_rate is not None:
            premium_sig, premium_score = self._analyze_premium(premium_rate)
            signals['溢价率'] = premium_sig
            scores['premium'] = premium_score * weights['premium']
            total_weight += weights['premium']

        final_score = sum(scores.values()) / total_weight if total_weight > 0 else 0

        signal_type, confidence = self._score_to_signal(final_score)
        reasons = self._build_reasons(signals, df, premium_rate)
        risk_level = self._assess_risk_from_df(df)

        current_price = df['收盘'].iloc[-1]
        entry_price, price_target, stop_loss = self._calc_price_levels(
            current_price, signal_type, df
        )

        trading_signal = TradingSignal(
            signal_type=signal_type,
            confidence=confidence,
            reasons=reasons,
            indicators={k: v.value for k, v in signals.items()},
            risk_level=risk_level,
            entry_price=entry_price,
            price_target=price_target,
            stop_loss=stop_loss,
        )

        indicator_summary = {k: v.value for k, v in signals.items()}
        return trading_signal, indicator_summary

    def _analyze_trend(self, df: pd.DataFrame, bond_type: str) -> Tuple[IndicatorSignal, float]:
        recent = min(20, len(df))
        prices = df['收盘'].tail(recent).values
        price_change_pct = (prices[-1] - prices[0]) / prices[0] * 100
        x = np.arange(recent)
        slope = np.polyfit(x, prices, 1)[0]

        if slope > 0 and price_change_pct >= self.TREND_STRONG_UP:
            return IndicatorSignal.BULLISH, 0.8
        if slope > 0 and price_change_pct >= self.TREND_UP:
            return IndicatorSignal.BULLISH, 0.4
        if slope < 0 and price_change_pct <= self.TREND_STRONG_DOWN:
            return IndicatorSignal.BEARISH, -0.8
        if slope < 0 and price_change_pct <= self.TREND_DOWN:
            return IndicatorSignal.BEARISH, -0.4
        return IndicatorSignal.NEUTRAL, 0

    def _analyze_ma(self, df: pd.DataFrame) -> Tuple[IndicatorSignal, float]:
        if 'MA5' not in df.columns or 'MA20' not in df.columns:
            return IndicatorSignal.NEUTRAL, 0
        ma5, ma20 = df['MA5'].iloc[-1], df['MA20'].iloc[-1]
        ma5_prev = df['MA5'].iloc[-2] if len(df) > 1 else ma5
        ma20_prev = df['MA20'].iloc[-2] if len(df) > 1 else ma20
        if ma5_prev <= ma20_prev and ma5 > ma20:
            return IndicatorSignal.BULLISH, 1.0
        if ma5_prev >= ma20_prev and ma5 < ma20:
            return IndicatorSignal.BEARISH, -1.0
        if ma5 > ma20:
            return IndicatorSignal.BULLISH, 0.4
        if ma5 < ma20:
            return IndicatorSignal.BEARISH, -0.4
        return IndicatorSignal.NEUTRAL, 0

    def _analyze_rsi(self, df: pd.DataFrame) -> Tuple[IndicatorSignal, float]:
        if 'RSI' not in df.columns:
            return IndicatorSignal.NEUTRAL, 0
        rsi = df['RSI'].iloc[-1]
        if pd.isna(rsi):
            return IndicatorSignal.NEUTRAL, 0
        # 债券 RSI 阈值：40/60（比股票 30/70 更紧）
        if rsi < self.RSI_EXTREME_OVERSOLD:
            return IndicatorSignal.BULLISH, 1.0
        if rsi < self.RSI_OVERSOLD:
            return IndicatorSignal.BULLISH, 0.6
        if rsi > self.RSI_EXTREME_OVERBOUGHT:
            return IndicatorSignal.BEARISH, -1.0
        if rsi > self.RSI_OVERBOUGHT:
            return IndicatorSignal.BEARISH, -0.6
        if 45 <= rsi <= 55:
            return IndicatorSignal.NEUTRAL, 0
        if rsi < 45:
            return IndicatorSignal.BULLISH, 0.2
        return IndicatorSignal.BEARISH, -0.2

    def _analyze_macd(self, df: pd.DataFrame) -> Tuple[IndicatorSignal, float]:
        if 'MACD' not in df.columns or 'Signal' not in df.columns:
            return IndicatorSignal.NEUTRAL, 0
        macd, signal = df['MACD'].iloc[-1], df['Signal'].iloc[-1]
        hist = df['Histogram'].iloc[-1] if 'Histogram' in df.columns else macd - signal
        macd_prev = df['MACD'].iloc[-2] if len(df) > 1 else macd
        sig_prev = df['Signal'].iloc[-2] if len(df) > 1 else signal
        if macd_prev <= sig_prev and macd > signal:
            return IndicatorSignal.BULLISH, 1.0
        if macd_prev >= sig_prev and macd < signal:
            return IndicatorSignal.BEARISH, -1.0
        if macd > 0 and hist > 0:
            return IndicatorSignal.BULLISH, 0.5
        if macd < 0 and hist < 0:
            return IndicatorSignal.BEARISH, -0.5
        return IndicatorSignal.NEUTRAL, 0

    def _analyze_bollinger(self, df: pd.DataFrame) -> Tuple[IndicatorSignal, float]:
        if 'BB_Upper' not in df.columns or 'BB_Lower' not in df.columns:
            return IndicatorSignal.NEUTRAL, 0
        price = df['收盘'].iloc[-1]
        upper, lower = df['BB_Upper'].iloc[-1], df['BB_Lower'].iloc[-1]
        mid = df['BB_Middle'].iloc[-1] if 'BB_Middle' in df.columns else (upper + lower) / 2
        if price <= lower:
            return IndicatorSignal.BULLISH, 0.8
        if price >= upper:
            return IndicatorSignal.BEARISH, -0.8
        if price < mid:
            return IndicatorSignal.BULLISH, 0.2
        if price > mid:
            return IndicatorSignal.BEARISH, -0.2
        return IndicatorSignal.NEUTRAL, 0

    def _analyze_premium(self, premium_rate: float) -> Tuple[IndicatorSignal, float]:
        # 债券ETF溢价率通常较小，±0.5% 就值得关注
        if premium_rate < -1.5:
            return IndicatorSignal.BULLISH, 0.9
        if premium_rate < -0.5:
            return IndicatorSignal.BULLISH, 0.5
        if premium_rate > 1.5:
            return IndicatorSignal.BEARISH, -0.9
        if premium_rate > 0.5:
            return IndicatorSignal.BEARISH, -0.5
        return IndicatorSignal.NEUTRAL, 0

    def _score_to_signal(self, score: float) -> Tuple[SignalType, float]:
        confidence = min(abs(score) * 100, 95)
        if score >= 0.55:
            return SignalType.STRONG_BUY, confidence
        if score >= 0.2:
            return SignalType.BUY, confidence
        if score <= -0.55:
            return SignalType.STRONG_SELL, confidence
        if score <= -0.2:
            return SignalType.SELL, confidence
        return SignalType.HOLD, 50.0

    def _assess_risk_from_df(self, df: pd.DataFrame) -> str:
        returns = df['收盘'].pct_change().dropna()
        if len(returns) == 0:
            return '低'
        vol = returns.std() * np.sqrt(252) * 100
        return self._assess_risk(vol)

    def _build_reasons(
        self,
        signals: Dict[str, IndicatorSignal],
        df: pd.DataFrame,
        premium_rate: Optional[float],
    ) -> List[str]:
        reasons = []

        if signals.get('趋势') == IndicatorSignal.BULLISH:
            recent = min(20, len(df))
            chg = (df['收盘'].iloc[-1] - df['收盘'].iloc[-recent]) / df['收盘'].iloc[-recent] * 100
            reasons.append(f"✓ 近{recent}日价格上涨{chg:.2f}%，处于上升趋势")
        elif signals.get('趋势') == IndicatorSignal.BEARISH:
            recent = min(20, len(df))
            chg = (df['收盘'].iloc[-1] - df['收盘'].iloc[-recent]) / df['收盘'].iloc[-recent] * 100
            reasons.append(f"✗ 近{recent}日价格下跌{abs(chg):.2f}%，处于下降趋势")

        if signals.get('均线') == IndicatorSignal.BULLISH:
            if len(df) > 1 and 'MA5' in df.columns and 'MA20' in df.columns:
                if df['MA5'].iloc[-2] <= df['MA20'].iloc[-2] and df['MA5'].iloc[-1] > df['MA20'].iloc[-1]:
                    reasons.append("✓ 短期均线金叉，动能转强")
                else:
                    reasons.append("✓ 均线多头排列")
        elif signals.get('均线') == IndicatorSignal.BEARISH:
            reasons.append("✗ 均线空头排列")

        if 'RSI' in df.columns:
            rsi = df['RSI'].iloc[-1]
            if not pd.isna(rsi):
                if signals.get('RSI') == IndicatorSignal.BULLISH:
                    reasons.append(f"✓ RSI={rsi:.1f}，处于偏低区间（债券超卖参考值<40）")
                elif signals.get('RSI') == IndicatorSignal.BEARISH:
                    reasons.append(f"✗ RSI={rsi:.1f}，处于偏高区间（债券超买参考值>60）")

        if signals.get('MACD') == IndicatorSignal.BULLISH:
            if len(df) > 1 and 'MACD' in df.columns and 'Signal' in df.columns:
                if df['MACD'].iloc[-2] <= df['Signal'].iloc[-2] and df['MACD'].iloc[-1] > df['Signal'].iloc[-1]:
                    reasons.append("✓ MACD金叉，买入信号")
                else:
                    reasons.append("✓ MACD处于多头状态")
        elif signals.get('MACD') == IndicatorSignal.BEARISH:
            reasons.append("✗ MACD处于空头状态")

        if premium_rate is not None:
            if signals.get('溢价率') == IndicatorSignal.BULLISH:
                reasons.append(f"✓ 折价{abs(premium_rate):.3f}%，低于净值，具有安全垫")
            elif signals.get('溢价率') == IndicatorSignal.BEARISH:
                reasons.append(f"✗ 溢价{premium_rate:.3f}%，高于净值，存在回归风险")
            else:
                reasons.append(f"• 溢价率{premium_rate:+.3f}%，接近公允价值")

        if not reasons:
            reasons.append("• 各项指标处于中性区域，建议观望")
        return reasons

    def _calc_price_levels(
        self,
        current_price: float,
        signal_type: SignalType,
        df: pd.DataFrame,
    ) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        if len(df) < 14:
            return None, None, None
        high = df['最高'].tail(14)
        low = df['最低'].tail(14)
        close_prev = df['收盘'].tail(14).shift(1)
        tr = pd.concat([
            high - low,
            (high - close_prev).abs(),
            (low - close_prev).abs(),
        ], axis=1).max(axis=1)
        atr = tr.mean()

        if signal_type in (SignalType.STRONG_BUY, SignalType.BUY):
            return (
                round(current_price, 4),
                round(current_price + 2 * atr, 4),
                round(current_price - atr, 4),
            )
        if signal_type == SignalType.HOLD:
            return (
                round(current_price - 0.5 * atr, 4),
                round(current_price + 1.5 * atr, 4),
                round(current_price - 1.2 * atr, 4),
            )
        return None, None, None
