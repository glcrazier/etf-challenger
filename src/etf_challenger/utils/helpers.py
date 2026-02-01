"""工具函数"""

from datetime import datetime
from typing import Optional


def format_number(value: float, decimal: int = 2) -> str:
    """
    格式化数字显示

    Args:
        value: 数值
        decimal: 小数位数

    Returns:
        格式化后的字符串
    """
    if abs(value) >= 1e8:
        return f"{value / 1e8:.{decimal}f}亿"
    elif abs(value) >= 1e4:
        return f"{value / 1e4:.{decimal}f}万"
    else:
        return f"{value:.{decimal}f}"


def format_percentage(value: float, decimal: int = 2, with_sign: bool = True) -> str:
    """
    格式化百分比显示

    Args:
        value: 百分比数值
        decimal: 小数位数
        with_sign: 是否显示正负号

    Returns:
        格式化后的字符串
    """
    sign = "+" if value > 0 and with_sign else ""
    return f"{sign}{value:.{decimal}f}%"


def parse_date(date_str: str, default_format: str = "%Y-%m-%d") -> Optional[datetime]:
    """
    解析日期字符串

    Args:
        date_str: 日期字符串
        default_format: 默认日期格式

    Returns:
        datetime对象，解析失败返回None
    """
    formats = [
        default_format,
        "%Y%m%d",
        "%Y/%m/%d",
        "%Y-%m-%d %H:%M:%S"
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue

    return None


def validate_etf_code(code: str) -> bool:
    """
    验证ETF代码格式

    Args:
        code: ETF代码

    Returns:
        是否有效
    """
    # A股ETF代码通常是6位数字
    return code.isdigit() and len(code) == 6


def get_color_by_value(value: float) -> str:
    """
    根据数值获取颜色（用于终端显示）

    Args:
        value: 数值

    Returns:
        颜色名称
    """
    if value > 0:
        return "green"
    elif value < 0:
        return "red"
    else:
        return "white"
