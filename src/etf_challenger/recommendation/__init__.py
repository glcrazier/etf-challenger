"""
智能推荐引擎模块

提供ETF多维度评分和智能推荐理由生成功能。
"""

from .scorer import ETFScorer, ScoringStrategy
from .explainer import RecommendationExplainer

__all__ = ['ETFScorer', 'ScoringStrategy', 'RecommendationExplainer']
