"""
定时任务调度器

使用APScheduler管理定时报告生成任务。
"""

import logging
from datetime import datetime
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.executors.pool import ThreadPoolExecutor

from ..config.scheduler_config import SchedulerConfig
from ..notification.email_service import EmailService
from ..notification.report_digest import ReportDigest
from ..scheduler.trading_calendar import TradingCalendar
from ..scheduler.report_job import ReportJob

logger = logging.getLogger(__name__)


class ReportScheduler:
    """
    报告定时调度器

    功能:
    - 每个交易日10:00和14:30自动生成报告
    - 自动跳过非交易日
    - 持久化任务状态
    - 支持启动、停止、查看状态
    """

    def __init__(self, config: SchedulerConfig):
        """
        初始化调度器

        Args:
            config: 调度器配置
        """
        self.config = config
        self.calendar = TradingCalendar()
        self.report_job = ReportJob(config)

        # 初始化邮件服务（如果启用）
        self.email_service = None
        if config.email.enabled:
            try:
                self.email_service = EmailService(config.email)
            except Exception as e:
                logger.warning(f"邮件服务初始化失败: {e}，将禁用邮件功能")

        # 配置APScheduler (使用内存jobstore，简单可靠)
        executors = {
            'default': ThreadPoolExecutor(3)
        }

        job_defaults = {
            'coalesce': False,
            'max_instances': 1
        }

        self.scheduler = BackgroundScheduler(
            executors=executors,
            job_defaults=job_defaults,
            timezone='Asia/Shanghai'
        )

        logger.info("报告调度器已初始化")

    def start(self):
        """启动调度器"""
        if not self.config.scheduler.enabled:
            logger.warning("调度器已禁用，无法启动")
            return

        # 解析报告时间
        morning_time = self.config.market.morning_report_time.split(':')
        afternoon_time = self.config.market.afternoon_report_time.split(':')

        # 添加早盘报告任务
        self.scheduler.add_job(
            func=self._execute_morning_report,
            trigger=CronTrigger(
                hour=int(morning_time[0]),
                minute=int(morning_time[1]),
                timezone='Asia/Shanghai'
            ),
            id='morning_report',
            name='早盘报告生成',
            replace_existing=True
        )

        # 添加尾盘报告任务
        self.scheduler.add_job(
            func=self._execute_afternoon_report,
            trigger=CronTrigger(
                hour=int(afternoon_time[0]),
                minute=int(afternoon_time[1]),
                timezone='Asia/Shanghai'
            ),
            id='afternoon_report',
            name='尾盘报告生成',
            replace_existing=True
        )

        self.scheduler.start()
        logger.info("调度器已启动")
        logger.info(f"早盘报告: 每个交易日 {self.config.market.morning_report_time}")
        logger.info(f"尾盘报告: 每个交易日 {self.config.market.afternoon_report_time}")

    def stop(self):
        """停止调度器"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("调度器已停止")

    def _execute_morning_report(self):
        """执行早盘报告（带交易日检查）"""
        if not self.calendar.is_trading_day(datetime.now()):
            logger.info("今日非交易日，跳过早盘报告")
            return

        logger.info("开始生成早盘报告...")

        try:
            result = self.report_job.execute(session='morning')

            # 发送邮件通知
            if result.success and self.email_service and self.config.email.send_daily_summary:
                self._send_email_notification('morning', result)

            logger.info(f"早盘报告生成完成: {result}")

        except Exception as e:
            logger.error(f"早盘报告生成失败: {e}", exc_info=True)
            self._send_error_notification('morning', str(e))

    def _execute_afternoon_report(self):
        """执行尾盘报告（带交易日检查）"""
        if not self.calendar.is_trading_day(datetime.now()):
            logger.info("今日非交易日，跳过尾盘报告")
            return

        logger.info("开始生成尾盘报告...")

        try:
            result = self.report_job.execute(session='afternoon')

            # 发送邮件通知
            if result.success and self.email_service and self.config.email.send_daily_summary:
                self._send_email_notification('afternoon', result)

            logger.info(f"尾盘报告生成完成: {result}")

        except Exception as e:
            logger.error(f"尾盘报告生成失败: {e}", exc_info=True)
            self._send_error_notification('afternoon', str(e))

    def _send_email_notification(self, session: str, result):
        """
        发送邮件通知

        Args:
            session: 时段
            result: 报告生成结果
        """
        try:
            # 读取汇总数据
            from ..storage.report_storage import ReportStorage
            storage = ReportStorage(self.config.storage.get_base_path())
            summary_data = storage.get_summary(datetime.now(), session)

            if not summary_data:
                logger.warning("未找到汇总数据，无法发送邮件")
                return

            # 生成邮件内容
            session_cn = '早盘' if session == 'morning' else '尾盘'
            subject = f"[ETF监控] {datetime.now():%Y-%m-%d} {session_cn}报告"

            html_content = ReportDigest.generate_html_digest(
                session=session,
                recommendations=summary_data.get('recommendations', []),
                pools=self.config.watchlists.pools
            )

            # 发送邮件
            self.email_service.send_email(
                subject=subject,
                body=html_content,
                body_type='html'
            )

            logger.info(f"{session_cn}报告邮件已发送")

        except Exception as e:
            logger.error(f"发送邮件失败: {e}", exc_info=True)

    def _send_error_notification(self, session: str, error_message: str):
        """
        发送错误通知邮件

        Args:
            session: 时段
            error_message: 错误信息
        """
        if not self.email_service:
            return

        try:
            session_cn = '早盘' if session == 'morning' else '尾盘'
            subject = f"[ETF监控] {datetime.now():%Y-%m-%d} {session_cn}报告生成失败"

            body = f"""
            <html>
            <body>
                <h2>报告生成失败通知</h2>
                <p><strong>时段:</strong> {session_cn}</p>
                <p><strong>时间:</strong> {datetime.now():%Y-%m-%d %H:%M:%S}</p>
                <p><strong>错误信息:</strong></p>
                <pre>{error_message}</pre>
                <p>请检查日志文件以获取详细信息。</p>
            </body>
            </html>
            """

            self.email_service.send_email(
                subject=subject,
                body=body,
                body_type='html'
            )

        except Exception as e:
            logger.error(f"发送错误通知邮件失败: {e}")

    def get_status(self) -> dict:
        """
        获取调度器状态

        Returns:
            状态字典
        """
        jobs = self.scheduler.get_jobs()

        return {
            'running': self.scheduler.running,
            'jobs': [
                {
                    'id': job.id,
                    'name': job.name,
                    'next_run': job.next_run_time,
                    'trigger': str(job.trigger)
                }
                for job in jobs
            ]
        }
