"""数据获取服务 - 基于akshare获取A股ETF数据"""

import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Optional
from ..models.etf import ETFQuote, ETFInfo, ETFNetValue, ETFHolding, ETFPremiumDiscount
from ..utils.retry import retry


class ETFDataService:
    """ETF数据获取服务"""

    def __init__(self):
        """初始化数据服务"""
        self._etf_list_cache = None
        self._cache_time = None

    @retry(max_attempts=2, delay=1.0)
    def get_etf_list(self, refresh: bool = False) -> pd.DataFrame:
        """
        获取所有场内ETF列表

        Args:
            refresh: 是否强制刷新缓存

        Returns:
            包含ETF代码、名称等信息的DataFrame（字段已规范化）
        """
        # 使用缓存（1小时内有效）
        if not refresh and self._etf_list_cache is not None:
            if self._cache_time and (datetime.now() - self._cache_time).seconds < 3600:
                return self._etf_list_cache

        df = None
        source = None

        try:
            # 优先使用东方财富数据源
            df = ak.fund_etf_spot_em()
            source = "em"
        except Exception as e1:
            # 如果失败，尝试同花顺数据源
            try:
                df_ths = ak.fund_etf_spot_ths()
                # 规范化同花顺数据源的字段名
                df = pd.DataFrame({
                    '代码': df_ths['基金代码'],
                    '名称': df_ths['基金名称'],
                    '最新价': df_ths['当前-单位净值'],
                    '涨跌幅': df_ths['增长率'],
                    '涨跌额': df_ths['增长值'],
                    '成交量': 0,  # 同花顺数据源没有成交量
                    '成交额': 0,  # 同花顺数据源没有成交额
                    '开盘价': df_ths['前一日-单位净值'],
                    '最高价': df_ths['当前-单位净值'],
                    '最低价': df_ths['前一日-单位净值'],
                    '昨收': df_ths['前一日-单位净值'],
                })
                source = "ths"
            except Exception as e2:
                raise Exception(f"获取ETF列表失败: {str(e1)} / {str(e2)}")

        self._etf_list_cache = df
        self._cache_time = datetime.now()
        return df

    @retry(max_attempts=2, delay=1.0)
    def get_realtime_quote(self, code: str) -> Optional[ETFQuote]:
        """
        获取ETF实时行情

        Args:
            code: ETF代码（如：512880）

        Returns:
            ETF实时行情数据
        """
        # 获取所有ETF实时行情（会使用缓存）
        df = self.get_etf_list()

        # 筛选指定代码
        etf_data = df[df['代码'] == code]

        if etf_data.empty:
            return None

        row = etf_data.iloc[0]

        return ETFQuote(
            code=code,
            name=row['名称'],
            price=float(row['最新价']),
            change=float(row['涨跌额']),
            change_pct=float(row['涨跌幅']),
            volume=float(row['成交量']),
            amount=float(row['成交额']),
            open_price=float(row['开盘价']),
            high=float(row['最高价']),
            low=float(row['最低价']),
            pre_close=float(row['昨收']),
            timestamp=datetime.now()
        )

    @retry(max_attempts=3, delay=1.0)
    def get_historical_data(
        self,
        code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        获取ETF历史行情数据

        Args:
            code: ETF代码
            start_date: 开始日期（格式：YYYYMMDD），默认为1年前
            end_date: 结束日期（格式：YYYYMMDD），默认为今天

        Returns:
            历史行情DataFrame
        """
        if end_date is None:
            end_date = datetime.now().strftime("%Y%m%d")

        if start_date is None:
            start_date = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")

        # 获取ETF历史行情
        df = ak.fund_etf_hist_em(
            symbol=code,
            period="daily",
            start_date=start_date,
            end_date=end_date,
            adjust="qfq"  # 前复权
        )
        return df

    @retry(max_attempts=2, delay=1.0)
    def get_etf_holdings(self, code: str, year: str = None) -> List[ETFHolding]:
        """
        获取ETF持仓成分

        Args:
            code: ETF代码
            year: 查询年份，默认为当前年份

        Returns:
            持仓成分列表
        """
        if year is None:
            year = str(datetime.now().year)

        # 获取ETF持仓信息（使用fund_portfolio_hold_em）
        df = ak.fund_portfolio_hold_em(symbol=code, date=year)

        if df.empty:
            return []

        holdings = []
        for _, row in df.iterrows():
            holding = ETFHolding(
                stock_code=row['股票代码'],
                stock_name=row['股票名称'],
                weight=float(row['占净值比例']),
                shares=float(row['持股数']) if '持股数' in row else None,
                market_value=float(row['持仓市值']) if '持仓市值' in row else None
            )
            holdings.append(holding)

        return holdings

    @retry(max_attempts=2, delay=1.0)
    def get_net_value_history(
        self,
        code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[ETFNetValue]:
        """
        获取ETF净值历史

        Args:
            code: ETF代码
            start_date: 开始日期（格式：YYYY-MM-DD）
            end_date: 结束日期（格式：YYYY-MM-DD）

        Returns:
            净值历史列表
        """
        if end_date is None:
            end_date = datetime.now().strftime("%Y%m%d")
        else:
            end_date = end_date.replace("-", "")

        if start_date is None:
            start_date = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")
        else:
            start_date = start_date.replace("-", "")

        try:
            # 使用fund_etf_fund_info_em获取净值数据
            df = ak.fund_etf_fund_info_em(
                fund=code,
                start_date=start_date,
                end_date=end_date
            )

            if df.empty:
                return []

            net_values = []
            for _, row in df.iterrows():
                nav = ETFNetValue(
                    date=row['净值日期'],
                    unit_nav=float(row['单位净值']),
                    accumulated_nav=float(row['累计净值']),
                    daily_return=float(row['日增长率']) if '日增长率' in row else None
                )
                net_values.append(nav)

            return net_values
        except Exception as e:
            # 如果无法获取净值数据，返回空列表
            return []

    def calculate_premium_discount(
        self,
        code: str,
        days: int = 30
    ) -> List[ETFPremiumDiscount]:
        """
        计算ETF溢价/折价率

        Args:
            code: ETF代码
            days: 计算天数

        Returns:
            溢价/折价数据列表
        """
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")

        # 获取市价数据
        market_data = self.get_historical_data(code, start_date, end_date)

        # 获取净值数据
        net_value_data = self.get_net_value_history(code, start_date, end_date)

        # 合并数据计算溢价率
        premium_list = []

        net_value_dict = {nv.date: nv.unit_nav for nv in net_value_data}

        for _, row in market_data.iterrows():
            date_str = row['日期']
            market_price = float(row['收盘'])

            # 查找对应日期的净值
            net_value = net_value_dict.get(date_str)

            if net_value:
                premium_rate = ((market_price - net_value) / net_value) * 100

                premium_list.append(ETFPremiumDiscount(
                    date=date_str,
                    market_price=market_price,
                    net_value=net_value,
                    premium_rate=premium_rate
                ))

        return premium_list

    def search_etf(self, keyword: str) -> pd.DataFrame:
        """
        搜索ETF

        Args:
            keyword: 搜索关键词（代码或名称）

        Returns:
            匹配的ETF列表
        """
        df = self.get_etf_list()

        # 按代码或名称搜索
        result = df[
            df['代码'].str.contains(keyword, na=False) |
            df['名称'].str.contains(keyword, na=False)
        ]

        return result
