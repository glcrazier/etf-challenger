"""ETF筛选器 - 基于流动性和费率筛选ETF"""

import akshare as ak
import pandas as pd
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from ..utils.retry import retry


@dataclass
class ETFScreeningResult:
    """ETF筛选结果"""
    code: str
    name: str
    exchange: str  # SSE/SZSE
    scale: float  # 基金份额(亿份)
    avg_volume: Optional[float] = None  # 平均成交量(万手)
    avg_amount: Optional[float] = None  # 平均成交额(亿元)
    liquidity_score: float = 0.0  # 流动性评分(0-100)
    fund_manager: Optional[str] = None  # 基金管理人
    list_date: Optional[str] = None  # 上市日期


class ETFScreener:
    """ETF筛选器"""

    def __init__(self):
        """初始化筛选器"""
        # ETF费率数据(手动维护的常见费率,年化)
        # 数据来源: 各基金公司官网
        self.fee_rates = {
            # 宽基指数ETF (费率通常较低)
            '510300': 0.50,  # 沪深300ETF - 管理费0.50%
            '510500': 0.50,  # 中证500ETF
            '159915': 0.50,  # 创业板ETF
            '588000': 0.50,  # 科创50ETF
            '510050': 0.50,  # 上证50ETF
            '159919': 0.50,  # 沪深300ETF
            '512880': 0.50,  # 证券公司ETF
            '515000': 0.15,  # 科创板50ETF (低费率)

            # 行业主题ETF (费率通常稍高)
            '512690': 0.80,  # 白酒ETF
            '512480': 0.80,  # 半导体ETF
            '159928': 0.60,  # 消费ETF
            '512290': 0.60,  # 医药ETF
            '515880': 0.60,  # 通信设备ETF
            '512980': 0.60,  # 传媒ETF

            # 默认费率
            'default': 0.60  # 默认管理费率
        }

    @retry(max_attempts=3, delay=1.0)
    def get_etf_scale_data(self) -> pd.DataFrame:
        """
        获取ETF规模数据(合并上交所和深交所)

        Returns:
            包含ETF规模信息的DataFrame
        """
        all_etfs = []

        # 获取上交所ETF规模
        try:
            sse_df = ak.fund_etf_scale_sse()
            # 规范化字段名
            sse_df = sse_df.rename(columns={
                '基金代码': 'code',
                '基金简称': 'name',
                'ETF类型': 'type',
                '基金份额': 'scale',
                '统计日期': 'date'
            })
            sse_df['exchange'] = 'SSE'
            sse_df['fund_manager'] = None
            sse_df['list_date'] = None
            all_etfs.append(sse_df[['code', 'name', 'exchange', 'scale', 'fund_manager', 'list_date']])
        except Exception as e:
            print(f"警告: 获取上交所ETF规模失败 - {e}")

        # 获取深交所ETF规模
        try:
            szse_df = ak.fund_etf_scale_szse()
            # 规范化字段名
            szse_df = szse_df.rename(columns={
                '基金代码': 'code',
                '基金简称': 'name',
                '基金类别': 'type',
                '基金份额': 'scale',
                '基金管理人': 'fund_manager',
                '上市日期': 'list_date'
            })
            szse_df['exchange'] = 'SZSE'
            all_etfs.append(szse_df[['code', 'name', 'exchange', 'scale', 'fund_manager', 'list_date']])
        except Exception as e:
            print(f"警告: 获取深交所ETF规模失败 - {e}")

        if not all_etfs:
            raise Exception("无法获取任何ETF规模数据")

        # 合并数据
        combined_df = pd.concat(all_etfs, ignore_index=True)

        # 转换份额为亿份
        combined_df['scale'] = combined_df['scale'] / 100000000

        return combined_df

    def calculate_liquidity_from_history(
        self,
        code: str,
        days: int = 30
    ) -> Dict[str, float]:
        """
        从历史数据计算流动性指标

        Args:
            code: ETF代码
            days: 计算天数

        Returns:
            包含avg_volume和avg_amount的字典
        """
        try:
            end_date = datetime.now().strftime("%Y%m%d")
            start_date = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")

            df = ak.fund_etf_hist_em(
                symbol=code,
                period="daily",
                start_date=start_date,
                end_date=end_date,
                adjust="qfq"
            )

            if df.empty or '成交量' not in df.columns:
                return {'avg_volume': None, 'avg_amount': None}

            # 计算平均成交量(万手)和平均成交额(亿元)
            avg_volume = df['成交量'].mean() / 10000 if '成交量' in df.columns else None
            avg_amount = df['成交额'].mean() / 100000000 if '成交额' in df.columns else None

            return {
                'avg_volume': avg_volume,
                'avg_amount': avg_amount
            }
        except Exception:
            # 历史数据获取失败时返回None
            return {'avg_volume': None, 'avg_amount': None}

    def calculate_liquidity_score(
        self,
        scale: float,
        avg_amount: Optional[float] = None
    ) -> float:
        """
        计算流动性评分(0-100分)

        评分依据:
        1. 基金规模(70%权重) - 规模越大流动性越好
        2. 平均成交额(30%权重) - 成交越活跃流动性越好

        Args:
            scale: 基金份额(亿份)
            avg_amount: 平均成交额(亿元)

        Returns:
            流动性评分(0-100)
        """
        score = 0.0

        # 基金规模评分(70分)
        if scale >= 100:
            score += 70
        elif scale >= 50:
            score += 60
        elif scale >= 20:
            score += 50
        elif scale >= 10:
            score += 40
        elif scale >= 5:
            score += 30
        elif scale >= 2:
            score += 20
        else:
            score += scale * 10  # 小规模按比例给分

        # 平均成交额评分(30分)
        if avg_amount is not None:
            if avg_amount >= 10:
                score += 30
            elif avg_amount >= 5:
                score += 25
            elif avg_amount >= 2:
                score += 20
            elif avg_amount >= 1:
                score += 15
            elif avg_amount >= 0.5:
                score += 10
            else:
                score += avg_amount * 20
        else:
            # 如果没有成交额数据,规模评分权重提升到100%
            score = score / 0.7

        return min(100, score)

    def get_fee_rate(self, code: str) -> float:
        """
        获取ETF费率(管理费率)

        Args:
            code: ETF代码

        Returns:
            年化管理费率(%)
        """
        return self.fee_rates.get(code, self.fee_rates['default'])

    def extract_index_name(self, etf_name: str) -> str:
        """
        从ETF名称中提取指数类型

        Args:
            etf_name: ETF名称

        Returns:
            指数类型标识(归一化后)
        """
        # 常见指数映射表(按匹配优先级排序,越具体的越靠前)
        index_patterns = [
            ('创业板50', ['创业板50']),
            ('科创50', ['科创50', '科创板50', 'KC50']),
            ('半导体50', ['半导体50']),
            ('沪深300', ['沪深300', '300ETF', 'HS300']),
            ('中证500', ['中证500', '500ETF', 'ZZ500']),
            ('上证50', ['上证50', '50ETF']),
            ('创业板', ['创业板', '创业板指', 'CYBZ']),
            ('科创板', ['科创板', '科创ETF']),
            ('红利', ['红利', '股息']),
            ('券商', ['证券', '券商']),
            ('银行', ['银行']),
            ('地产', ['地产', '房地产']),
            ('消费', ['消费', '内需']),
            ('医药', ['医药', '医疗', '生物']),
            ('科技', ['科技']),
            ('半导体', ['半导体', '芯片']),
            ('通信', ['通信', '5G']),
            ('军工', ['军工', '国防']),
            ('新能源', ['新能源', '光伏', '锂电']),
            ('白酒', ['白酒', '酒ETF']),
            ('传媒', ['传媒', '文化']),
            ('环保', ['环保']),
            ('有色', ['有色金属', '有色']),
            ('钢铁', ['钢铁']),
            ('煤炭', ['煤炭']),
            ('石油', ['石油', '油气']),
            ('黄金', ['黄金', '黄金ETF']),
            ('恒生', ['恒生', 'HSI']),
            ('纳斯达克', ['纳斯达克', 'NASDAQ', 'NDX']),
            ('标普', ['标普500', 'S&P']),
        ]

        # 提取指数名称(优先匹配更具体的模式)
        for index_type, patterns in index_patterns:
            for pattern in patterns:
                if pattern in etf_name:
                    return index_type

        # 如果没有匹配到,返回原名称(去除"ETF"等后缀)
        clean_name = etf_name.replace('ETF', '').replace('LOF', '').replace('联接', '').strip()
        return clean_name

    def screen_etfs(
        self,
        top_n: int = 10,
        min_scale: float = 5.0,
        max_fee_rate: float = 0.60,
        include_volume: bool = True,
        etf_type: str = '股票',
        dedup_by_index: bool = True
    ) -> List[ETFScreeningResult]:
        """
        筛选ETF

        Args:
            top_n: 返回前N支
            min_scale: 最小规模(亿份)
            max_fee_rate: 最大费率(%)
            include_volume: 是否包含成交量分析(耗时较长)
            etf_type: ETF类型筛选('股票'/'债券'/'货币'/None表示全部)
            dedup_by_index: 是否按指数去重(相同指数只保留一支)

        Returns:
            筛选结果列表
        """
        # 获取ETF规模数据
        scale_df = self.get_etf_scale_data()

        # 筛选条件1: 最小规模
        scale_df = scale_df[scale_df['scale'] >= min_scale]

        # 筛选条件2: 股票型ETF
        if etf_type:
            # 通过名称简单过滤(包含"股票"或常见股票ETF关键词)
            stock_keywords = ['ETF', 'etf']  # 基本上所有ETF都包含这个
            # 排除货币、债券类
            exclude_keywords = ['货币', '债', '理财', '短融']

            mask = scale_df['name'].str.contains('|'.join(stock_keywords), na=False)
            for keyword in exclude_keywords:
                mask &= ~scale_df['name'].str.contains(keyword, na=False)

            scale_df = scale_df[mask]

        # 按规模排序取前top_n*3支(用于后续详细分析)
        candidate_count = min(top_n * 3, len(scale_df))
        candidates = scale_df.nlargest(candidate_count, 'scale')

        results = []

        for _, row in candidates.iterrows():
            code = row['code']

            # 检查费率
            fee_rate = self.get_fee_rate(code)
            if fee_rate > max_fee_rate:
                continue

            # 获取成交量数据(可选)
            liquidity_data = {'avg_volume': None, 'avg_amount': None}
            if include_volume:
                liquidity_data = self.calculate_liquidity_from_history(code, days=30)

            # 计算流动性评分
            liquidity_score = self.calculate_liquidity_score(
                row['scale'],
                liquidity_data['avg_amount']
            )

            result = ETFScreeningResult(
                code=code,
                name=row['name'],
                exchange=row['exchange'],
                scale=row['scale'],
                avg_volume=liquidity_data['avg_volume'],
                avg_amount=liquidity_data['avg_amount'],
                liquidity_score=liquidity_score,
                fund_manager=row.get('fund_manager'),
                list_date=row.get('list_date')
            )
            results.append(result)

        # 按流动性评分排序,取前top_n支
        results.sort(key=lambda x: x.liquidity_score, reverse=True)

        # 按指数去重(相同指数只保留评分最高的一支)
        if dedup_by_index:
            deduplicated = []
            seen_indexes = set()

            for result in results:
                index_name = self.extract_index_name(result.name)

                # 如果该指数还没出现过,则加入结果
                if index_name not in seen_indexes:
                    deduplicated.append(result)
                    seen_indexes.add(index_name)

                    # 达到数量上限则停止
                    if len(deduplicated) >= top_n:
                        break

            return deduplicated
        else:
            return results[:top_n]
