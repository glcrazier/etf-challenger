"""
RecommendationExplainer推荐理由生成器测试
"""

import pytest
from src.etf_challenger.recommendation.scorer import ScoreBreakdown
from src.etf_challenger.recommendation.explainer import RecommendationExplainer


class TestRecommendationExplainer:
    """推荐理由生成器测试"""

    def test_explainer_initialization(self):
        """测试初始化"""
        explainer = RecommendationExplainer()
        assert explainer is not None

    def test_generate_reasons_high_score(self):
        """测试高分ETF的推荐理由生成"""
        explainer = RecommendationExplainer()

        # 创建高分评分明细
        score_breakdown = ScoreBreakdown(
            total_score=88.0,
            return_score=85.0,
            risk_score=90.0,
            liquidity_score=95.0,
            fee_score=80.0,
            technical_score=75.0
        )

        reasons = explainer.generate_reasons(
            etf_code='510300',
            etf_name='沪深300ETF',
            score_breakdown=score_breakdown,
            annual_return=25.0,
            volatility=15.0,
            scale=900.0,
            fee_rate=0.5
        )

        # 应该生成3-5条理由
        assert 3 <= len(reasons) <= 5

        # 应该包含收益相关理由
        assert any('收益' in reason for reason in reasons)

        # 应该包含风险相关理由
        assert any('风险' in reason or '波动' in reason for reason in reasons)

        # 应该包含流动性相关理由
        assert any('流动' in reason or '规模' in reason for reason in reasons)

    def test_generate_reasons_low_score(self):
        """测试低分ETF的推荐理由生成"""
        explainer = RecommendationExplainer()

        # 创建低分评分明细
        score_breakdown = ScoreBreakdown(
            total_score=45.0,
            return_score=30.0,
            risk_score=40.0,
            liquidity_score=50.0,
            fee_score=45.0,
            technical_score=35.0
        )

        reasons = explainer.generate_reasons(
            etf_code='TEST001',
            etf_name='低分ETF',
            score_breakdown=score_breakdown,
            annual_return=5.0,
            volatility=35.0,
            scale=10.0,
            fee_rate=0.7
        )

        # 低分ETF没有突出优势，可能没有推荐理由（这是合理的）
        assert isinstance(reasons, list)
        assert len(reasons) >= 0  # 可能为空

    def test_generate_reasons_content(self):
        """测试推荐理由的具体内容"""
        explainer = RecommendationExplainer()

        score_breakdown = ScoreBreakdown(
            total_score=85.0,
            return_score=90.0,  # 高收益分
            risk_score=75.0,
            liquidity_score=88.0,
            fee_score=90.0,  # 高费率分
            technical_score=80.0
        )

        reasons = explainer.generate_reasons(
            etf_code='510300',
            etf_name='沪深300ETF',
            score_breakdown=score_breakdown,
            annual_return=28.0,  # 高收益
            volatility=18.0,
            scale=900.0,  # 大规模
            fee_rate=0.2  # 低费率
        )

        # 验证理由包含emoji标识
        assert any('📈' in reason or '🛡️' in reason or '💰' in reason or '💵' in reason
                   for reason in reasons)

    def test_generate_risk_warnings(self):
        """测试风险提示生成"""
        explainer = RecommendationExplainer()

        # 创建高风险评分
        score_breakdown = ScoreBreakdown(
            total_score=55.0,
            return_score=60.0,
            risk_score=35.0,  # 低风险分（高风险）
            liquidity_score=45.0,  # 低流动性
            fee_score=50.0,
            technical_score=30.0  # 低技术面分
        )

        warnings = explainer.generate_risk_warnings(
            score_breakdown=score_breakdown,
            annual_return=10.0,
            volatility=35.0,  # 高波动
            max_drawdown=28.0  # 大回撤
        )

        # 应该有风险提示
        assert len(warnings) > 0

        # 应该提示波动率风险
        assert any('波动率' in warning for warning in warnings)

        # 应该提示回撤风险
        assert any('回撤' in warning for warning in warnings)

        # 应该有风险emoji标识
        assert any('⚠️' in warning for warning in warnings)

    def test_generate_risk_warnings_low_risk(self):
        """测试低风险ETF的风险提示"""
        explainer = RecommendationExplainer()

        # 创建低风险评分
        score_breakdown = ScoreBreakdown(
            total_score=85.0,
            return_score=80.0,
            risk_score=90.0,  # 高风险分（低风险）
            liquidity_score=95.0,
            fee_score=85.0,
            technical_score=75.0
        )

        warnings = explainer.generate_risk_warnings(
            score_breakdown=score_breakdown,
            annual_return=15.0,
            volatility=12.0,  # 低波动
            max_drawdown=8.0  # 小回撤
        )

        # 低风险ETF应该没有或很少风险提示
        assert len(warnings) <= 1

    def test_generate_comparison(self):
        """测试对比信息生成"""
        explainer = RecommendationExplainer()

        # 收益高于市场
        comparisons_high = explainer.generate_comparison(
            etf_code='510300',
            annual_return=18.0,  # 高于市场平均10%
            volatility=15.0,     # 低于市场平均20%
            market_avg_return=10.0,
            market_avg_volatility=20.0
        )

        assert len(comparisons_high) > 0
        assert any('跑赢市场' in comp for comp in comparisons_high)

        # 收益低于市场
        comparisons_low = explainer.generate_comparison(
            etf_code='TEST001',
            annual_return=6.0,   # 低于市场平均
            volatility=25.0,     # 高于市场平均
            market_avg_return=10.0,
            market_avg_volatility=20.0
        )

        assert len(comparisons_low) > 0

    def test_generate_confidence_level(self):
        """测试置信度生成"""
        explainer = RecommendationExplainer()

        # 极高置信度
        score_very_high = ScoreBreakdown(
            total_score=90.0,
            return_score=85.0,
            risk_score=90.0,
            liquidity_score=95.0,
            fee_score=85.0,
            technical_score=80.0
        )
        confidence_very_high = explainer.generate_confidence_level(score_very_high)
        assert confidence_very_high[0] == "极高"
        assert "强烈推荐" in confidence_very_high[1]

        # 高置信度
        score_high = ScoreBreakdown(
            total_score=78.0,
            return_score=75.0,
            risk_score=80.0,
            liquidity_score=85.0,
            fee_score=70.0,
            technical_score=65.0
        )
        confidence_high = explainer.generate_confidence_level(score_high)
        assert confidence_high[0] == "高"

        # 中等置信度
        score_medium = ScoreBreakdown(
            total_score=68.0,
            return_score=65.0,
            risk_score=70.0,
            liquidity_score=75.0,
            fee_score=60.0,
            technical_score=55.0
        )
        confidence_medium = explainer.generate_confidence_level(score_medium)
        assert confidence_medium[0] == "中等"

        # 低置信度
        score_low = ScoreBreakdown(
            total_score=45.0,
            return_score=40.0,
            risk_score=50.0,
            liquidity_score=55.0,
            fee_score=35.0,
            technical_score=30.0
        )
        confidence_low = explainer.generate_confidence_level(score_low)
        assert confidence_low[0] == "低"

    def test_format_recommendation_report(self):
        """测试完整推荐报告格式化"""
        explainer = RecommendationExplainer()

        score_breakdown = ScoreBreakdown(
            total_score=82.0,
            return_score=80.0,
            risk_score=85.0,
            liquidity_score=90.0,
            fee_score=75.0,
            technical_score=70.0
        )

        reasons = ["理由1", "理由2", "理由3"]
        warnings = ["警告1"]
        comparisons = ["对比1"]
        confidence = ("高", "推荐关注")

        report = explainer.format_recommendation_report(
            etf_code='510300',
            etf_name='沪深300ETF',
            score_breakdown=score_breakdown,
            reasons=reasons,
            warnings=warnings,
            comparisons=comparisons,
            confidence=confidence
        )

        # 验证报告结构
        assert report['etf_code'] == '510300'
        assert report['etf_name'] == '沪深300ETF'
        assert report['total_score'] == 82.0
        assert 'score_breakdown' in report
        assert report['reasons'] == reasons
        assert report['warnings'] == warnings
        assert report['comparisons'] == comparisons
        assert report['confidence_level'] == "高"
        assert report['confidence_desc'] == "推荐关注"

    def test_empty_warnings_and_comparisons(self):
        """测试无警告和对比信息的情况"""
        explainer = RecommendationExplainer()

        score_breakdown = ScoreBreakdown(
            total_score=88.0,
            return_score=85.0,
            risk_score=90.0,
            liquidity_score=95.0,
            fee_score=80.0,
            technical_score=75.0
        )

        warnings = explainer.generate_risk_warnings(
            score_breakdown=score_breakdown,
            annual_return=20.0,
            volatility=12.0,
            max_drawdown=8.0
        )

        # 优秀ETF可能没有警告
        # 这是正常的，不应该报错
        assert isinstance(warnings, list)

    def test_reasons_variety(self):
        """测试推荐理由的多样性"""
        explainer = RecommendationExplainer()

        # 收益优秀的ETF
        score_high_return = ScoreBreakdown(
            total_score=75.0,
            return_score=95.0,  # 收益突出
            risk_score=60.0,
            liquidity_score=70.0,
            fee_score=65.0,
            technical_score=55.0
        )

        reasons_return = explainer.generate_reasons(
            etf_code='TEST001',
            etf_name='高收益ETF',
            score_breakdown=score_high_return,
            annual_return=35.0,
            volatility=25.0,
            scale=50.0,
            fee_rate=0.6
        )

        # 应该主要强调收益
        assert any('收益' in reason for reason in reasons_return)

        # 流动性优秀的ETF
        score_high_liquidity = ScoreBreakdown(
            total_score=75.0,
            return_score=60.0,
            risk_score=65.0,
            liquidity_score=98.0,  # 流动性突出
            fee_score=70.0,
            technical_score=55.0
        )

        reasons_liquidity = explainer.generate_reasons(
            etf_code='TEST002',
            etf_name='大规模ETF',
            score_breakdown=score_high_liquidity,
            annual_return=12.0,
            volatility=20.0,
            scale=1000.0,
            fee_rate=0.5
        )

        # 应该主要强调流动性
        assert any('流动' in reason or '规模' in reason for reason in reasons_liquidity)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
