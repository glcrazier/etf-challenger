"""
统一决策报告作业编排

使用UnifiedBatchReporter生成4层分析报告，保存到ReportStorage。
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List

from ..analysis.unified_batch_reporter import UnifiedBatchReporter, ScanResult
from ..config.scheduler_config import SchedulerConfig
from ..scheduler.report_job import ReportResult
from ..storage.report_storage import ReportStorage

logger = logging.getLogger(__name__)


class UnifiedReportJob:
    """
    统一决策报告作业

    编排流程:
    1. 为每个ETF池使用DecisionEngine执行4层分析
    2. 生成多格式报告并保存
    3. 汇总所有池的结果
    """

    def __init__(self, config: SchedulerConfig):
        self.config = config
        self.storage = ReportStorage(config.storage.get_base_path())
        # 使用绝对路径查找etf_pool.json配置文件
        import os
        etf_pool_path = os.path.join(os.path.expanduser("~"), ".etf_challenger", "etf_pool.json")
        self.reporter = UnifiedBatchReporter(config_path=etf_pool_path)

    def execute(self, session: str = 'midday') -> ReportResult:
        """
        执行统一决策报告生成

        Args:
            session: 时段标识（默认 'midday'）

        Returns:
            报告生成结果
        """
        logger.info(f"开始生成{session}统一决策报告...")

        all_results: List[ScanResult] = []
        errors = []
        reports_generated = 0
        pools_processed = 0

        report_date = datetime.now()

        # 遍历所有ETF池
        pool_list = self.reporter.get_pool_list()

        for pool_name in pool_list:
            try:
                logger.info(f"正在处理ETF池: {pool_name}")

                pool_results = self._generate_pool_reports(
                    pool_name=pool_name,
                    session=session,
                    date=report_date
                )

                all_results.extend(pool_results)
                reports_generated += len(self.config.report.formats)
                pools_processed += 1

                logger.info(f"ETF池 {pool_name} 处理完成，获得 {len(pool_results)} 个结果")

            except Exception as e:
                error_msg = f"生成{pool_name}统一决策报告失败: {e}"
                logger.error(error_msg, exc_info=True)
                errors.append(error_msg)
                continue

        # 去重：同一ETF在多个池中出现，保留得分最高的
        if all_results:
            deduplicated = self._deduplicate_results(all_results)
            if len(deduplicated) < len(all_results):
                logger.info(
                    f"去重完成: {len(all_results)} -> {len(deduplicated)} "
                    f"(移除{len(all_results) - len(deduplicated)}个重复ETF)"
                )
            all_results = deduplicated

        # 保存汇总数据
        summary_path = ""
        if all_results:
            try:
                summary_path = str(self.storage.save_summary(
                    date=report_date,
                    session=session,
                    recommendations=self._convert_results_to_dict(all_results)
                ))
                logger.info(f"汇总数据已保存: {summary_path}")
            except Exception as e:
                error_msg = f"保存汇总数据失败: {e}"
                logger.error(error_msg, exc_info=True)
                errors.append(error_msg)

        result = ReportResult(
            success=len(errors) == 0,
            session=session,
            reports_generated=reports_generated,
            pools_processed=pools_processed,
            errors=errors,
            summary_path=summary_path
        )

        logger.info(
            f"{session}统一决策报告生成完成: "
            f"处理{pools_processed}个池, "
            f"生成{reports_generated}个报告, "
            f"{len(errors)}个错误"
        )

        return result

    def _generate_pool_reports(
        self,
        pool_name: str,
        session: str,
        date: datetime
    ) -> List[ScanResult]:
        """为单个ETF池生成所有格式的报告"""
        scan_results = None

        for format_type in self.config.report.formats:
            try:
                # 确定输出格式（json转为markdown保存）
                output_format = format_type
                if format_type == 'json':
                    output_format = 'markdown'

                content, results = self.reporter.generate_report(
                    pool_name=pool_name,
                    days=self.config.report.analysis_days,
                    output_format=output_format
                )

                if scan_results is None:
                    scan_results = results

                # JSON格式单独处理
                if format_type == 'json':
                    content = self._generate_json_report(pool_name, results, date)

                # 保存报告
                self.storage.save_report(
                    content=content,
                    metadata={
                        'pool': pool_name,
                        'date': date,
                        'session': session,
                        'format': format_type
                    }
                )

                logger.debug(f"已保存 {pool_name} 的 {format_type} 统一决策报告")

            except Exception as e:
                logger.error(f"生成{pool_name}的{format_type}统一决策报告失败: {e}")
                continue

        return scan_results or []

    def _generate_json_report(
        self,
        pool_name: str,
        results: List[ScanResult],
        date: datetime
    ) -> str:
        """生成JSON格式报告"""
        report_data = {
            'pool_name': pool_name,
            'generated_at': date.isoformat(),
            'engine': 'unified_decision',
            'etf_count': len(results),
            'recommendations': self._convert_results_to_dict(results)
        }
        return json.dumps(report_data, ensure_ascii=False, indent=2)

    def _convert_results_to_dict(self, results: List[ScanResult]) -> List[Dict[str, Any]]:
        """将ScanResult转换为字典列表"""
        return [
            {
                'code': r.code,
                'name': r.name,
                'action': r.action,
                'composite_score': r.score,
                'confidence': r.confidence,
                'grade': r.grade,
                'grade_score': r.grade_score,
                'regime': r.analysis.regime.regime.value,
                'conclusion': r.analysis.conclusion,
                'risks': r.analysis.risks,
                'channels': [
                    {
                        'name': ch.name,
                        'score': ch.score,
                        'weight': ch.weight,
                        'detail': ch.detail
                    }
                    for ch in r.analysis.timing.channels
                ]
            }
            for r in results
        ]

    def _deduplicate_results(self, results: List[ScanResult]) -> List[ScanResult]:
        """去重：同一ETF保留composite_score最高的"""
        best = {}
        for r in results:
            if r.code not in best or r.score > best[r.code].score:
                best[r.code] = r

        return sorted(best.values(), key=lambda x: x.score, reverse=True)
