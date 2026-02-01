"""
邮件发送服务

提供SMTP邮件发送功能，支持163邮箱。
"""

import logging
import smtplib
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from typing import List, Optional

from ..config.scheduler_config import EmailSettings
from ..utils.retry import retry

logger = logging.getLogger(__name__)


class EmailService:
    """
    邮件发送服务

    支持:
    - 163邮箱SMTP
    - HTML格式邮件
    - 附件发送
    - 自动重试
    """

    def __init__(self, config: EmailSettings):
        """
        初始化邮件服务

        Args:
            config: 邮件配置
        """
        self.config = config

        # 验证配置
        errors = config.validate()
        if errors:
            raise ValueError(f"邮件配置错误: {', '.join(errors)}")

        logger.info(f"邮件服务已初始化 (SMTP: {config.smtp_server}:{config.smtp_port})")

    @retry(max_attempts=5, delay=1.0, backoff=2.0)
    def send_email(
        self,
        subject: str,
        body: str,
        body_type: str = 'html',
        attachments: Optional[List[Path]] = None
    ):
        """
        发送邮件

        Args:
            subject: 邮件主题
            body: 邮件正文
            body_type: 正文类型 ('html' 或 'plain')
            attachments: 附件路径列表

        Raises:
            smtplib.SMTPException: 邮件发送失败
        """
        if not self.config.enabled:
            logger.info("邮件功能已禁用，跳过发送")
            return

        logger.info(f"准备发送邮件: {subject}")

        # 创建邮件
        msg = MIMEMultipart()
        msg['From'] = self.config.sender_email
        msg['To'] = ', '.join(self.config.recipients)
        msg['Subject'] = subject

        # 添加正文
        msg.attach(MIMEText(body, body_type, 'utf-8'))

        # 添加附件
        if attachments:
            for file_path in attachments:
                if file_path.exists():
                    self._attach_file(msg, file_path)

        # 发送邮件
        try:
            if self.config.use_ssl:
                server = smtplib.SMTP_SSL(self.config.smtp_server, self.config.smtp_port, timeout=30)
            else:
                server = smtplib.SMTP(self.config.smtp_server, self.config.smtp_port, timeout=30)
                server.starttls()

            server.login(self.config.sender_email, self.config.sender_password)
            server.send_message(msg)
            server.quit()

            logger.info(f"邮件发送成功: {subject}")

        except smtplib.SMTPAuthenticationError as e:
            logger.error("邮箱认证失败，请检查邮箱地址和授权码")
            logger.error("提示: 163邮箱需要使用授权码，不是登录密码")
            logger.error("获取授权码: 登录163邮箱 -> 设置 -> POP3/SMTP/IMAP -> 开启服务 -> 获取授权码")
            raise

        except smtplib.SMTPException as e:
            logger.error(f"邮件发送失败: {e}")
            raise

    def _attach_file(self, msg: MIMEMultipart, file_path: Path):
        """
        添加附件到邮件

        Args:
            msg: 邮件对象
            file_path: 附件路径
        """
        try:
            with open(file_path, 'rb') as f:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(f.read())

            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename= {file_path.name}'
            )

            msg.attach(part)
            logger.debug(f"已添加附件: {file_path.name}")

        except Exception as e:
            logger.warning(f"添加附件失败 {file_path}: {e}")

    def send_test_email(self):
        """
        发送测试邮件

        用于验证邮件配置是否正确
        """
        subject = "[ETF监控] 测试邮件"
        body = """
        <html>
        <body>
            <h2>ETF监控系统测试邮件</h2>
            <p>如果您收到这封邮件，说明邮件配置成功!</p>
            <p><strong>配置信息:</strong></p>
            <ul>
                <li>发件人: {sender}</li>
                <li>SMTP服务器: {smtp_server}:{smtp_port}</li>
                <li>发送时间: {time}</li>
            </ul>
            <p>ETF Challenger - 智能ETF分析工具</p>
        </body>
        </html>
        """.format(
            sender=self.config.sender_email,
            smtp_server=self.config.smtp_server,
            smtp_port=self.config.smtp_port,
            time=time.strftime('%Y-%m-%d %H:%M:%S')
        )

        self.send_email(subject, body, body_type='html')
        logger.info("测试邮件已发送")
