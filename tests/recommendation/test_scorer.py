"""
ETFScorer评分系统测试
"""

import pytest
import pandas as pd
from src.etf_challenger.recommendation.scorer import (
    ETFScorer,
    ScoringStrategy,
    ScoreBreakdown
)


class TestScoreBreakdown:
    """ScoreBreakdown数据类测试"""

    def test_score_breakdown_creation(self):
        """测试ScoreBreakdown创建"""
        breakdown = ScoreBreakdown(
            total_score=85.5,
            return_score=80.0,
            risk_score=90.0,
            liquidity_score=100.0,
            fee_score=75.0,
            technical_score=70.0
        )

        assert breakdown.total_score == 85.5
        assert breakdown.return_score == 80.0
        assert breakdown.risk_score == 90.0

    def test_score_breakdown_to_dict(self):
        """测试转换为字典"""
        breakdown = ScoreBreakdown(
            total_score=85.5,
            return_score=80.0,
            risk_score=90.0,
            liquidity_score=100.0,
            fee_score=75.0,
            technical_score=70.0
        )

        result = breakdown.to_dict()

        assert '总分' in result
        assert '收益潜力' in result
        assert '风险评估' in result
        assert result['总分'] == 85.5
        assert result['收益潜力'] == 80.0


class TestETFScorer:
    """ETFScorer评分引擎测试"""

    def test_scorer_initialization(self):
        """测试评分器初始化"""
        # 默认策略
        scorer = ETFScorer()
        assert scorer.strategy == ScoringStrategy.BALANCED

        # 保守型策略
        scorer_conservative = ETFScorer(strategy=ScoringStrategy.CONSERVATIVE)
        assert scorer_conservative.strategy == ScoringStrategy.CONSERVATIVE
        assert scorer_conservative.weights['risk'] == 0.35  # 风险权重最高

    def test_strategy_weights(self):
        """测试不同策略的权重配置"""
        # 保守型
        conservative = ETFScorer(strategy=ScoringStrategy.CONSERVATIVE)
        assert conservative.weights['risk'] == 0.35
        assert conservative.weights['liquidity'] == 0.25

        # 激进型
        aggressive = ETFScorer(strategy=ScoringStrategy.AGGRESSIVE)
        assert aggressive.weights['return'] == 0.45  # 收益权重最高
        assert aggressive.weights['technical'] == 0.20

        # 权重和应该为1
        assert sum(conservative.weights.values()) == 1.0
        assert sum(aggressive.weights.values()) == 1.0

    def test_calculate_return_score(self):
        """测试收益潜力评分"""
        scorer = ETFScorer()

        # 优秀收益 (年化30%+, 夏普比率2.0+)
        score_excellent = scorer._calculate_return_score(35.0, 2.5)
        assert score_excellent >= 90

        # 良好收益 (年化15%, 夏普比率1.0)
        # return_part = (15+10)/40*20 = 12.5, sharpe_part = 1.0/2.0*80 = 40, total = 52.5
        score_good = scorer._calculate_return_score(15.0, 1.0)
        assert 50 <= score_good <= 55

        # 负收益 (年化-10%, 夏普比率0)
        score_poor = scorer._calculate_return_score(-10.0, 0.0)
        assert score_poor <= 20

    def test_calculate_risk_score(self):
        """测试风险评估评分（风险越低分越高）"""
        scorer = ETFScorer()

        # 低风险 (波动率10%, 最大回撤5%)
        score_low_risk = scorer._calculate_risk_score(10.0, 5.0)
        assert score_low_risk >= 90

        # 中等风险 (波动率20%, 最大回撤15%)
        score_medium_risk = scorer._calculate_risk_score(20.0, 15.0)
        assert 50 <= score_medium_risk <= 80

        # 高风险 (波动率40%, 最大回撤30%)
        score_high_risk = scorer._calculate_risk_score(40.0, 30.0)
        assert score_high_risk <= 40

    def test_calculate_fee_score(self):
        """测试费率优势评分"""
        scorer = ETFScorer()

        # 低费率 (0.15%)
        score_low_fee = scorer._calculate_fee_score(0.15)
        assert score_low_fee == 100

        # 中等费率 (0.5%)
        score_medium_fee = scorer._calculate_fee_score(0.5)
        assert 20 <= score_medium_fee <= 30

        # 高费率 (0.6%)
        score_high_fee = scorer._calculate_fee_score(0.6)
        assert score_high_fee == 0

    def test_calculate_technical_score_without_data(self):
        """测试无技术指标数据时的评分"""
        scorer = ETFScorer()

        # 无数据时应返回中性得分
        score = scorer._calculate_technical_score(None)
        assert score == 50.0

        # 空DataFrame
        empty_df = pd.DataFrame()
        score_empty = scorer._calculate_technical_score(empty_df)
        assert score_empty == 50.0

    def test_calculate_technical_score_with_ma(self):
        """测试带MA指标的技术面评分"""
        scorer = ETFScorer()

        # 创建测试数据
        df = pd.DataFrame({
            '收盘': [10.5],
            'MA5': [10.0],
            'MA20': [9.5],
            'RSI': [55.0],
            'MACD': [0.1],
            'Signal': [0.05]
        })

        score = scorer._calculate_technical_score(df)

        # 价格>MA5>MA20(30分) + RSI中性(30分) + MACD金叉且>0(40分) = 100分
        # 3个指标平均: 100/3 = 33.33
        assert 30 <= score <= 35

    def test_calculate_score_complete(self):
        """测试完整评分计算"""
        scorer = ETFScorer(strategy=ScoringStrategy.BALANCED)

        # 创建测试数据
        df = pd.DataFrame({
            '收盘': [4.5],
            'MA5': [4.4],
            'MA20': [4.3],
            'RSI': [55.0],
            'MACD': [0.05],
            'Signal': [0.03]
        })

        score_breakdown = scorer.calculate_score(
            etf_code='510300',
            etf_name='沪深300ETF',
            annual_return=15.0,
            sharpe_ratio=1.2,
            volatility=18.0,
            max_drawdown=12.0,
            scale=900.0,
            liquidity_score=100.0,
            fee_rate=0.5,
            df=df
        )

        # 验证返回类型
        assert isinstance(score_breakdown, ScoreBreakdown)

        # 验证评分范围
        assert 0 <= score_breakdown.total_score <= 100
        assert 0 <= score_breakdown.return_score <= 100
        assert 0 <= score_breakdown.risk_score <= 100
        assert 0 <= score_breakdown.liquidity_score <= 100
        assert 0 <= score_breakdown.fee_score <= 100
        assert 0 <= score_breakdown.technical_score <= 100

        # 验证总分计算逻辑
        weights = scorer.weights
        expected_total = (
            score_breakdown.return_score * weights['return'] +
            score_breakdown.risk_score * weights['risk'] +
            score_breakdown.liquidity_score * weights['liquidity'] +
            score_breakdown.fee_score * weights['fee'] +
            score_breakdown.technical_score * weights['technical']
        )

        assert abs(score_breakdown.total_score - expected_total) < 0.01

    def test_different_strategies_produce_different_scores(self):
        """测试不同策略产生不同的总分"""
        # 创建三个不同策略的评分器
        conservative = ETFScorer(strategy=ScoringStrategy.CONSERVATIVE)
        balanced = ETFScorer(strategy=ScoringStrategy.BALANCED)
        aggressive = ETFScorer(strategy=ScoringStrategy.AGGRESSIVE)

        # 创建有技术指标的DataFrame（激进型重视技术面）
        df_bullish = pd.DataFrame({
            '收盘': [10.5],
            'MA5': [10.0],
            'MA20': [9.5],
            'RSI': [55.0],
            'MACD': [0.1],
            'Signal': [0.05]
        })

        # 使用高收益、中等风险、优秀技术面的ETF数据
        common_params = {
            'etf_code': '510300',
            'etf_name': '沪深300ETF',
            'annual_return': 30.0,  # 高收益
            'sharpe_ratio': 2.0,    # 高夏普
            'volatility': 18.0,     # 中等波动
            'max_drawdown': 12.0,   # 中等回撤
            'scale': 200.0,         # 中等规模
            'liquidity_score': 70.0,  # 中等流动性
            'fee_rate': 0.5,
            'df': df_bullish
        }

        score_conservative = conservative.calculate_score(**common_params)
        score_balanced = balanced.calculate_score(**common_params)
        score_aggressive = aggressive.calculate_score(**common_params)

        # 激进型应看重高收益和技术面，总分应该更高
        assert score_aggressive.total_score > score_balanced.total_score
        # 保守型应看重流动性和风险，在流动性一般时分数应较低
        assert score_balanced.total_score > score_conservative.total_score

    def test_get_strategy_description(self):
        """测试获取策略描述"""
        conservative = ETFScorer(strategy=ScoringStrategy.CONSERVATIVE)
        balanced = ETFScorer(strategy=ScoringStrategy.BALANCED)
        aggressive = ETFScorer(strategy=ScoringStrategy.AGGRESSIVE)

        assert "保守型" in conservative.get_strategy_description()
        assert "稳健型" in balanced.get_strategy_description()
        assert "激进型" in aggressive.get_strategy_description()

    def test_edge_cases(self):
        """测试边界情况"""
        scorer = ETFScorer()

        # 极端优秀的ETF
        score_perfect = scorer.calculate_score(
            etf_code='TEST001',
            etf_name='完美ETF',
            annual_return=50.0,  # 极高收益
            sharpe_ratio=3.0,     # 极高夏普
            volatility=5.0,       # 极低波动
            max_drawdown=2.0,     # 极小回撤
            scale=1000.0,         # 超大规模
            liquidity_score=100.0,
            fee_rate=0.15,        # 极低费率
            df=None
        )

        assert score_perfect.total_score >= 90

        # 极端差的ETF
        score_poor = scorer.calculate_score(
            etf_code='TEST002',
            etf_name='差劲ETF',
            annual_return=-20.0,  # 负收益
            sharpe_ratio=0.0,
            volatility=60.0,      # 极高波动
            max_drawdown=50.0,    # 极大回撤
            scale=5.0,
            liquidity_score=30.0,
            fee_rate=0.8,         # 极高费率
            df=None
        )

        assert score_poor.total_score <= 40


class TestScoringStrategy:
    """ScoringStrategy枚举测试"""

    def test_strategy_values(self):
        """测试策略枚举值"""
        assert ScoringStrategy.CONSERVATIVE.value == "conservative"
        assert ScoringStrategy.BALANCED.value == "balanced"
        assert ScoringStrategy.AGGRESSIVE.value == "aggressive"

    def test_strategy_in_weights_dict(self):
        """测试所有策略都有权重配置"""
        for strategy in ScoringStrategy:
            assert strategy in ETFScorer.STRATEGY_WEIGHTS


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
