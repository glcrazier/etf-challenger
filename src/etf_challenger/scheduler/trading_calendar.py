"""
中国A股交易日历管理

提供交易日判断、市场时间管理、节假日更新等功能。
"""

import logging
from datetime import datetime, time, timedelta
from typing import Optional

logger = logging.getLogger(__name__)


class TradingCalendar:
    """
    中国A股交易日历

    特性:
    - 判断是否为交易日（排除周末和节假日）
    - 获取市场开盘/收盘时间
    - 计算报告生成时间点
    """

    # 市场交易时间
    MARKET_HOURS = {
        'morning_open': time(9, 30),
        'morning_close': time(11, 30),
        'afternoon_open': time(13, 0),
        'afternoon_close': time(15, 0),
    }

    # 报告生成时间
    REPORT_TIMES = {
        'morning': time(10, 0),      # 开盘后30分钟
        'afternoon': time(14, 30),   # 收盘前30分钟
    }

    # 2026年节假日（根据国务院办公厅2025年11月4日通知）
    # 只列出工作日休市日期，周末本身不交易无需列入
    HOLIDAYS_2026 = [
        # 元旦: 1月1日(四)-3日，休市工作日：1-2日
        '2026-01-01', '2026-01-02',

        # 春节: 2月15日(日)-23日(一)，休市工作日：16-20日、23日
        '2026-02-16', '2026-02-17', '2026-02-18', '2026-02-19', '2026-02-20', '2026-02-23',

        # 清明节: 4月4日(六)-6日(一)，休市工作日：6日
        '2026-04-06',

        # 劳动节: 5月1日(五)-5日(二)，休市工作日：1日、4-5日
        '2026-05-01', '2026-05-04', '2026-05-05',

        # 端午节: 6月19日(五)-21日(日)，休市工作日：19日
        '2026-06-19',

        # 中秋节: 9月25日(五)-27日(日)，休市工作日：25日
        '2026-09-25',

        # 国庆节: 10月1日(四)-7日(三)，休市工作日：1-2日、5-7日
        '2026-10-01', '2026-10-02', '2026-10-05', '2026-10-06', '2026-10-07',
    ]

    def __init__(self):
        """初始化交易日历"""
        self.holidays = set(self.HOLIDAYS_2026)
        logger.info(f"交易日历已加载，包含{len(self.holidays)}个节假日")

    def is_trading_day(self, date: Optional[datetime] = None) -> bool:
        """
        判断是否为交易日

        Args:
            date: 要检查的日期，默认为今天

        Returns:
            是否为交易日
        """
        if date is None:
            date = datetime.now()

        # 检查是否为周末
        if date.weekday() >= 5:  # 5=周六, 6=周日
            return False

        # 检查是否为节假日
        date_str = date.strftime('%Y-%m-%d')
        if date_str in self.holidays:
            return False

        return True

    def is_market_open(self, dt: Optional[datetime] = None) -> bool:
        """
        判断市场是否开盘

        Args:
            dt: 要检查的时间，默认为现在

        Returns:
            市场是否开盘
        """
        if dt is None:
            dt = datetime.now()

        # 首先检查是否为交易日
        if not self.is_trading_day(dt):
            return False

        current_time = dt.time()

        # 检查是否在交易时段内
        morning_open = self.MARKET_HOURS['morning_open'] <= current_time <= self.MARKET_HOURS['morning_close']
        afternoon_open = self.MARKET_HOURS['afternoon_open'] <= current_time <= self.MARKET_HOURS['afternoon_close']

        return morning_open or afternoon_open

    def get_report_time(self, session: str) -> time:
        """
        获取报告生成时间

        Args:
            session: 'morning' 或 'afternoon'

        Returns:
            报告生成时间
        """
        if session not in self.REPORT_TIMES:
            raise ValueError(f"无效的session: {session}，应为'morning'或'afternoon'")

        return self.REPORT_TIMES[session]

    def get_next_trading_day(self, date: Optional[datetime] = None) -> datetime:
        """
        获取下一个交易日

        Args:
            date: 起始日期，默认为今天

        Returns:
            下一个交易日
        """
        if date is None:
            date = datetime.now()

        next_day = date + timedelta(days=1)

        # 最多查找30天
        for _ in range(30):
            if self.is_trading_day(next_day):
                return next_day
            next_day += timedelta(days=1)

        raise ValueError("未找到下一个交易日（30天内）")

    def get_previous_trading_day(self, date: Optional[datetime] = None) -> datetime:
        """
        获取上一个交易日

        Args:
            date: 起始日期，默认为今天

        Returns:
            上一个交易日
        """
        if date is None:
            date = datetime.now()

        prev_day = date - timedelta(days=1)

        # 最多查找30天
        for _ in range(30):
            if self.is_trading_day(prev_day):
                return prev_day
            prev_day -= timedelta(days=1)

        raise ValueError("未找到上一个交易日（30天内）")

    def update_holidays(self, holidays: list[str]):
        """
        更新节假日列表

        Args:
            holidays: 节假日列表，格式为 'YYYY-MM-DD'
        """
        self.holidays = set(holidays)
        logger.info(f"节假日列表已更新，共{len(self.holidays)}个")

    def add_holiday(self, date_str: str):
        """
        添加单个节假日

        Args:
            date_str: 日期字符串，格式为 'YYYY-MM-DD'
        """
        self.holidays.add(date_str)
        logger.info(f"已添加节假日: {date_str}")

    def remove_holiday(self, date_str: str):
        """
        移除单个节假日（用于调休补班）

        Args:
            date_str: 日期字符串，格式为 'YYYY-MM-DD'
        """
        if date_str in self.holidays:
            self.holidays.remove(date_str)
            logger.info(f"已移除节假日: {date_str}")
