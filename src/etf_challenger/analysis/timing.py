"""时机分析器（Layer 3）

4个独立信号通道，权重根据市场状态自适应调整。
"""

import numpy as np
import pandas as pd
from typing import Optional

from ..models.decision import (
    MarketRegime, RegimeType, TimingResult, ChannelSignal,
)


# 状态自适应权重表
REGIME_WEIGHTS = {
    RegimeType.TRENDING_UP:   {"trend": 50, "mean_rev": 5,  "vol_price": 25, "premium": 20},
    RegimeType.TRENDING_DOWN: {"trend": 50, "mean_rev": 5,  "vol_price": 25, "premium": 20},
    RegimeType.RANGING:       {"trend": 10, "mean_rev": 45, "vol_price": 20, "premium": 25},
    RegimeType.CRISIS:        {"trend": 15, "mean_rev": 15, "vol_price": 20, "premium": 50},
}


class TimingAnalyzer:
    """时机分析器"""

    def analyze(
        self,
        df: pd.DataFrame,
        regime: MarketRegime,
        premium_rate: Optional[float] = None,
        premium_history: Optional[list] = None,
    ) -> TimingResult:
        """
        分析买入/卖出时机

        Args:
            df: 包含技术指标的历史数据
            regime: 当前市场状态
            premium_rate: 当前溢价率（%）
            premium_history: 溢价率历史列表（用于z-score）

        Returns:
            TimingResult
        """
        weights = REGIME_WEIGHTS[regime.regime]

        channels = []

        # 通道1：趋势复合信号
        trend_score, trend_detail = self._trend_composite(df)
        channels.append(ChannelSignal(
            name="趋势", score=trend_score,
            weight=weights["trend"], detail=trend_detail,
        ))

        # 通道2：均值回归
        mr_score, mr_detail = self._mean_reversion(df, premium_rate, premium_history)
        channels.append(ChannelSignal(
            name="均值回归", score=mr_score,
            weight=weights["mean_rev"], detail=mr_detail,
        ))

        # 通道3：量价关系
        vp_score, vp_detail = self._volume_price(df)
        channels.append(ChannelSignal(
            name="量价", score=vp_score,
            weight=weights["vol_price"], detail=vp_detail,
        ))

        # 通道4：溢价/折价
        pm_score, pm_detail = self._premium_channel(premium_rate, premium_history)
        channels.append(ChannelSignal(
            name="溢折价", score=pm_score,
            weight=weights["premium"], detail=pm_detail,
        ))

        # 加权合成
        total_weight = sum(ch.weight for ch in channels)
        composite = sum(ch.score * ch.weight for ch in channels) / total_weight if total_weight > 0 else 0
        composite = max(-1, min(1, composite))

        # 置信度 = |composite| * 100，但考虑通道一致性
        agreement = self._channel_agreement(channels)
        confidence = min(100, abs(composite) * 80 + agreement * 20)

        action = self._score_to_action(composite)
        narrative = self._build_narrative(channels, composite, action, regime)

        return TimingResult(
            composite_score=round(composite, 3),
            confidence=round(confidence, 1),
            action=action,
            channels=channels,
            narrative=narrative,
        )

    # ---- 通道实现 ----

    def _trend_composite(self, df: pd.DataFrame) -> tuple:
        """
        趋势复合信号：MA20/MA60关系 + MACD柱状图方向 + 20日线性回归斜率
        输出 -1 到 +1
        """
        scores = []

        # MA20/MA60 关系
        if 'MA20' in df.columns and 'MA60' in df.columns:
            ma20 = df['MA20'].iloc[-1]
            ma60 = df['MA60'].iloc[-1]
            if not pd.isna(ma20) and not pd.isna(ma60) and ma60 > 0:
                ma_ratio = (ma20 - ma60) / ma60
                # 将偏离映射到 -1 到 +1（±5%饱和）
                ma_score = max(-1, min(1, ma_ratio / 0.05))
                scores.append(ma_score)

        # MACD柱状图方向
        if 'Histogram' in df.columns:
            hist = df['Histogram'].tail(5).dropna()
            if len(hist) >= 2:
                # 柱状图趋势（斜率方向）
                hist_diff = hist.iloc[-1] - hist.iloc[-2]
                price = df['收盘'].iloc[-1]
                if price > 0:
                    # 归一化
                    norm_diff = hist_diff / price * 100
                    macd_score = max(-1, min(1, norm_diff * 10))
                    scores.append(macd_score)

        # 20日线性回归斜率
        recent_days = min(20, len(df))
        if recent_days >= 5:
            prices = df['收盘'].tail(recent_days).values
            x = np.arange(recent_days)
            slope = np.polyfit(x, prices, 1)[0]
            avg_price = prices.mean()
            if avg_price > 0:
                # 日涨幅标准化
                daily_pct = slope / avg_price * 100
                slope_score = max(-1, min(1, daily_pct * 5))
                scores.append(slope_score)

        if not scores:
            return 0, "趋势数据不足"

        composite = sum(scores) / len(scores)
        composite = max(-1, min(1, composite))

        if composite > 0.3:
            detail = f"趋势偏多（MA/MACD/斜率综合 {composite:+.2f}）"
        elif composite < -0.3:
            detail = f"趋势偏空（MA/MACD/斜率综合 {composite:+.2f}）"
        else:
            detail = f"趋势中性（综合 {composite:+.2f}）"

        return round(composite, 3), detail

    def _mean_reversion(
        self,
        df: pd.DataFrame,
        premium_rate: Optional[float],
        premium_history: Optional[list],
    ) -> tuple:
        """
        均值回归信号：价格在60日范围的百分位 + 溢折价z-score
        输出 -1 到 +1（负值=超卖=买入机会）
        """
        scores = []

        # 价格百分位
        window = min(60, len(df))
        if window >= 10:
            recent = df['收盘'].tail(window)
            current = recent.iloc[-1]
            pct = (current - recent.min()) / (recent.max() - recent.min()) if recent.max() != recent.min() else 0.5
            # 50%百分位=中性，0%=超卖(买入)，100%=超买(卖出)
            # 映射：0→+1（买），0.5→0，1→-1（卖）
            price_score = 1 - 2 * pct
            scores.append(price_score)

        # 溢折价z-score
        if premium_history and len(premium_history) >= 5:
            rates = [p.premium_rate for p in premium_history]
            mean_rate = np.mean(rates)
            std_rate = np.std(rates)
            if std_rate > 0 and premium_rate is not None:
                z = (premium_rate - mean_rate) / std_rate
                # z>0 溢价偏高=卖出, z<0 折价偏多=买入
                prem_score = max(-1, min(1, -z / 2))
                scores.append(prem_score)

        if not scores:
            return 0, "均值回归数据不足"

        composite = sum(scores) / len(scores)
        composite = max(-1, min(1, composite))

        if composite > 0.3:
            detail = f"价格偏低，有回归上涨空间（{composite:+.2f}）"
        elif composite < -0.3:
            detail = f"价格偏高，有回归下跌风险（{composite:+.2f}）"
        else:
            detail = f"价格处于均值附近（{composite:+.2f}）"

        return round(composite, 3), detail

    def _volume_price(self, df: pd.DataFrame) -> tuple:
        """
        量价关系：成交量比率 × 价格方向 + 趋势确认
        输出 -1 到 +1
        """
        if '成交量' not in df.columns or len(df) < 10:
            return 0, "成交量数据不足"

        # 近5日均量 vs 20日均量
        vol_5 = df['成交量'].tail(5).mean()
        vol_20 = df['成交量'].tail(20).mean()

        if vol_20 == 0:
            return 0, "成交量为零"

        vol_ratio = vol_5 / vol_20

        # 近5日价格变化方向
        price_5d = df['收盘'].tail(5)
        price_change = (price_5d.iloc[-1] - price_5d.iloc[0]) / price_5d.iloc[0] if price_5d.iloc[0] > 0 else 0

        # 量价配合
        if vol_ratio > 1.2 and price_change > 0:
            # 放量上涨
            score = min(1, vol_ratio - 1 + abs(price_change) * 5)
            detail = f"放量上涨（量比{vol_ratio:.2f}，涨{price_change*100:.1f}%）"
        elif vol_ratio > 1.2 and price_change < 0:
            # 放量下跌
            score = max(-1, -(vol_ratio - 1 + abs(price_change) * 5))
            detail = f"放量下跌（量比{vol_ratio:.2f}，跌{abs(price_change)*100:.1f}%）"
        elif vol_ratio < 0.7 and price_change > 0:
            # 缩量上涨（弱）
            score = 0.15
            detail = f"缩量上涨，动能不足（量比{vol_ratio:.2f}）"
        elif vol_ratio < 0.7 and price_change < 0:
            # 缩量下跌（抛压减少，可能见底）
            score = 0.2
            detail = f"缩量下跌，抛压减轻（量比{vol_ratio:.2f}）"
        else:
            score = 0
            detail = f"量价关系中性（量比{vol_ratio:.2f}）"

        return round(max(-1, min(1, score)), 3), detail

    def _premium_channel(
        self,
        premium_rate: Optional[float],
        premium_history: Optional[list],
    ) -> tuple:
        """
        溢折价通道：当前溢折价绝对值 + 历史z-score
        输出 -1 到 +1
        """
        if premium_rate is None:
            return 0, "无溢折价数据"

        scores = []

        # 绝对水平信号
        if premium_rate < -3:
            scores.append(0.9)
        elif premium_rate < -1:
            scores.append(0.5)
        elif premium_rate > 3:
            scores.append(-0.9)
        elif premium_rate > 1:
            scores.append(-0.5)
        else:
            scores.append(0)

        # 历史z-score
        if premium_history and len(premium_history) >= 5:
            rates = [p.premium_rate for p in premium_history]
            mean_r = np.mean(rates)
            std_r = np.std(rates)
            if std_r > 0:
                z = (premium_rate - mean_r) / std_r
                z_score_signal = max(-1, min(1, -z / 2))
                scores.append(z_score_signal)

        composite = sum(scores) / len(scores) if scores else 0
        composite = max(-1, min(1, composite))

        if premium_rate < -1:
            detail = f"折价{abs(premium_rate):.2f}%，价格可能被低估"
        elif premium_rate > 1:
            detail = f"溢价{premium_rate:.2f}%，价格可能被高估"
        else:
            detail = f"溢折价{premium_rate:+.2f}%，处于正常范围"

        return round(composite, 3), detail

    # ---- 辅助方法 ----

    @staticmethod
    def _channel_agreement(channels: list) -> float:
        """计算通道一致性（0-1）"""
        if not channels:
            return 0
        signs = [1 if ch.score > 0.1 else (-1 if ch.score < -0.1 else 0) for ch in channels]
        non_zero = [s for s in signs if s != 0]
        if not non_zero:
            return 0
        agreement = abs(sum(non_zero)) / len(non_zero)
        return agreement

    @staticmethod
    def _score_to_action(composite: float) -> str:
        if composite >= 0.2:
            return "买入"
        elif composite <= -0.2:
            return "卖出"
        else:
            return "持有"

    @staticmethod
    def _build_narrative(channels, composite, action, regime) -> str:
        parts = []

        for ch in channels:
            direction = "看涨" if ch.score > 0.1 else ("看跌" if ch.score < -0.1 else "中性")
            parts.append(f"{ch.name}信号{direction}（权重{ch.weight:.0f}%）")

        summary = "，".join(parts)
        summary += f"。综合建议{action}，置信度{abs(composite)*100:.0f}%。"

        return summary
