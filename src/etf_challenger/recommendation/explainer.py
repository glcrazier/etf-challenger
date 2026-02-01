"""
推荐理由生成器

基于ETF评分明细，自动生成智能推荐理由和风险提示。
"""

from typing import List, Dict
from .scorer import ScoreBreakdown


class RecommendationExplainer:
    """推荐理由生成器"""

    def __init__(self):
        """初始化推荐理由生成器"""
        pass

    def generate_reasons(
        self,
        etf_code: str,
        etf_name: str,
        score_breakdown: ScoreBreakdown,
        annual_return: float,
        volatility: float,
        scale: float,
        fee_rate: float,
        **kwargs
    ) -> List[str]:
        """
        生成推荐理由

        Args:
            etf_code: ETF代码
            etf_name: ETF名称
            score_breakdown: 评分明细
            annual_return: 年化收益率(%)
            volatility: 波动率(%)
            scale: 规模(亿份)
            fee_rate: 管理费率(%)
            **kwargs: 其他可选参数

        Returns:
            推荐理由列表（3-5条）
        """
        reasons = []

        # 1. 收益潜力理由
        if score_breakdown.return_score >= 70:
            if annual_return > 20:
                reasons.append(f"📈 年化收益率达{annual_return:.1f}%，收益表现优异")
            elif annual_return > 10:
                reasons.append(f"📈 年化收益率{annual_return:.1f}%，收益表现良好")
            else:
                reasons.append(f"📊 夏普比率高，风险调整后收益优秀")

        # 2. 风险控制理由
        if score_breakdown.risk_score >= 70:
            if volatility < 15:
                reasons.append(f"🛡️ 波动率仅{volatility:.1f}%，风险控制优秀，适合稳健投资")
            elif volatility < 25:
                reasons.append(f"🛡️ 波动率{volatility:.1f}%，风险可控")
            else:
                reasons.append(f"📉 最大回撤控制良好，风险管理能力强")

        # 3. 流动性理由
        if score_breakdown.liquidity_score >= 85:
            if scale >= 100:
                reasons.append(f"💰 规模{scale:.0f}亿份，超大规模，流动性极佳")
            elif scale >= 50:
                reasons.append(f"💰 规模{scale:.0f}亿份，流动性优秀，适合大额交易")
            else:
                reasons.append(f"💰 规模{scale:.0f}亿份，流动性良好")

        # 4. 费率优势理由
        if score_breakdown.fee_score >= 70:
            if fee_rate <= 0.3:
                reasons.append(f"💵 管理费率仅{fee_rate:.2f}%，成本优势明显")
            elif fee_rate <= 0.5:
                reasons.append(f"💵 管理费率{fee_rate:.2f}%，费用合理")

        # 5. 技术面理由
        if score_breakdown.technical_score >= 70:
            reasons.append(f"📊 技术指标健康，趋势向好")
        elif score_breakdown.technical_score >= 60:
            reasons.append(f"📊 技术面中性偏多，走势平稳")

        # 6. 综合评分理由（作为兜底）
        if len(reasons) < 3:
            if score_breakdown.total_score >= 80:
                reasons.append(f"⭐ 综合评分{score_breakdown.total_score:.1f}，各项指标均衡优秀")
            elif score_breakdown.total_score >= 70:
                reasons.append(f"⭐ 综合评分{score_breakdown.total_score:.1f}，整体表现良好")

        # 限制在3-5条理由
        return reasons[:5]

    def generate_risk_warnings(
        self,
        score_breakdown: ScoreBreakdown,
        annual_return: float,
        volatility: float,
        max_drawdown: float,
        **kwargs
    ) -> List[str]:
        """
        生成风险提示

        Args:
            score_breakdown: 评分明细
            annual_return: 年化收益率(%)
            volatility: 波动率(%)
            max_drawdown: 最大回撤(%)
            **kwargs: 其他可选参数

        Returns:
            风险提示列表
        """
        warnings = []

        # 1. 风险评分较低
        if score_breakdown.risk_score < 50:
            if volatility > 30:
                warnings.append(f"⚠️ 波动率较高({volatility:.1f}%)，建议控制仓位")
            if max_drawdown > 25:
                warnings.append(f"⚠️ 历史最大回撤达{max_drawdown:.1f}%，注意风险")

        # 2. 流动性风险
        if score_breakdown.liquidity_score < 60:
            warnings.append(f"⚠️ 流动性一般，建议小额交易")

        # 3. 收益风险比
        if annual_return < 0:
            warnings.append(f"⚠️ 年化收益为负({annual_return:.1f}%)，需谨慎")

        # 4. 技术面风险
        if score_breakdown.technical_score < 40:
            warnings.append(f"⚠️ 技术面偏弱，短期可能承压")

        return warnings

    def generate_comparison(
        self,
        etf_code: str,
        annual_return: float,
        volatility: float,
        market_avg_return: float = 10.0,
        market_avg_volatility: float = 20.0,
    ) -> List[str]:
        """
        生成对比参考信息

        Args:
            etf_code: ETF代码
            annual_return: 年化收益率(%)
            volatility: 波动率(%)
            market_avg_return: 市场平均收益率(%)
            market_avg_volatility: 市场平均波动率(%)

        Returns:
            对比信息列表
        """
        comparisons = []

        # 收益对比
        if annual_return > market_avg_return * 1.2:
            diff = annual_return - market_avg_return
            comparisons.append(f"📊 收益率跑赢市场平均{diff:.1f}个百分点")
        elif annual_return < market_avg_return * 0.8:
            diff = market_avg_return - annual_return
            comparisons.append(f"📊 收益率低于市场平均{diff:.1f}个百分点")

        # 波动率对比
        if volatility < market_avg_volatility * 0.8:
            comparisons.append(f"📉 波动率明显低于市场平均，更加稳健")
        elif volatility > market_avg_volatility * 1.2:
            comparisons.append(f"📈 波动率高于市场平均，波动较大")

        return comparisons

    def generate_confidence_level(
        self,
        score_breakdown: ScoreBreakdown
    ) -> tuple[str, str]:
        """
        生成推荐置信度

        Args:
            score_breakdown: 评分明细

        Returns:
            (置信度等级, 置信度说明)
        """
        total_score = score_breakdown.total_score

        if total_score >= 85:
            return ("极高", "各维度得分均衡且优秀，强烈推荐")
        elif total_score >= 75:
            return ("高", "综合表现优秀，推荐关注")
        elif total_score >= 65:
            return ("中等", "整体表现良好，可以考虑")
        elif total_score >= 55:
            return ("偏低", "部分指标较弱，需谨慎")
        else:
            return ("低", "综合表现欠佳，不建议配置")

    def format_recommendation_report(
        self,
        etf_code: str,
        etf_name: str,
        score_breakdown: ScoreBreakdown,
        reasons: List[str],
        warnings: List[str],
        comparisons: List[str],
        confidence: tuple[str, str],
    ) -> Dict[str, any]:
        """
        格式化完整的推荐报告

        Args:
            etf_code: ETF代码
            etf_name: ETF名称
            score_breakdown: 评分明细
            reasons: 推荐理由
            warnings: 风险提示
            comparisons: 对比信息
            confidence: 推荐置信度

        Returns:
            推荐报告字典
        """
        return {
            'etf_code': etf_code,
            'etf_name': etf_name,
            'total_score': score_breakdown.total_score,
            'score_breakdown': score_breakdown.to_dict(),
            'reasons': reasons,
            'warnings': warnings,
            'comparisons': comparisons,
            'confidence_level': confidence[0],
            'confidence_desc': confidence[1],
        }
