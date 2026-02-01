"""
守护进程管理

将调度器作为后台进程运行。
"""

import logging
import os
import signal
import sys
import time
from pathlib import Path

logger = logging.getLogger(__name__)


class MonitorDaemon:
    """
    监控守护进程

    功能:
    - 将调度器作为后台进程运行
    - 处理信号（SIGTERM, SIGINT）优雅关闭
    - 记录PID文件
    """

    def __init__(self, config_path: str = None):
        """
        初始化守护进程

        Args:
            config_path: 配置文件路径
        """
        self.config_path = config_path
        self.pidfile = Path.home() / '.etf_challenger' / 'scheduler.pid'
        self.scheduler = None

    def start(self):
        """启动守护进程"""
        # 检查是否已经在运行
        if self._is_running():
            logger.error("守护进程已在运行")
            return False

        logger.info("启动守护进程...")

        # 创建守护进程
        try:
            # Fork第一次
            pid = os.fork()
            if pid > 0:
                # 父进程退出
                sys.exit(0)
        except OSError as e:
            logger.error(f"Fork失败: {e}")
            sys.exit(1)

        # 脱离父进程环境
        os.chdir('/')
        os.setsid()
        os.umask(0)

        # Fork第二次
        try:
            pid = os.fork()
            if pid > 0:
                # 父进程退出
                sys.exit(0)
        except OSError as e:
            logger.error(f"Fork失败: {e}")
            sys.exit(1)

        # 重定向标准输入输出
        sys.stdout.flush()
        sys.stderr.flush()

        log_dir = Path.home() / '.etf_challenger' / 'logs'
        log_dir.mkdir(parents=True, exist_ok=True)

        with open(log_dir / 'stdout.log', 'a') as stdout_file:
            os.dup2(stdout_file.fileno(), sys.stdout.fileno())

        with open(log_dir / 'stderr.log', 'a') as stderr_file:
            os.dup2(stderr_file.fileno(), sys.stderr.fileno())

        # 注册信号处理
        signal.signal(signal.SIGTERM, self._shutdown)
        signal.signal(signal.SIGINT, self._shutdown)

        # 写入PID文件
        self._write_pidfile()

        # 运行调度器
        self._run()

    def stop(self):
        """停止守护进程"""
        if not self.pidfile.exists():
            logger.error("PID文件不存在，守护进程可能未运行")
            return False

        try:
            with open(self.pidfile, 'r') as f:
                pid = int(f.read().strip())

            # 发送SIGTERM信号
            os.kill(pid, signal.SIGTERM)

            # 等待进程退出
            for _ in range(10):
                try:
                    os.kill(pid, 0)
                    time.sleep(0.5)
                except OSError:
                    # 进程已退出
                    break

            # 删除PID文件
            self.pidfile.unlink(missing_ok=True)

            logger.info("守护进程已停止")
            return True

        except Exception as e:
            logger.error(f"停止守护进程失败: {e}")
            return False

    def _run(self):
        """运行调度器（主循环）"""
        from ..config.scheduler_config import SchedulerConfig
        from ..scheduler.job_scheduler import ReportScheduler

        logger.info("守护进程已启动")

        try:
            # 加载配置
            config = SchedulerConfig.from_file(self.config_path)

            # 创建并启动调度器
            self.scheduler = ReportScheduler(config)
            self.scheduler.start()

            # 保持运行
            while True:
                time.sleep(1)

        except Exception as e:
            logger.error(f"守护进程运行失败: {e}", exc_info=True)
            sys.exit(1)

    def _shutdown(self, signum, frame):
        """优雅关闭"""
        logger.info(f"收到信号 {signum}，正在关闭...")

        if self.scheduler:
            self.scheduler.stop()

        # 删除PID文件
        self.pidfile.unlink(missing_ok=True)

        logger.info("守护进程已关闭")
        sys.exit(0)

    def _write_pidfile(self):
        """写入PID文件"""
        self.pidfile.parent.mkdir(parents=True, exist_ok=True)

        with open(self.pidfile, 'w') as f:
            f.write(str(os.getpid()))

    def _is_running(self) -> bool:
        """检查守护进程是否正在运行"""
        if not self.pidfile.exists():
            return False

        try:
            with open(self.pidfile, 'r') as f:
                pid = int(f.read().strip())

            # 检查进程是否存在
            os.kill(pid, 0)
            return True

        except (OSError, ValueError):
            # 进程不存在或PID文件损坏
            self.pidfile.unlink(missing_ok=True)
            return False

    def get_status(self) -> dict:
        """
        获取守护进程状态

        Returns:
            状态字典
        """
        if not self._is_running():
            return {
                'running': False,
                'pid': None
            }

        with open(self.pidfile, 'r') as f:
            pid = int(f.read().strip())

        return {
            'running': True,
            'pid': pid
        }
