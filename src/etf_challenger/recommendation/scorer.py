"""
ETF多维度评分系统

提供5个维度的ETF评分算法：
1. 收益潜力 - 基于年化收益率和夏普比率
2. 风险评估 - 基于波动率和最大回撤
3. 流动性 - 基于规模和成交量
4. 费率优势 - 基于管理费率
5. 技术面 - 基于技术指标(MA/RSI/MACD)
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional
import pandas as pd


class ScoringStrategy(Enum):
    """评分策略"""
    CONSERVATIVE = "conservative"  # 保守型
    BALANCED = "balanced"         # 稳健型
    AGGRESSIVE = "aggressive"     # 激进型


@dataclass
class ScoreBreakdown:
    """评分明细"""
    total_score: float
    return_score: float      # 收益潜力得分
    risk_score: float        # 风险评估得分
    liquidity_score: float   # 流动性得分
    fee_score: float         # 费率优势得分
    technical_score: float   # 技术面得分

    def to_dict(self) -> Dict[str, float]:
        """转换为字典"""
        return {
            '总分': round(self.total_score, 1),
            '收益潜力': round(self.return_score, 1),
            '风险评估': round(self.risk_score, 1),
            '流动性': round(self.liquidity_score, 1),
            '费率优势': round(self.fee_score, 1),
            '技术面': round(self.technical_score, 1),
        }


class ETFScorer:
    """ETF评分引擎"""

    # 策略权重配置
    STRATEGY_WEIGHTS = {
        ScoringStrategy.CONSERVATIVE: {
            'return': 0.20,     # 收益潜力
            'risk': 0.35,       # 风险评估（最重要）
            'liquidity': 0.25,  # 流动性
            'fee': 0.15,        # 费率
            'technical': 0.05   # 技术面
        },
        ScoringStrategy.BALANCED: {
            'return': 0.30,
            'risk': 0.25,
            'liquidity': 0.20,
            'fee': 0.15,
            'technical': 0.10
        },
        ScoringStrategy.AGGRESSIVE: {
            'return': 0.45,     # 收益潜力（最重要）
            'risk': 0.10,       # 风险评估
            'liquidity': 0.15,
            'fee': 0.10,
            'technical': 0.20   # 技术面
        }
    }

    def __init__(self, strategy: ScoringStrategy = ScoringStrategy.BALANCED):
        """
        初始化评分引擎

        Args:
            strategy: 评分策略
        """
        self.strategy = strategy
        self.weights = self.STRATEGY_WEIGHTS[strategy]

    def calculate_score(
        self,
        etf_code: str,
        etf_name: str,
        annual_return: float,
        sharpe_ratio: float,
        volatility: float,
        max_drawdown: float,
        scale: float,
        liquidity_score: float,
        fee_rate: float,
        df: Optional[pd.DataFrame] = None
    ) -> ScoreBreakdown:
        """
        计算ETF综合评分

        Args:
            etf_code: ETF代码
            etf_name: ETF名称
            annual_return: 年化收益率(%)
            sharpe_ratio: 夏普比率
            volatility: 波动率(%)
            max_drawdown: 最大回撤(%)
            scale: 规模(亿份)
            liquidity_score: 流动性评分(0-100)
            fee_rate: 管理费率(%)
            df: 历史数据DataFrame(包含技术指标)

        Returns:
            评分明细对象
        """
        # 1. 收益潜力得分
        return_score = self._calculate_return_score(annual_return, sharpe_ratio)

        # 2. 风险评估得分
        risk_score = self._calculate_risk_score(volatility, max_drawdown)

        # 3. 流动性得分（直接使用）
        liquidity_score = liquidity_score

        # 4. 费率优势得分
        fee_score = self._calculate_fee_score(fee_rate)

        # 5. 技术面得分
        technical_score = self._calculate_technical_score(df) if df is not None else 50.0

        # 加权计算总分
        total_score = (
            return_score * self.weights['return'] +
            risk_score * self.weights['risk'] +
            liquidity_score * self.weights['liquidity'] +
            fee_score * self.weights['fee'] +
            technical_score * self.weights['technical']
        )

        return ScoreBreakdown(
            total_score=total_score,
            return_score=return_score,
            risk_score=risk_score,
            liquidity_score=liquidity_score,
            fee_score=fee_score,
            technical_score=technical_score
        )

    def _calculate_return_score(self, annual_return: float, sharpe_ratio: float) -> float:
        """
        计算收益潜力得分

        评分逻辑:
        - 年化收益率: 0-20分
        - 夏普比率: 0-80分

        Args:
            annual_return: 年化收益率(%)
            sharpe_ratio: 夏普比率

        Returns:
            收益潜力得分(0-100)
        """
        # 年化收益率评分 (0-20分)
        # 超过30%算满分，低于-10%算0分
        if annual_return >= 30:
            return_part = 20
        elif annual_return <= -10:
            return_part = 0
        else:
            return_part = (annual_return + 10) / 40 * 20

        # 夏普比率评分 (0-80分)
        # 大于2.0算满分，小于0算0分
        if sharpe_ratio >= 2.0:
            sharpe_part = 80
        elif sharpe_ratio <= 0:
            sharpe_part = 0
        else:
            sharpe_part = sharpe_ratio / 2.0 * 80

        return return_part + sharpe_part

    def _calculate_risk_score(self, volatility: float, max_drawdown: float) -> float:
        """
        计算风险评估得分（风险越低分数越高）

        评分逻辑:
        - 波动率: 0-60分（越低越好）
        - 最大回撤: 0-40分（越小越好）

        Args:
            volatility: 波动率(%)
            max_drawdown: 最大回撤(%)

        Returns:
            风险评估得分(0-100)
        """
        # 波动率评分 (0-60分，越低越好)
        # 低于10%算满分，高于50%算0分
        if volatility <= 10:
            vol_part = 60
        elif volatility >= 50:
            vol_part = 0
        else:
            vol_part = (50 - volatility) / 40 * 60

        # 最大回撤评分 (0-40分，越小越好)
        # 低于5%算满分，高于40%算0分
        if max_drawdown <= 5:
            drawdown_part = 40
        elif max_drawdown >= 40:
            drawdown_part = 0
        else:
            drawdown_part = (40 - max_drawdown) / 35 * 40

        return vol_part + drawdown_part

    def _calculate_fee_score(self, fee_rate: float) -> float:
        """
        计算费率优势得分（费率越低分数越高）

        评分逻辑:
        - 费率0.15%算100分
        - 费率0.6%算0分
        - 线性插值

        Args:
            fee_rate: 管理费率(%)

        Returns:
            费率优势得分(0-100)
        """
        if fee_rate <= 0.15:
            return 100
        elif fee_rate >= 0.6:
            return 0
        else:
            return (0.6 - fee_rate) / 0.45 * 100

    def _calculate_technical_score(self, df: pd.DataFrame) -> float:
        """
        计算技术面得分

        基于MA/RSI/MACD等技术指标综合评分

        Args:
            df: 包含技术指标的历史数据

        Returns:
            技术面得分(0-100)
        """
        if df is None or df.empty:
            return 50.0

        score = 0
        indicators_count = 0

        try:
            last_row = df.iloc[-1]
            current_price = last_row['收盘']

            # MA趋势评分 (0-30分)
            if 'MA5' in df.columns and 'MA20' in df.columns:
                ma5 = last_row['MA5']
                ma20 = last_row['MA20']

                if pd.notna(ma5) and pd.notna(ma20):
                    if current_price > ma5 > ma20:
                        # 价格>MA5>MA20，强势上涨
                        score += 30
                    elif current_price > ma5:
                        # 价格>MA5，短期上涨
                        score += 20
                    elif current_price > ma20:
                        # 价格>MA20，长期上涨
                        score += 10
                    indicators_count += 1

            # RSI评分 (0-30分)
            if 'RSI' in df.columns:
                rsi = last_row['RSI']
                if pd.notna(rsi):
                    if 40 <= rsi <= 60:
                        # RSI中性区域，最佳
                        score += 30
                    elif 30 <= rsi < 40 or 60 < rsi <= 70:
                        # RSI偏离中性，但未超买超卖
                        score += 20
                    elif rsi < 30:
                        # 超卖，可能反弹
                        score += 15
                    elif rsi > 70:
                        # 超买，风险较高
                        score += 5
                    indicators_count += 1

            # MACD评分 (0-40分)
            if 'MACD' in df.columns and 'Signal' in df.columns:
                macd = last_row['MACD']
                signal = last_row['Signal']

                if pd.notna(macd) and pd.notna(signal):
                    macd_diff = macd - signal

                    if macd_diff > 0 and macd > 0:
                        # MACD金叉且在0轴上方，强势
                        score += 40
                    elif macd_diff > 0:
                        # MACD金叉，买入信号
                        score += 30
                    elif macd > 0:
                        # MACD在0轴上方，多头趋势
                        score += 20
                    else:
                        # MACD在0轴下方，空头趋势
                        score += 10
                    indicators_count += 1

            # 归一化到0-100
            if indicators_count > 0:
                return min(100, score / indicators_count * 100 / 100)

        except Exception:
            # 如果计算失败，返回中性得分
            pass

        return 50.0

    def get_strategy_description(self) -> str:
        """获取当前策略的描述"""
        descriptions = {
            ScoringStrategy.CONSERVATIVE: "保守型 - 注重风险控制和流动性",
            ScoringStrategy.BALANCED: "稳健型 - 收益与风险平衡",
            ScoringStrategy.AGGRESSIVE: "激进型 - 追求高收益，技术面权重高"
        }
        return descriptions[self.strategy]
