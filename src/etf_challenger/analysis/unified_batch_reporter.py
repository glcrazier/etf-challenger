"""统一批量决策报告生成器

使用DecisionEngine对ETF池中所有ETF执行4层分析，
生成包含市场环境、基金评级、时机分析、持仓建议的综合报告。
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ..data.service import ETFDataService
from ..analysis.decision_engine import DecisionEngine
from ..models.decision import UnifiedAnalysis

logger = logging.getLogger(__name__)


@dataclass
class ScanResult:
    """单个ETF的扫描结果"""
    code: str
    name: str
    analysis: UnifiedAnalysis
    score: float          # timing.composite_score
    action: str           # 买入/卖出/持有
    confidence: float     # 0-100
    grade: str            # A/B/C/D
    grade_score: float    # 0-100


class UnifiedBatchReporter:
    """统一批量决策报告生成器"""

    def __init__(self, config_path: str = "etf_pool.json"):
        self.config_path = Path(config_path)
        self._config_cache = None
        self._config_mtime = None
        self.data_service = ETFDataService()
        self.engine = DecisionEngine(data_service=self.data_service)

    @property
    def config(self) -> Dict:
        """获取配置（自动检测文件变化并重新加载）"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {self.config_path}")

        current_mtime = self.config_path.stat().st_mtime
        if self._config_cache is None or self._config_mtime != current_mtime:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self._config_cache = json.load(f)
            self._config_mtime = current_mtime

        return self._config_cache

    def get_pool_list(self) -> List[str]:
        """获取所有池的名称"""
        return list(self.config['pools'].keys())

    def get_pool_etfs(self, pool_name: str = None) -> List[str]:
        """获取指定池的ETF列表"""
        if pool_name is None:
            pool_name = self.config.get('default_pool', '宽基指数')

        if pool_name not in self.config['pools']:
            raise ValueError(f"池 '{pool_name}' 不存在")

        return self.config['pools'][pool_name]['etfs']

    def generate_report(
        self,
        pool_name: str = None,
        days: int = 60,
        output_format: str = 'markdown'
    ) -> Tuple[str, List[ScanResult]]:
        """
        生成统一决策扫描报告

        Args:
            pool_name: ETF池名称，None则使用默认池
            days: 分析天数
            output_format: 输出格式 (markdown/html)

        Returns:
            (报告内容, 扫描结果列表)
        """
        etf_codes = self.get_pool_etfs(pool_name)
        if not etf_codes:
            raise ValueError(f"ETF池 '{pool_name}' 为空")

        pool_name = pool_name or self.config.get('default_pool', '宽基指数')
        pool_desc = self.config['pools'][pool_name].get('description', '')

        # 逐个分析
        results: List[ScanResult] = []
        skipped_bonds: List[str] = []
        failed: List[Tuple[str, str]] = []

        for code in etf_codes:
            # 跳过债券ETF
            if self.engine.is_bond_etf(code):
                name = self.engine._get_etf_name(code)
                skipped_bonds.append(f"{name}({code})")
                logger.info(f"跳过债券ETF: {code}")
                continue

            try:
                analysis = self.engine.analyze(code, days=days)
                result = ScanResult(
                    code=analysis.code,
                    name=analysis.name,
                    analysis=analysis,
                    score=analysis.timing.composite_score,
                    action=analysis.timing.action,
                    confidence=analysis.timing.confidence,
                    grade=analysis.fund_grade.grade.value,
                    grade_score=analysis.fund_grade.total_score,
                )
                results.append(result)
                logger.info(f"分析完成: {code} {analysis.name} -> {analysis.timing.action}")
            except Exception as e:
                logger.error(f"分析 {code} 失败: {e}")
                failed.append((code, str(e)))
                continue

        if not results:
            raise Exception("所有ETF分析均失败")

        # 按composite_score降序排序
        results.sort(key=lambda x: x.score, reverse=True)

        # 共享的市场环境（取第一个结果的regime）
        shared_regime = results[0].analysis.regime

        # 生成报告
        if output_format == 'markdown':
            content = self._generate_markdown(
                pool_name, pool_desc, results, shared_regime,
                skipped_bonds, failed, days
            )
        else:
            content = self._generate_html(
                pool_name, pool_desc, results, shared_regime,
                skipped_bonds, failed, days
            )

        return content, results

    def generate_all_pools_report(
        self,
        days: int = 60,
        output_format: str = 'markdown'
    ) -> Tuple[str, List[ScanResult]]:
        """
        扫描所有ETF池，去重后生成一份合并报告

        Args:
            days: 分析天数
            output_format: 输出格式 (markdown/html)

        Returns:
            (报告内容, 去重后的扫描结果列表)
        """
        all_results: List[ScanResult] = []
        all_skipped_bonds: List[str] = []
        all_failed: List[Tuple[str, str]] = []
        seen_codes = set()
        pool_names_processed = []

        for pool_name in self.get_pool_list():
            etf_codes = self.get_pool_etfs(pool_name)
            if not etf_codes:
                continue

            pool_names_processed.append(pool_name)

            for code in etf_codes:
                # 跳过已分析过的（跨池去重）
                if code in seen_codes:
                    continue
                seen_codes.add(code)

                # 跳过债券ETF
                if self.engine.is_bond_etf(code):
                    name = self.engine._get_etf_name(code)
                    all_skipped_bonds.append(f"{name}({code})")
                    logger.info(f"跳过债券ETF: {code}")
                    continue

                try:
                    analysis = self.engine.analyze(code, days=days)
                    result = ScanResult(
                        code=analysis.code,
                        name=analysis.name,
                        analysis=analysis,
                        score=analysis.timing.composite_score,
                        action=analysis.timing.action,
                        confidence=analysis.timing.confidence,
                        grade=analysis.fund_grade.grade.value,
                        grade_score=analysis.fund_grade.total_score,
                    )
                    all_results.append(result)
                    logger.info(f"分析完成: {code} {analysis.name} -> {analysis.timing.action}")
                except Exception as e:
                    logger.error(f"分析 {code} 失败: {e}")
                    all_failed.append((code, str(e)))
                    continue

        if not all_results:
            raise Exception("所有ETF分析均失败")

        all_results.sort(key=lambda x: x.score, reverse=True)
        shared_regime = all_results[0].analysis.regime

        title = "全部ETF池"
        desc = f"覆盖 {', '.join(pool_names_processed)}（共{len(seen_codes)}只，去重后{len(all_results)}只分析成功）"

        if output_format == 'markdown':
            content = self._generate_markdown(
                title, desc, all_results, shared_regime,
                all_skipped_bonds, all_failed, days
            )
        else:
            content = self._generate_html(
                title, desc, all_results, shared_regime,
                all_skipped_bonds, all_failed, days
            )

        return content, all_results

    def _generate_markdown(
        self,
        pool_name: str,
        pool_desc: str,
        results: List[ScanResult],
        regime,
        skipped_bonds: List[str],
        failed: List[Tuple[str, str]],
        days: int
    ) -> str:
        """生成Markdown格式报告"""
        lines = []

        # 标题
        lines.append(f"# ETF决策扫描报告 - {pool_name}")
        lines.append(f"\n**时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
                      f"**周期**: {days}天 | **数量**: {len(results)}只")
        if pool_desc:
            lines.append(f" | **说明**: {pool_desc}")
        lines.append("\n\n---\n")

        # 市场环境
        lines.append("## 市场环境\n")
        lines.append(f"**状态**: {regime.regime.value}\n")
        lines.append(f"{regime.narrative}\n")
        lines.append("\n---\n")

        # 投资建议清单
        lines.append("## 投资建议清单\n")
        lines.append("| # | 代码 | 名称 | 评级 | 建议 | 得分 | 置信度 | 关键因素 |\n")
        lines.append("|:--:|------|------|:----:|:----:|-----:|-------:|----------|\n")

        for i, r in enumerate(results, 1):
            # 取前2个通道作为关键因素
            key_factors = []
            for ch in r.analysis.timing.channels[:2]:
                direction = "+" if ch.score > 0 else ""
                key_factors.append(f"{ch.name}{direction}{ch.score:.2f}")
            factors_str = ", ".join(key_factors)

            action_emoji = {"买入": "📈", "卖出": "📉", "持有": "➡️"}.get(r.action, "❓")

            lines.append(
                f"| #{i} | {r.code} | {r.name[:10]} | {r.grade}({r.grade_score:.0f}) | "
                f"{action_emoji} {r.action} | {r.score:+.3f} | {r.confidence:.0f}% | {factors_str} |\n"
            )

        lines.append("\n---\n")

        # 个股分析
        lines.append("## 个股分析\n")

        for i, r in enumerate(results, 1):
            a = r.analysis

            if r.action == "买入":
                emoji = "🟢"
            elif r.action == "卖出":
                emoji = "🔴"
            else:
                emoji = "🟡"

            lines.append(f"### {emoji} #{i} {r.name} ({r.code})\n")

            # 基金评级
            dim_parts = []
            for dim in a.fund_grade.dimensions:
                dim_parts.append(f"{dim.name} {dim.score:.0f}/25")
            lines.append(f"**基金评级**: {r.grade}（{r.grade_score:.0f}分）— {', '.join(dim_parts)}\n")

            # 时机信号
            ch_parts = []
            for ch in a.timing.channels:
                arrow = "↗" if ch.score > 0.1 else ("↘" if ch.score < -0.1 else "→")
                ch_parts.append(f"{ch.name} {arrow}{ch.score:+.2f}({ch.weight:.0f}%)")
            lines.append(f"**时机信号**: {' | '.join(ch_parts)}\n")

            # 持仓建议
            if a.portfolio:
                p = a.portfolio
                tranche_parts = []
                for t in p.tranches:
                    tranche_parts.append(f"{t.price:.3f}")
                tranches_str = " / ".join(tranche_parts)
                batch_count = len(p.tranches)
                lines.append(f"**持仓建议**: {p.suggested_pct:.0f}%, 分{batch_count}批: {tranches_str}\n")

            # 结论
            lines.append(f"**结论**: {a.conclusion}\n")
            lines.append("\n---\n")

        # 跳过的债券ETF
        if skipped_bonds:
            lines.append(f"\n> 跳过债券ETF: {', '.join(skipped_bonds)}（请使用 `etf bond` 命令分析）\n")

        # 失败的ETF
        if failed:
            lines.append("\n> 分析失败: " + ", ".join(f"{code}({err})" for code, err in failed) + "\n")

        # 风险提示
        lines.append("\n---\n")
        lines.append("## ⚠️ 风险提示\n")
        lines.append("本报告基于统一决策框架（4层分析）生成，仅供参考，不构成投资建议。"
                      "技术分析存在滞后性，市场随时可能变化。"
                      "请结合基本面分析和自身风险承受能力做决策，建议分散投资、控制仓位、严格止损。\n")
        lines.append(f"\n*报告生成工具: ETF Challenger v1.1.0-dev (Unified Decision Engine)*\n")

        return "".join(lines)

    def _generate_html(
        self,
        pool_name: str,
        pool_desc: str,
        results: List[ScanResult],
        regime,
        skipped_bonds: List[str],
        failed: List[Tuple[str, str]],
        days: int
    ) -> str:
        """生成HTML格式报告"""
        # 先生成Markdown
        md_content = self._generate_markdown(
            pool_name, pool_desc, results, regime, skipped_bonds, failed, days
        )

        # 尝试使用markdown库转换
        try:
            import markdown
            html_body = markdown.markdown(
                md_content,
                extensions=['tables', 'fenced_code', 'nl2br']
            )
        except ImportError:
            html_body = self._generate_simple_html(
                pool_name, pool_desc, results, regime, skipped_bonds, failed, days
            )

        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ETF决策扫描报告 - {pool_name}</title>
    {self._get_html_style()}
</head>
<body>
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#f0f0f5;">
        <tr><td align="center" style="padding:20px 10px;">
            <div class="container">
                {html_body}
            </div>
        </td></tr>
    </table>
</body>
</html>"""

    def _generate_simple_html(
        self,
        pool_name: str,
        pool_desc: str,
        results: List[ScanResult],
        regime,
        skipped_bonds: List[str],
        failed: List[Tuple[str, str]],
        days: int
    ) -> str:
        """直接生成HTML（不依赖markdown库）"""
        html = []

        # 标题
        html.append(f"<h1>ETF决策扫描报告 - {pool_name}</h1>")
        html.append(f"<p><strong>时间</strong>: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
                     f"<strong>周期</strong>: {days}天 | <strong>数量</strong>: {len(results)}只")
        if pool_desc:
            html.append(f" | <strong>说明</strong>: {pool_desc}")
        html.append("</p><hr>")

        # 市场环境
        html.append("<h2>市场环境</h2>")
        html.append(f"<p><strong>状态</strong>: {regime.regime.value}</p>")
        html.append(f"<p>{regime.narrative}</p><hr>")

        # 投资建议清单
        html.append("<h2>投资建议清单</h2>")
        html.append("<table><thead><tr>")
        html.append("<th>#</th><th>代码</th><th>名称</th><th>评级</th>"
                     "<th>建议</th><th>得分</th><th>置信度</th><th>关键因素</th>")
        html.append("</tr></thead><tbody>")

        for i, r in enumerate(results, 1):
            key_factors = []
            for ch in r.analysis.timing.channels[:2]:
                direction = "+" if ch.score > 0 else ""
                key_factors.append(f"{ch.name}{direction}{ch.score:.2f}")
            factors_str = ", ".join(key_factors)

            action_emoji = {"买入": "📈", "卖出": "📉", "持有": "➡️"}.get(r.action, "❓")

            row_class = ""
            if r.action == "买入":
                row_class = 'class="buy-row"'
            elif r.action == "卖出":
                row_class = 'class="sell-row"'

            html.append(f"<tr {row_class}>")
            html.append(f"<td>#{i}</td><td>{r.code}</td><td>{r.name}</td>")
            html.append(f"<td>{r.grade}({r.grade_score:.0f})</td>")
            html.append(f"<td>{action_emoji} {r.action}</td>")
            html.append(f"<td><strong>{r.score:+.3f}</strong></td>")
            html.append(f"<td>{r.confidence:.0f}%</td>")
            html.append(f"<td>{factors_str}</td>")
            html.append("</tr>")

        html.append("</tbody></table><hr>")

        # 个股分析
        html.append("<h2>个股分析</h2>")

        for i, r in enumerate(results, 1):
            a = r.analysis
            if r.action == "买入":
                emoji = "🟢"
                card_class = "analysis-card buy-card"
            elif r.action == "卖出":
                emoji = "🔴"
                card_class = "analysis-card sell-card"
            else:
                emoji = "🟡"
                card_class = "analysis-card hold-card"

            html.append(f"<div class='{card_class}'>")
            html.append(f"<h3>{emoji} #{i} {r.name} ({r.code})</h3>")

            # 基金评级
            dim_parts = [f"{dim.name} {dim.score:.0f}/25" for dim in a.fund_grade.dimensions]
            html.append(f"<p class='core-data'><strong>基金评级</strong>: "
                         f"{r.grade}（{r.grade_score:.0f}分）— {', '.join(dim_parts)}</p>")

            # 时机信号
            ch_parts = []
            for ch in a.timing.channels:
                arrow = "↗" if ch.score > 0.1 else ("↘" if ch.score < -0.1 else "→")
                ch_parts.append(f"{ch.name} {arrow}{ch.score:+.2f}({ch.weight:.0f}%)")
            html.append(f"<p class='metrics'><strong>时机信号</strong>: {' | '.join(ch_parts)}</p>")

            # 持仓建议
            if a.portfolio:
                p = a.portfolio
                tranches_str = " / ".join(f"{t.price:.3f}" for t in p.tranches)
                html.append(f"<p class='price-ref'><strong>持仓建议</strong>: "
                             f"{p.suggested_pct:.0f}%, 分{len(p.tranches)}批: {tranches_str}</p>")

            # 结论
            html.append(f"<p class='reasons'><strong>结论</strong>: {a.conclusion}</p>")
            html.append("</div>")

        # 跳过/失败
        if skipped_bonds:
            html.append(f"<p><em>跳过债券ETF: {', '.join(skipped_bonds)}</em></p>")
        if failed:
            html.append(f"<p><em>分析失败: {', '.join(f'{c}({e})' for c, e in failed)}</em></p>")

        # 风险提示
        html.append("<hr><h2>⚠️ 风险提示</h2>")
        html.append("<p class='disclaimer'>")
        html.append("本报告基于统一决策框架（4层分析）生成，仅供参考，不构成投资建议。"
                     "技术分析存在滞后性，市场随时可能变化。"
                     "请结合基本面分析和自身风险承受能力做决策，建议分散投资、控制仓位、严格止损。")
        html.append("</p>")
        html.append("<hr>")
        html.append("<p style='text-align:center; color:#999; font-size:0.9em;'>")
        html.append("报告生成工具: ETF Challenger v1.1.0-dev (Unified Decision Engine)")
        html.append("</p>")

        return "\n".join(html)

    def _get_html_style(self) -> str:
        """获取HTML样式（邮件客户端兼容）"""
        return """
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB',
                         'Microsoft YaHei', 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background-color: #f0f0f5;
            margin: 0;
            padding: 0;
            width: 100%;
            -webkit-text-size-adjust: 100%;
        }

        .container {
            max-width: 900px;
            width: 100%;
            margin: 0 auto;
            background: #ffffff;
            padding: 30px;
            border-radius: 8px;
        }

        h1 {
            color: #667eea;
            border-bottom: 3px solid #667eea;
            padding-bottom: 15px;
            margin-bottom: 20px;
            font-size: 1.6em;
        }

        h2 {
            color: #764ba2;
            margin: 30px 0 15px 0;
            padding-bottom: 10px;
            border-bottom: 2px solid #e0e0e0;
            font-size: 1.3em;
        }

        h3 { color: #555; margin: 15px 0 10px 0; font-size: 1.1em; }
        p { margin: 10px 0; line-height: 1.8; }
        hr { border: none; border-top: 1px solid #e0e0e0; margin: 25px 0; }

        table {
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
            font-size: 0.9em;
            table-layout: fixed;
            word-wrap: break-word;
        }

        thead {
            background-color: #667eea;
            color: white;
        }

        th { padding: 10px 6px; text-align: center; font-weight: 600; font-size: 0.85em; }
        td { padding: 8px 6px; text-align: center; border-bottom: 1px solid #f0f0f0; font-size: 0.85em; overflow: hidden; text-overflow: ellipsis; }
        .buy-row { background-color: #f0fdf4; }
        .sell-row { background-color: #fef2f2; }

        .analysis-card {
            margin: 15px 0;
            padding: 15px;
            border-radius: 6px;
            border-left: 4px solid #ddd;
            background: #fafafa;
        }

        .buy-card { border-left-color: #22c55e; background-color: #f0fdf4; }
        .sell-card { border-left-color: #ef4444; background-color: #fef2f2; }
        .hold-card { border-left-color: #f59e0b; background-color: #fffbeb; }

        .analysis-card h3 { margin-top: 0; margin-bottom: 12px; color: #333; }
        .core-data { font-size: 0.95em; margin: 8px 0; padding: 8px; background: white; border-radius: 4px; }
        .price-ref { font-size: 0.9em; color: #555; margin: 6px 0; }
        .metrics { font-size: 0.9em; color: #666; margin: 6px 0; }
        .reasons { font-size: 0.85em; color: #777; margin-top: 10px; padding-top: 10px; border-top: 1px dashed #ddd; font-style: italic; }

        .disclaimer {
            padding: 12px;
            background: #fff3cd;
            border-left: 4px solid #ffc107;
            border-radius: 4px;
            color: #856404;
            font-size: 0.9em;
        }

        @media (max-width: 768px) {
            .container { padding: 15px; }
            h1 { font-size: 1.3em; }
            h2 { font-size: 1.1em; }
            table { font-size: 0.8em; }
            th, td { padding: 6px 4px; }
        }
    </style>
        """
