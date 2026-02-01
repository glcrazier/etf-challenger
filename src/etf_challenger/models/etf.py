"""ETF数据模型定义"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class ETFQuote:
    """ETF实时行情数据"""

    code: str                    # ETF代码
    name: str                    # ETF名称
    price: float                 # 最新价
    change: float                # 涨跌额
    change_pct: float            # 涨跌幅(%)
    volume: float                # 成交量
    amount: float                # 成交额
    open_price: float            # 开盘价
    high: float                  # 最高价
    low: float                   # 最低价
    pre_close: float             # 昨收价
    timestamp: datetime          # 数据时间


@dataclass
class ETFInfo:
    """ETF基本信息"""

    code: str                    # ETF代码
    name: str                    # ETF名称
    type: str                    # ETF类型
    fund_company: str            # 基金公司
    listing_date: Optional[str]  # 上市日期
    benchmark: Optional[str]     # 跟踪指数
    management_fee: Optional[float]  # 管理费率
    custodian_fee: Optional[float]   # 托管费率


@dataclass
class ETFNetValue:
    """ETF净值数据"""

    date: str                    # 日期
    unit_nav: float              # 单位净值
    accumulated_nav: float       # 累计净值
    daily_return: Optional[float] = None  # 日收益率(%)


@dataclass
class ETFHolding:
    """ETF持仓成分"""

    stock_code: str              # 股票代码
    stock_name: str              # 股票名称
    weight: float                # 持仓权重(%)
    shares: Optional[float] = None  # 持股数量
    market_value: Optional[float] = None  # 持仓市值


@dataclass
class ETFPremiumDiscount:
    """ETF溢价/折价数据"""

    date: str                    # 日期
    market_price: float          # 市价
    net_value: float             # 净值
    premium_rate: float          # 溢价率(%)，正数为溢价，负数为折价

    @property
    def is_premium(self) -> bool:
        """是否溢价"""
        return self.premium_rate > 0

    @property
    def is_discount(self) -> bool:
        """是否折价"""
        return self.premium_rate < 0
