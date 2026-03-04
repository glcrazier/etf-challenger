"""统一决策框架数据模型"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum


class RegimeType(Enum):
    """市场状态类型"""
    CRISIS = "危机"
    TRENDING_UP = "上升趋势"
    TRENDING_DOWN = "下降趋势"
    RANGING = "震荡"


class FundGradeLevel(Enum):
    """基金评级"""
    A = "A"
    B = "B"
    C = "C"
    D = "D"


@dataclass
class MarketRegime:
    """市场状态（Layer 1）"""
    regime: RegimeType
    volatility_20d: float           # 20日波动率（年化%）
    volatility_long: float          # 长期波动率（年化%）
    drawdown_20d: float             # 20日回撤（%）
    price_vs_ma60: float            # 价格相对MA60偏离（%）
    ma20_vs_ma60: float             # MA20相对MA60偏离（%）
    narrative: str = ""             # 叙述段落


@dataclass
class DimensionScore:
    """单维度评分"""
    name: str
    score: float                    # 0-25
    detail: str                     # 描述


@dataclass
class FundGrade:
    """基金评级（Layer 2）"""
    grade: FundGradeLevel
    total_score: float              # 0-100
    dimensions: List[DimensionScore] = field(default_factory=list)
    tracking_error: Optional[float] = None   # 跟踪误差（%）
    expense_ratio: Optional[float] = None    # 费率（%）
    avg_daily_amount: Optional[float] = None # 日均成交额（亿元）
    fund_scale: Optional[float] = None       # 基金规模（亿份）
    benchmark_note: str = ""                 # 基准说明（如：使用沪深300回退）
    narrative: str = ""


@dataclass
class ChannelSignal:
    """单通道信号"""
    name: str
    score: float                    # -1 到 +1
    weight: float                   # 权重（%）
    detail: str


@dataclass
class TimingResult:
    """时机分析结果（Layer 3）"""
    composite_score: float          # -1 到 +1（加权后）
    confidence: float               # 0-100
    action: str                     # "买入" / "卖出" / "持有"
    channels: List[ChannelSignal] = field(default_factory=list)
    narrative: str = ""


@dataclass
class TrancheEntry:
    """分批买入条目"""
    tranche_no: int
    price: float
    pct_of_position: float          # 该批占总仓位百分比


@dataclass
class PositionAdvice:
    """持仓建议（Layer 4）"""
    suggested_pct: float            # 建议仓位百分比
    max_correlation: float          # 与现有持仓最大相关性
    correlated_holding: str         # 最相关的持仓名称
    tranches: List[TrancheEntry] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    narrative: str = ""


@dataclass
class UnifiedAnalysis:
    """统一分析结果（4层汇总）"""
    code: str
    name: str
    regime: MarketRegime
    fund_grade: FundGrade
    timing: TimingResult
    portfolio: Optional[PositionAdvice] = None
    conclusion: str = ""            # 综合结论叙述
    risks: List[str] = field(default_factory=list)
