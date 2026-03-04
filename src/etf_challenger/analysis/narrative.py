"""叙事报告生成器

将4层分析结果转化为投资者可读的叙述文本。
"""

from typing import Optional

from ..models.decision import (
    UnifiedAnalysis, MarketRegime, FundGrade, TimingResult,
    PositionAdvice, RegimeType, FundGradeLevel,
)


class NarrativeReporter:
    """叙事报告生成器"""

    def generate_conclusion(
        self,
        regime: MarketRegime,
        fund_grade: FundGrade,
        timing: TimingResult,
        portfolio: Optional[PositionAdvice],
    ) -> tuple:
        """
        生成综合结论和风险列表

        Returns:
            (conclusion_text, risk_list)
        """
        # 各层评价
        regime_tag = self._regime_tag(regime)
        grade_tag = self._grade_tag(fund_grade)
        timing_tag = self._timing_tag(timing)

        # 组合结论
        parts = []
        parts.append(regime_tag)
        parts.append(grade_tag)
        parts.append(timing_tag)

        if portfolio:
            parts.append(f"持仓建议{portfolio.suggested_pct:.0f}%")

        conclusion = " + ".join(parts)

        # 行动建议
        action_map = self._derive_action(regime, fund_grade, timing)
        conclusion += f" → {action_map}"

        # 风险识别
        risks = self._identify_risks(regime, fund_grade, timing, portfolio)

        if risks:
            conclusion += "。\n主要风险：" + "；".join(risks) + "。"
        else:
            conclusion += "。"

        return conclusion, risks

    def _regime_tag(self, regime: MarketRegime) -> str:
        tags = {
            RegimeType.CRISIS: "市场危机",
            RegimeType.TRENDING_UP: "市场有利",
            RegimeType.TRENDING_DOWN: "市场不利",
            RegimeType.RANGING: "市场中性",
        }
        return tags.get(regime.regime, "市场未知")

    def _grade_tag(self, grade: FundGrade) -> str:
        tags = {
            FundGradeLevel.A: "基金优质",
            FundGradeLevel.B: "基金良好",
            FundGradeLevel.C: "基金一般",
            FundGradeLevel.D: "基金较差",
        }
        return tags.get(grade.grade, "基金未评")

    def _timing_tag(self, timing: TimingResult) -> str:
        if timing.action == "买入":
            return "时机偏多"
        elif timing.action == "卖出":
            return "时机偏空"
        else:
            return "时机中性"

    def _derive_action(
        self,
        regime: MarketRegime,
        fund_grade: FundGrade,
        timing: TimingResult,
    ) -> str:
        """根据三层综合判断行动"""
        # 基金评级D，不建议买入
        if fund_grade.grade == FundGradeLevel.D:
            return "基金质量不佳，建议换标的"

        # 危机模式
        if regime.regime == RegimeType.CRISIS:
            if timing.action == "买入" and timing.confidence > 60:
                return "危机中出现买入信号，可小仓位试探"
            return "建议观望，等待市场企稳"

        # 下降趋势
        if regime.regime == RegimeType.TRENDING_DOWN:
            if timing.action == "买入":
                return "逆势买入需谨慎，建议减少仓位"
            return "建议减仓或观望"

        # 上升趋势或震荡
        if timing.action == "买入":
            if fund_grade.grade == FundGradeLevel.A:
                return "建议分批建仓"
            return "建议适量买入"
        elif timing.action == "卖出":
            return "建议减仓"
        else:
            return "建议观望，等待更好时机"

    def _identify_risks(
        self,
        regime: MarketRegime,
        fund_grade: FundGrade,
        timing: TimingResult,
        portfolio: Optional[PositionAdvice],
    ) -> list:
        """识别主要风险"""
        risks = []

        # 市场风险
        if regime.regime == RegimeType.CRISIS:
            risks.append("市场处于危机模式，系统性风险较高")
        elif regime.volatility_20d > 30:
            risks.append(f"短期波动率偏高（{regime.volatility_20d:.1f}%）")
        if regime.drawdown_20d < -8:
            risks.append(f"近20日回撤{regime.drawdown_20d:.1f}%")

        # 基金风险
        if fund_grade.grade in (FundGradeLevel.C, FundGradeLevel.D):
            risks.append(f"基金评级{fund_grade.grade.value}，质量偏低")
        if fund_grade.tracking_error and fund_grade.tracking_error > 2:
            risks.append(f"跟踪误差{fund_grade.tracking_error:.2f}%偏高")

        # 时机风险
        if timing.confidence < 40:
            risks.append("信号置信度偏低，不确定性较大")

        # 通道分歧
        bullish = sum(1 for ch in timing.channels if ch.score > 0.1)
        bearish = sum(1 for ch in timing.channels if ch.score < -0.1)
        if bullish > 0 and bearish > 0:
            risks.append("多空信号存在分歧")

        # 持仓风险
        if portfolio and portfolio.warnings:
            risks.extend(portfolio.warnings)

        return risks
