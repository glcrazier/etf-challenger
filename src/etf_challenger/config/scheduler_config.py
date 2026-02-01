"""
调度器配置管理

提供配置加载、验证、保存等功能。
"""

import logging
import os
import toml
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class SchedulerSettings:
    """调度器设置"""
    enabled: bool = True
    timezone: str = "Asia/Shanghai"


@dataclass
class WatchlistSettings:
    """监控列表设置"""
    pools: List[str] = field(default_factory=lambda: [
        "宽基指数",
        "医疗医药",
        "科技创新",
        "金融券商",
        "港股海外",
        "消费能源",
        "精选组合"
    ])


@dataclass
class ReportSettings:
    """报告设置"""
    formats: List[str] = field(default_factory=lambda: ["html", "markdown", "json"])
    analysis_days: int = 60
    include_holdings: bool = False
    include_premium: bool = True


@dataclass
class StorageSettings:
    """存储设置"""
    base_path: str = "~/.etf_challenger/reports"
    archive_after_days: int = 90
    max_storage_gb: int = 10

    def get_base_path(self) -> Path:
        """获取展开后的基础路径"""
        return Path(self.base_path).expanduser()


@dataclass
class EmailSettings:
    """邮件设置"""
    enabled: bool = True
    smtp_server: str = "smtp.163.com"
    smtp_port: int = 465
    use_ssl: bool = True
    sender_email: str = ""
    sender_password: str = ""
    recipients: List[str] = field(default_factory=list)
    send_daily_summary: bool = True
    send_immediate_alerts: bool = False

    def validate(self) -> List[str]:
        """
        验证邮件配置

        Returns:
            错误信息列表，空列表表示验证通过
        """
        errors = []

        if self.enabled:
            if not self.sender_email:
                errors.append("发件人邮箱未配置 (sender_email)")
            if not self.sender_password:
                errors.append("发件人授权码未配置 (sender_password)")
            if not self.recipients:
                errors.append("收件人列表为空 (recipients)")

        return errors


@dataclass
class MarketSettings:
    """市场设置"""
    morning_report_time: str = "10:00"
    afternoon_report_time: str = "14:30"


@dataclass
class LoggingSettings:
    """日志设置"""
    level: str = "INFO"
    file_path: str = "~/.etf_challenger/logs/scheduler.log"
    max_file_size_mb: int = 10
    backup_count: int = 5

    def get_file_path(self) -> Path:
        """获取展开后的日志文件路径"""
        return Path(self.file_path).expanduser()


@dataclass
class SchedulerConfig:
    """调度器完整配置"""
    scheduler: SchedulerSettings = field(default_factory=SchedulerSettings)
    watchlists: WatchlistSettings = field(default_factory=WatchlistSettings)
    report: ReportSettings = field(default_factory=ReportSettings)
    storage: StorageSettings = field(default_factory=StorageSettings)
    email: EmailSettings = field(default_factory=EmailSettings)
    market: MarketSettings = field(default_factory=MarketSettings)
    logging: LoggingSettings = field(default_factory=LoggingSettings)

    @classmethod
    def from_file(cls, config_path: Optional[Path] = None) -> 'SchedulerConfig':
        """
        从文件加载配置

        Args:
            config_path: 配置文件路径，默认为 ~/.etf_challenger/config/scheduler_config.toml

        Returns:
            配置对象
        """
        if config_path is None:
            config_path = Path.home() / '.etf_challenger' / 'config' / 'scheduler_config.toml'
        else:
            config_path = Path(config_path).expanduser()

        if not config_path.exists():
            logger.warning(f"配置文件不存在: {config_path}，使用默认配置")
            return cls.default()

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                data = toml.load(f)

            # 支持环境变量覆盖敏感信息
            if 'email' in data:
                data['email']['sender_email'] = os.getenv(
                    'ETF_SENDER_EMAIL',
                    data['email'].get('sender_email', '')
                )
                data['email']['sender_password'] = os.getenv(
                    'ETF_SENDER_PASSWORD',
                    data['email'].get('sender_password', '')
                )

            config = cls(
                scheduler=SchedulerSettings(**data.get('scheduler', {})),
                watchlists=WatchlistSettings(**data.get('watchlists', {})),
                report=ReportSettings(**data.get('report', {})),
                storage=StorageSettings(**data.get('storage', {})),
                email=EmailSettings(**data.get('email', {})),
                market=MarketSettings(**data.get('market', {})),
                logging=LoggingSettings(**data.get('logging', {})),
            )

            logger.info(f"已从 {config_path} 加载配置")
            return config

        except Exception as e:
            logger.error(f"加载配置文件失败: {e}，使用默认配置")
            return cls.default()

    @classmethod
    def default(cls) -> 'SchedulerConfig':
        """
        获取默认配置

        Returns:
            默认配置对象
        """
        return cls()

    def save(self, config_path: Optional[Path] = None):
        """
        保存配置到文件

        Args:
            config_path: 配置文件路径，默认为 ~/.etf_challenger/config/scheduler_config.toml
        """
        if config_path is None:
            config_path = Path.home() / '.etf_challenger' / 'config' / 'scheduler_config.toml'
        else:
            config_path = Path(config_path).expanduser()

        # 创建目录
        config_path.parent.mkdir(parents=True, exist_ok=True)

        # 转换为字典
        data = {
            'scheduler': {
                'enabled': self.scheduler.enabled,
                'timezone': self.scheduler.timezone,
            },
            'watchlists': {
                'pools': self.watchlists.pools,
            },
            'report': {
                'formats': self.report.formats,
                'analysis_days': self.report.analysis_days,
                'include_holdings': self.report.include_holdings,
                'include_premium': self.report.include_premium,
            },
            'storage': {
                'base_path': self.storage.base_path,
                'archive_after_days': self.storage.archive_after_days,
                'max_storage_gb': self.storage.max_storage_gb,
            },
            'email': {
                'enabled': self.email.enabled,
                'smtp_server': self.email.smtp_server,
                'smtp_port': self.email.smtp_port,
                'use_ssl': self.email.use_ssl,
                'sender_email': self.email.sender_email,
                'sender_password': self.email.sender_password,
                'recipients': self.email.recipients,
                'send_daily_summary': self.email.send_daily_summary,
                'send_immediate_alerts': self.email.send_immediate_alerts,
            },
            'market': {
                'morning_report_time': self.market.morning_report_time,
                'afternoon_report_time': self.market.afternoon_report_time,
            },
            'logging': {
                'level': self.logging.level,
                'file_path': self.logging.file_path,
                'max_file_size_mb': self.logging.max_file_size_mb,
                'backup_count': self.logging.backup_count,
            },
        }

        with open(config_path, 'w', encoding='utf-8') as f:
            toml.dump(data, f)

        logger.info(f"配置已保存到: {config_path}")

    def validate(self) -> List[str]:
        """
        验证配置

        Returns:
            错误信息列表，空列表表示验证通过
        """
        errors = []

        # 验证邮件配置
        email_errors = self.email.validate()
        errors.extend(email_errors)

        # 验证监控池
        if not self.watchlists.pools:
            errors.append("监控池列表为空")

        # 验证报告格式
        valid_formats = {'html', 'markdown', 'json'}
        invalid_formats = set(self.report.formats) - valid_formats
        if invalid_formats:
            errors.append(f"无效的报告格式: {invalid_formats}")

        return errors
