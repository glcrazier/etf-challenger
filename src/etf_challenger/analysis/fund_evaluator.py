"""基金评估器（Layer 2）

从跟踪误差、费率、流动性、规模四个维度给ETF评级 A/B/C/D。
"""

import json
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Optional

from ..models.decision import FundGrade, FundGradeLevel, DimensionScore
from .screener import ETFScreener


class FundEvaluator:
    """ETF基金质量评估器"""

    # 沪深300作为默认基准指数
    DEFAULT_BENCHMARK = "000300"

    def __init__(self, data_service):
        self.data_service = data_service
        self.screener = ETFScreener()
        self._index_map = self._load_index_map()

    def _load_index_map(self) -> dict:
        """加载ETF→指数映射"""
        map_path = Path(__file__).resolve().parents[3] / "etf_index_map.json"
        if map_path.exists():
            with open(map_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                # 过滤掉注释键
                return {k: v for k, v in data.items() if not k.startswith("_")}
        return {}

    def evaluate(self, code: str, etf_df: pd.DataFrame, days: int = 60) -> FundGrade:
        """
        评估ETF质量

        Args:
            code: ETF代码
            etf_df: ETF历史数据DataFrame
            days: 分析天数

        Returns:
            FundGrade 评级结果
        """
        dimensions = []
        benchmark_note = ""

        # 1. 跟踪误差评分
        te_score, te_detail, te_value, b_note = self._score_tracking_error(code, etf_df, days)
        dimensions.append(DimensionScore(name="跟踪误差", score=te_score, detail=te_detail))
        if b_note:
            benchmark_note = b_note

        # 2. 费率评分
        fee_score, fee_detail, fee_value = self._score_expense_ratio(code, etf_df)
        dimensions.append(DimensionScore(name="费率", score=fee_score, detail=fee_detail))

        # 3. 流动性评分
        liq_score, liq_detail, liq_value = self._score_liquidity(etf_df)
        dimensions.append(DimensionScore(name="流动性", score=liq_score, detail=liq_detail))

        # 4. 规模评分
        scale_score, scale_detail, scale_value = self._score_fund_scale(code)
        dimensions.append(DimensionScore(name="规模", score=scale_score, detail=scale_detail))

        total = sum(d.score for d in dimensions)
        grade = self._total_to_grade(total)

        narrative = self._build_narrative(dimensions, grade, total, benchmark_note)

        return FundGrade(
            grade=grade,
            total_score=round(total, 1),
            dimensions=dimensions,
            tracking_error=te_value,
            expense_ratio=fee_value,
            avg_daily_amount=liq_value,
            fund_scale=scale_value,
            benchmark_note=benchmark_note,
            narrative=narrative,
        )

    # ---- 维度评分 ----

    def _score_tracking_error(self, code: str, etf_df: pd.DataFrame, days: int):
        """跟踪误差评分（0-25）"""
        index_code = self._index_map.get(code)
        benchmark_note = ""

        if not index_code:
            index_code = self.DEFAULT_BENCHMARK
            benchmark_note = f"该ETF未在索引映射中，使用沪深300(000300)作为基准"

        try:
            from datetime import datetime, timedelta
            end_date = datetime.now().strftime("%Y%m%d")
            start_date = (datetime.now() - timedelta(days=days + 30)).strftime("%Y%m%d")

            index_df = self.data_service.get_index_historical_data(index_code, start_date, end_date)

            if index_df is None or index_df.empty or len(index_df) < 10:
                return 15, "无法获取基准数据，给予中等评分", None, benchmark_note

            # 对齐日期计算跟踪误差
            etf_returns = etf_df.set_index('日期')['收盘'].pct_change().dropna()
            idx_returns = index_df.set_index('日期')['收盘'].pct_change().dropna()

            common_dates = etf_returns.index.intersection(idx_returns.index)
            if len(common_dates) < 10:
                return 15, "共同交易日不足，给予中等评分", None, benchmark_note

            diff = etf_returns.loc[common_dates] - idx_returns.loc[common_dates]
            tracking_error = diff.std() * np.sqrt(252) * 100  # 年化%

            # 评分
            if tracking_error < 1:
                score = 25
                level = "优秀"
            elif tracking_error < 2:
                score = 20
                level = "良好"
            elif tracking_error < 3:
                score = 12
                level = "一般"
            else:
                score = 5
                level = "较差"

            detail = f"年化跟踪误差{tracking_error:.2f}%（{level}）"
            return score, detail, round(tracking_error, 2), benchmark_note

        except Exception:
            return 15, "跟踪误差计算失败，给予中等评分", None, benchmark_note

    def _score_expense_ratio(self, code: str, etf_df: pd.DataFrame):
        """费率评分（0-25）"""
        # 判断是否为债券ETF
        etf_type = '股票'
        # 检查是否是债券ETF（从历史数据中无法直接判断，用screener的方法）
        fee_rate = self.screener.get_fee_rate(code, etf_type=etf_type)

        if fee_rate < 0.2:
            score = 25
            level = "优秀"
        elif fee_rate < 0.5:
            score = 20
            level = "良好"
        elif fee_rate < 0.8:
            score = 12
            level = "一般"
        else:
            score = 5
            level = "较差"

        detail = f"管理费率{fee_rate:.2f}%（{level}）"
        return score, detail, fee_rate

    def _score_liquidity(self, etf_df: pd.DataFrame):
        """流动性评分（0-25）——基于日均成交额"""
        if '成交额' not in etf_df.columns:
            return 12, "无成交额数据", None

        # 最近20天的日均成交额（元 → 亿元）
        recent = etf_df['成交额'].tail(20)
        avg_amount = recent.mean() / 1e8  # 元→亿元

        if avg_amount > 5:
            score = 25
            level = "充足"
        elif avg_amount > 1:
            score = 20
            level = "良好"
        elif avg_amount > 0.3:
            score = 12
            level = "一般"
        else:
            score = 5
            level = "偏低"

        detail = f"日均成交{avg_amount:.2f}亿元（{level}）"
        return score, detail, round(avg_amount, 2)

    def _score_fund_scale(self, code: str):
        """规模评分（0-25）"""
        try:
            scale_df = self.screener.get_etf_scale_data()
            match = scale_df[scale_df['code'] == code]
            if match.empty:
                return 12, "未找到规模数据", None

            scale = match.iloc[0]['scale']  # 亿份

            if scale > 100:
                score = 25
                level = "大型"
            elif scale > 30:
                score = 20
                level = "中大型"
            elif scale > 5:
                score = 12
                level = "中型"
            else:
                score = 5
                level = "小型"

            detail = f"基金规模{scale:.1f}亿份（{level}）"
            return score, detail, round(scale, 1)

        except Exception:
            return 12, "获取规模数据失败", None

    # ---- 辅助方法 ----

    @staticmethod
    def _total_to_grade(total: float) -> FundGradeLevel:
        if total >= 80:
            return FundGradeLevel.A
        elif total >= 60:
            return FundGradeLevel.B
        elif total >= 40:
            return FundGradeLevel.C
        else:
            return FundGradeLevel.D

    @staticmethod
    def _build_narrative(dimensions, grade, total, benchmark_note) -> str:
        parts = []
        for dim in dimensions:
            parts.append(dim.detail)

        summary = "、".join(parts) + f" → 评级{grade.value}（{total:.0f}分）"

        if benchmark_note:
            summary += f"。注：{benchmark_note}"

        return summary
