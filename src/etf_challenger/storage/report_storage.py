"""
报告文件存储管理

提供报告文件组织、存储、查询、归档等功能。
"""

import json
import logging
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ReportStorage:
    """
    报告存储管理器

    报告目录结构:
    ~/.etf_challenger/reports/
        daily/
            2026/
                02/
                    01/
                        morning/
                            宽基指数_20260201_1000.html
                            宽基指数_20260201_1000.md
                            宽基指数_20260201_1000.json
                            summary_morning.json
                        afternoon/
                            ...
    """

    def __init__(self, base_path: Optional[Path] = None):
        """
        初始化报告存储管理器

        Args:
            base_path: 基础存储路径，默认为 ~/.etf_challenger/reports
        """
        if base_path is None:
            self.base_path = Path.home() / '.etf_challenger' / 'reports'
        else:
            self.base_path = Path(base_path).expanduser()

        self.base_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"报告存储路径: {self.base_path}")

    def get_report_path(
        self,
        date: datetime,
        session: str,
        pool_name: str,
        format: str
    ) -> Path:
        """
        获取报告文件路径

        Args:
            date: 报告日期
            session: 时段 ('morning' 或 'afternoon')
            pool_name: ETF池名称
            format: 报告格式 ('html', 'markdown', 'json')

        Returns:
            报告文件路径
        """
        # 构建目录路径: daily/2026/02/01/morning/
        dir_path = self.base_path / 'daily' / f"{date.year:04d}" / f"{date.month:02d}" / f"{date.day:02d}" / session

        # 创建目录
        dir_path.mkdir(parents=True, exist_ok=True)

        # 文件名: 宽基指数_20260201_1000.html
        time_str = "1000" if session == 'morning' else "1430"
        file_ext = {
            'html': 'html',
            'markdown': 'md',
            'json': 'json'
        }.get(format, 'txt')

        filename = f"{pool_name}_{date:%Y%m%d}_{time_str}.{file_ext}"

        return dir_path / filename

    def save_report(
        self,
        content: str,
        metadata: Dict[str, Any]
    ) -> Path:
        """
        保存报告文件

        Args:
            content: 报告内容
            metadata: 元数据，包含:
                - pool: ETF池名称
                - date: 报告日期
                - session: 时段
                - format: 格式

        Returns:
            保存的文件路径
        """
        pool_name = metadata['pool']
        date = metadata['date']
        session = metadata['session']
        format = metadata['format']

        file_path = self.get_report_path(date, session, pool_name, format)

        # 保存文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        logger.info(f"报告已保存: {file_path}")
        return file_path

    def save_summary(
        self,
        date: datetime,
        session: str,
        recommendations: List[Dict[str, Any]]
    ) -> Path:
        """
        保存汇总数据

        Args:
            date: 报告日期
            session: 时段
            recommendations: 所有ETF的投资建议列表

        Returns:
            汇总文件路径
        """
        # 汇总文件路径
        dir_path = self.base_path / 'daily' / f"{date.year:04d}" / f"{date.month:02d}" / f"{date.day:02d}" / session
        dir_path.mkdir(parents=True, exist_ok=True)

        summary_path = dir_path / f"summary_{session}.json"

        # 构建汇总数据
        summary_data = {
            'date': date.strftime('%Y-%m-%d'),
            'session': session,
            'generated_at': datetime.now().isoformat(),
            'total_count': len(recommendations),
            'recommendations': recommendations,
            'statistics': self._calculate_statistics(recommendations)
        }

        # 保存汇总文件
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary_data, f, ensure_ascii=False, indent=2)

        logger.info(f"汇总数据已保存: {summary_path}")
        return summary_path

    def _calculate_statistics(self, recommendations: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        计算统计数据

        Args:
            recommendations: 投资建议列表

        Returns:
            统计数据字典
        """
        stats = {
            'strong_buy': 0,
            'buy': 0,
            'hold': 0,
            'sell': 0,
            'strong_sell': 0
        }

        for rec in recommendations:
            signal = rec.get('signal', 'HOLD')
            if signal == 'STRONG_BUY':
                stats['strong_buy'] += 1
            elif signal == 'BUY':
                stats['buy'] += 1
            elif signal == 'HOLD':
                stats['hold'] += 1
            elif signal == 'SELL':
                stats['sell'] += 1
            elif signal == 'STRONG_SELL':
                stats['strong_sell'] += 1

        return stats

    def list_reports(
        self,
        date: datetime,
        session: Optional[str] = None
    ) -> List[Path]:
        """
        列出指定日期的报告文件

        Args:
            date: 日期
            session: 时段，不指定则返回全天的报告

        Returns:
            报告文件路径列表
        """
        date_path = self.base_path / 'daily' / f"{date.year:04d}" / f"{date.month:02d}" / f"{date.day:02d}"

        if not date_path.exists():
            return []

        report_files = []

        if session:
            # 仅列出指定时段
            session_path = date_path / session
            if session_path.exists():
                report_files.extend(session_path.glob('*.html'))
                report_files.extend(session_path.glob('*.md'))
                report_files.extend(session_path.glob('*.json'))
        else:
            # 列出全天
            for sess in ['morning', 'afternoon']:
                session_path = date_path / sess
                if session_path.exists():
                    report_files.extend(session_path.glob('*.html'))
                    report_files.extend(session_path.glob('*.md'))
                    report_files.extend(session_path.glob('*.json'))

        # 排除汇总文件
        report_files = [f for f in report_files if not f.name.startswith('summary_')]

        return sorted(report_files)

    def get_summary(
        self,
        date: datetime,
        session: str
    ) -> Optional[Dict[str, Any]]:
        """
        获取汇总数据

        Args:
            date: 日期
            session: 时段

        Returns:
            汇总数据字典，如果不存在则返回None
        """
        summary_path = self.base_path / 'daily' / f"{date.year:04d}" / f"{date.month:02d}" / f"{date.day:02d}" / session / f"summary_{session}.json"

        if not summary_path.exists():
            return None

        with open(summary_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def archive_old_reports(self, days: int = 90):
        """
        归档旧报告（删除超过指定天数的报告）

        Args:
            days: 保留天数
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        logger.info(f"开始归档 {cutoff_date:%Y-%m-%d} 之前的报告...")

        daily_path = self.base_path / 'daily'
        if not daily_path.exists():
            return

        archived_count = 0

        # 遍历年份目录
        for year_dir in daily_path.iterdir():
            if not year_dir.is_dir():
                continue

            # 遍历月份目录
            for month_dir in year_dir.iterdir():
                if not month_dir.is_dir():
                    continue

                # 遍历日期目录
                for day_dir in month_dir.iterdir():
                    if not day_dir.is_dir():
                        continue

                    # 解析日期
                    try:
                        dir_date = datetime(
                            int(year_dir.name),
                            int(month_dir.name),
                            int(day_dir.name)
                        )

                        if dir_date < cutoff_date:
                            # 删除整个日期目录
                            shutil.rmtree(day_dir)
                            archived_count += 1
                            logger.info(f"已归档: {day_dir}")

                    except (ValueError, OSError) as e:
                        logger.warning(f"归档失败 {day_dir}: {e}")
                        continue

        logger.info(f"归档完成，共归档 {archived_count} 天的报告")

    def get_storage_size(self) -> int:
        """
        获取存储空间使用量（字节）

        Returns:
            存储空间大小（字节）
        """
        total_size = 0

        for file in self.base_path.rglob('*'):
            if file.is_file():
                total_size += file.stat().st_size

        return total_size

    def get_storage_size_mb(self) -> float:
        """
        获取存储空间使用量（MB）

        Returns:
            存储空间大小（MB）
        """
        return self.get_storage_size() / (1024 * 1024)
