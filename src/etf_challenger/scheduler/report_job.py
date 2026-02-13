"""
报告生成作业编排

编排批量报告生成流程，为每个ETF池生成多格式报告并保存。
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List

from ..analysis.batch_reporter import BatchReportGenerator, ETFRecommendation
from ..config.scheduler_config import SchedulerConfig
from ..storage.report_storage import ReportStorage

logger = logging.getLogger(__name__)


@dataclass
class ReportResult:
    """报告生成结果"""
    success: bool
    session: str
    reports_generated: int
    pools_processed: int
    errors: List[str]
    summary_path: str = ""


class ReportJob:
    """
    报告生成作业

    编排批量报告生成流程:
    1. 为每个ETF池生成3种格式的报告
    2. 汇总所有池的分析结果
    3. 保存到文件系统
    """

    def __init__(self, config: SchedulerConfig):
        """
        初始化报告生成作业

        Args:
            config: 调度器配置
        """
        self.config = config
        self.storage = ReportStorage(config.storage.get_base_path())
        # 使用绝对路径查找etf_pool.json配置文件
        import os
        etf_pool_path = os.path.join(os.path.expanduser("~"), ".etf_challenger", "etf_pool.json")
        self.batch_generator = BatchReportGenerator(config_path=etf_pool_path)

    def execute(self, session: str) -> ReportResult:
        """
        执行报告生成

        Args:
            session: 时段 ('morning' 或 'afternoon')

        Returns:
            报告生成结果
        """
        logger.info(f"开始生成{session}报告...")

        all_recommendations = []
        errors = []
        reports_generated = 0
        pools_processed = 0

        report_date = datetime.now()

        # 遍历所有ETF池（从etf_pool.json动态读取，支持热加载）
        # 优先使用etf_pool.json中的池列表，但只处理scheduler_config中指定的池
        available_pools = self.batch_generator.get_pool_list()
        configured_pools = self.config.watchlists.pools

        # 取交集：只处理同时存在于etf_pool.json和scheduler_config中的池
        pool_list = [p for p in configured_pools if p in available_pools]

        if not pool_list:
            logger.warning(f"没有可处理的ETF池。配置池: {configured_pools}, 可用池: {available_pools}")

        for pool_name in pool_list:
            try:
                logger.info(f"正在处理ETF池: {pool_name}")

                # 为当前池生成所有格式的报告
                pool_recommendations = self._generate_pool_reports(
                    pool_name=pool_name,
                    session=session,
                    date=report_date
                )

                all_recommendations.extend(pool_recommendations)
                reports_generated += len(self.config.report.formats)
                pools_processed += 1

                logger.info(f"ETF池 {pool_name} 处理完成，获得 {len(pool_recommendations)} 个建议")

            except Exception as e:
                error_msg = f"生成{pool_name}报告失败: {e}"
                logger.error(error_msg, exc_info=True)
                errors.append(error_msg)
                continue

        # 去重：如果同一ETF在多个池中出现，保留评分最高的
        if all_recommendations:
            deduplicated = self._deduplicate_recommendations(all_recommendations)
            if len(deduplicated) < len(all_recommendations):
                logger.info(
                    f"去重完成: {len(all_recommendations)} -> {len(deduplicated)} "
                    f"(移除{len(all_recommendations) - len(deduplicated)}个重复ETF)"
                )
            all_recommendations = deduplicated

        # 生成汇总数据
        summary_path = ""
        if all_recommendations:
            try:
                summary_path = str(self.storage.save_summary(
                    date=report_date,
                    session=session,
                    recommendations=self._convert_recommendations_to_dict(all_recommendations)
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
            f"{session}报告生成完成: "
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
    ) -> List[ETFRecommendation]:
        """
        为单个ETF池生成所有格式的报告

        Args:
            pool_name: ETF池名称
            session: 时段
            date: 报告日期

        Returns:
            ETF投资建议列表
        """
        recommendations = None

        # 生成每种格式的报告
        for format_type in self.config.report.formats:
            try:
                # 使用BatchReportGenerator生成报告
                content, recs = self.batch_generator.generate_batch_report(
                    pool_name=pool_name,
                    days=self.config.report.analysis_days,
                    output_format=format_type,
                    session=session
                )

                # 第一次生成时保存recommendations
                if recommendations is None:
                    recommendations = recs

                # 如果是JSON格式，转换为JSON字符串
                if format_type == 'json':
                    content = self._generate_json_report(pool_name, recs, date)

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

                logger.debug(f"已保存 {pool_name} 的 {format_type} 报告")

            except Exception as e:
                logger.error(f"生成{pool_name}的{format_type}报告失败: {e}")
                # 继续处理其他格式
                continue

        return recommendations or []

    def _generate_json_report(
        self,
        pool_name: str,
        recommendations: List[ETFRecommendation],
        date: datetime
    ) -> str:
        """
        生成JSON格式的报告

        Args:
            pool_name: ETF池名称
            recommendations: 投资建议列表
            date: 报告日期

        Returns:
            JSON字符串
        """
        report_data = {
            'pool_name': pool_name,
            'generated_at': date.isoformat(),
            'etf_count': len(recommendations),
            'recommendations': self._convert_recommendations_to_dict(recommendations)
        }

        return json.dumps(report_data, ensure_ascii=False, indent=2)

    def _convert_recommendations_to_dict(
        self,
        recommendations: List[ETFRecommendation]
    ) -> List[Dict[str, Any]]:
        """
        将ETFRecommendation对象转换为字典列表

        Args:
            recommendations: 投资建议列表

        Returns:
            字典列表
        """
        return [
            {
                'code': rec.code,
                'name': rec.name,
                'signal': rec.signal_type,
                'confidence': rec.confidence,
                'risk_level': rec.risk_level,
                'current_price': rec.current_price,
                'entry_price': rec.entry_price,
                'price_target': rec.price_target,
                'stop_loss': rec.stop_loss,
                'change_pct': rec.change_pct,
                'annual_return': rec.annual_return,
                'sharpe_ratio': rec.sharpe_ratio,
                'score': rec.score,
                'reasons': rec.reasons
            }
            for rec in recommendations
        ]

    def _deduplicate_recommendations(
        self,
        recommendations: List[ETFRecommendation]
    ) -> List[ETFRecommendation]:
        """
        对ETF建议列表去重

        当同一ETF在多个池中出现时，保留评分最高的那个。

        Args:
            recommendations: 可能包含重复ETF的建议列表

        Returns:
            去重后的建议列表
        """
        best_recommendations = {}

        for rec in recommendations:
            code = rec.code
            if code not in best_recommendations:
                best_recommendations[code] = rec
            else:
                # 如果已存在，比较评分，保留评分更高的
                if rec.score > best_recommendations[code].score:
                    logger.debug(
                        f"ETF {code} 出现重复，保留评分更高的: "
                        f"{rec.score:.1f} > {best_recommendations[code].score:.1f}"
                    )
                    best_recommendations[code] = rec
                else:
                    logger.debug(
                        f"ETF {code} 出现重复，跳过评分较低的: "
                        f"{rec.score:.1f} <= {best_recommendations[code].score:.1f}"
                    )

        # 按评分排序返回
        return sorted(best_recommendations.values(), key=lambda x: x.score, reverse=True)
