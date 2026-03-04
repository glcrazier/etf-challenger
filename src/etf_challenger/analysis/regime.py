"""市场状态检测器（Layer 1）

通过沪深300指数判断当前市场状态：危机、上升趋势、下降趋势、震荡。
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta

from ..models.decision import MarketRegime, RegimeType
from .analyzer import ETFAnalyzer


class RegimeDetector:
    """市场状态检测器"""

    # 沪深300指数代码
    BENCHMARK_INDEX = "000300"
    # 需要的历史天数
    LOOKBACK_DAYS = 180  # 多取一些保证有120个交易日

    def __init__(self, data_service):
        self.data_service = data_service

    def detect(self) -> MarketRegime:
        """
        检测当前市场状态

        Returns:
            MarketRegime 包含状态类型和叙述
        """
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=self.LOOKBACK_DAYS)).strftime("%Y%m%d")

        df = self.data_service.get_index_historical_data(
            self.BENCHMARK_INDEX, start_date, end_date
        )

        if df is None or df.empty or len(df) < 30:
            return self._fallback_regime()

        # 计算技术指标
        df = ETFAnalyzer.calculate_moving_averages(df, windows=[20, 60])
        df = ETFAnalyzer.calculate_volatility(df, window=20)

        # 提取关键数值
        latest = df.iloc[-1]
        price = latest['收盘']
        ma20 = latest.get('MA20', price)
        ma60 = latest.get('MA60', price)

        # 20日波动率（已经是年化%）
        vol_20d = latest.get('20日波动率', 0)
        if pd.isna(vol_20d):
            vol_20d = 0

        # 长期波动率：全量计算
        returns = df['收盘'].pct_change().dropna()
        vol_long = returns.std() * np.sqrt(252) * 100 if len(returns) > 20 else vol_20d

        # 20日最大回撤
        recent_20 = df['收盘'].tail(20)
        peak = recent_20.expanding().max()
        drawdown_series = (recent_20 - peak) / peak * 100
        drawdown_20d = drawdown_series.min()

        # 价格相对MA60偏离
        price_vs_ma60 = ((price - ma60) / ma60 * 100) if ma60 > 0 and not pd.isna(ma60) else 0
        ma20_vs_ma60 = ((ma20 - ma60) / ma60 * 100) if ma60 > 0 and not pd.isna(ma20) and not pd.isna(ma60) else 0

        # 判断状态
        regime = self._classify(vol_20d, vol_long, drawdown_20d, price, ma20, ma60)

        # 生成叙述
        narrative = self._build_narrative(regime, price_vs_ma60, vol_20d, vol_long, drawdown_20d)

        return MarketRegime(
            regime=regime,
            volatility_20d=round(vol_20d, 2),
            volatility_long=round(vol_long, 2),
            drawdown_20d=round(drawdown_20d, 2),
            price_vs_ma60=round(price_vs_ma60, 2),
            ma20_vs_ma60=round(ma20_vs_ma60, 2),
            narrative=narrative,
        )

    def _classify(
        self,
        vol_20d: float,
        vol_long: float,
        drawdown_20d: float,
        price: float,
        ma20: float,
        ma60: float,
    ) -> RegimeType:
        """根据指标判断市场状态"""
        # 危机：波动率飙升 或 短期大幅回撤
        if (vol_long > 0 and vol_20d > 2 * vol_long) or drawdown_20d < -10:
            return RegimeType.CRISIS

        ma20_valid = not pd.isna(ma20)
        ma60_valid = not pd.isna(ma60)

        if ma20_valid and ma60_valid:
            # 上升趋势：价格 > MA60 且 MA20 > MA60
            if price > ma60 and ma20 > ma60:
                return RegimeType.TRENDING_UP

            # 下降趋势：价格 < MA60 且 MA20 < MA60
            if price < ma60 and ma20 < ma60:
                return RegimeType.TRENDING_DOWN

        return RegimeType.RANGING

    def _build_narrative(
        self,
        regime: RegimeType,
        price_vs_ma60: float,
        vol_20d: float,
        vol_long: float,
        drawdown_20d: float,
    ) -> str:
        """生成市场状态叙述"""
        parts = []

        # 状态描述
        regime_desc = {
            RegimeType.CRISIS: "市场处于危机模式",
            RegimeType.TRENDING_UP: "沪深300处于上升趋势",
            RegimeType.TRENDING_DOWN: "沪深300处于下降趋势",
            RegimeType.RANGING: "沪深300处于震荡整理",
        }
        desc = regime_desc[regime]

        # 补充数据
        if abs(price_vs_ma60) > 0.1:
            direction = "上方" if price_vs_ma60 > 0 else "下方"
            desc += f"（价格在60日均线{direction}{abs(price_vs_ma60):.1f}%）"

        parts.append(desc)

        # 波动率描述
        if vol_20d > 0:
            vol_desc = f"20日年化波动率{vol_20d:.1f}%"
            if vol_long > 0 and vol_20d > 1.5 * vol_long:
                vol_desc += "，显著高于长期均值"
            elif vol_long > 0 and vol_20d < 0.7 * vol_long:
                vol_desc += "，低于长期均值"
            else:
                vol_desc += "，处于正常水平"
            parts.append(vol_desc)

        # 回撤描述
        if drawdown_20d < -5:
            parts.append(f"近20日最大回撤{drawdown_20d:.1f}%，注意风险")

        # 策略建议
        strategy = {
            RegimeType.CRISIS: "建议防御为主，关注折价机会",
            RegimeType.TRENDING_UP: "趋势跟随策略更可靠",
            RegimeType.TRENDING_DOWN: "谨慎操作，注意控制仓位",
            RegimeType.RANGING: "均值回归策略更适合",
        }
        parts.append(strategy[regime])

        return "。".join(parts) + "。"

    def _fallback_regime(self) -> MarketRegime:
        """无法获取数据时的回退结果"""
        return MarketRegime(
            regime=RegimeType.RANGING,
            volatility_20d=0,
            volatility_long=0,
            drawdown_20d=0,
            price_vs_ma60=0,
            ma20_vs_ma60=0,
            narrative="无法获取沪深300数据，默认按震荡市场处理。",
        )
