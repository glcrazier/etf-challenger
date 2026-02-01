"""
ETF监控通知模块

提供邮件发送、报告摘要生成等功能。
"""

from .email_service import EmailService
from .report_digest import ReportDigest

__all__ = [
    "EmailService",
    "ReportDigest",
]
