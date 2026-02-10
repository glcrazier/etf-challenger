"""分析报告生成器"""

from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any, List
from datetime import datetime
import json
import pandas as pd

from ..models.etf import ETFQuote, ETFHolding
from ..analysis.advisor import TradingSignal


@dataclass
class ETFAnalysisReport:
    """ETF综合分析报告"""
    # 基本信息
    code: str
    name: str
    report_date: str

    # 实时行情
    quote: Optional[Dict[str, Any]] = None

    # 技术分析
    performance: Optional[Dict[str, float]] = None
    technical_indicators: Optional[Dict[str, float]] = None

    # 交易建议
    trading_signal: Optional[Dict[str, Any]] = None

    # 持仓信息
    holdings: Optional[List[Dict[str, Any]]] = None
    holdings_summary: Optional[Dict[str, Any]] = None

    # 溢价分析
    premium_analysis: Optional[Dict[str, Any]] = None

    # 历史数据
    recent_prices: Optional[List[Dict[str, float]]] = None


class ReportGenerator:
    """报告生成器"""

    def __init__(self):
        self.report_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def generate_markdown(self, report: ETFAnalysisReport) -> str:
        """生成Markdown格式报告"""
        md = []

        # 标题
        md.append(f"# {report.name} ({report.code}) 分析报告\n")
        md.append(f"**报告生成时间**: {report.report_date}\n")
        md.append("---\n")

        # 实时行情
        if report.quote:
            md.append("## 📊 实时行情\n")
            q = report.quote
            change_emoji = "📈" if q['change_pct'] > 0 else "📉" if q['change_pct'] < 0 else "➡️"
            md.append(f"- **最新价**: {q['price']:.3f}")
            md.append(f"- **涨跌幅**: {change_emoji} {q['change_pct']:+.2f}%")
            md.append(f"- **涨跌额**: {q['change']:+.3f}")
            md.append(f"- **开盘价**: {q['open_price']:.3f}")
            md.append(f"- **最高价**: {q['high']:.3f}")
            md.append(f"- **最低价**: {q['low']:.3f}")
            md.append(f"- **昨收价**: {q['pre_close']:.3f}")
            md.append(f"- **成交量**: {self._format_number(q['volume'])}")
            md.append(f"- **成交额**: {self._format_number(q['amount'])}\n")

        # 交易建议
        if report.trading_signal:
            md.append("## 🎯 交易建议\n")
            ts = report.trading_signal
            signal_emoji = self._get_signal_emoji(ts['signal_type'])
            md.append(f"### {signal_emoji} {ts['signal_type']}\n")
            md.append(f"- **置信度**: {ts['confidence']:.0f}%")
            md.append(f"- **风险等级**: {ts['risk_level']}\n")

            if ts.get('entry_price') or ts.get('price_target') or ts.get('stop_loss'):
                md.append("#### 💰 价格参考\n")
                if ts.get('entry_price'):
                    md.append(f"- **建议买入价**: {ts['entry_price']:.3f}")
                if ts.get('price_target'):
                    md.append(f"- **止盈价位**: {ts['price_target']:.3f}")
                if ts.get('stop_loss'):
                    md.append(f"- **止损价位**: {ts['stop_loss']:.3f}\n")

            md.append("#### 📝 分析依据\n")
            for reason in ts['reasons']:
                md.append(f"- {reason}")
            md.append("")

            md.append("#### 📈 技术指标状态\n")
            md.append("| 指标 | 状态 |")
            md.append("|------|------|")
            for indicator, status in ts['indicators'].items():
                status_display = self._get_status_display(status)
                md.append(f"| {indicator} | {status_display} |")
            md.append("")

        # 历史表现
        if report.performance:
            md.append("## 📈 历史表现\n")
            perf = report.performance
            md.append("| 指标 | 数值 |")
            md.append("|------|------|")
            for key, value in perf.items():
                if key == '交易天数':
                    md.append(f"| {key} | {value} |")
                else:
                    md.append(f"| {key} | {value} |")
            md.append("")

        # 技术指标
        if report.technical_indicators:
            md.append("## 🔧 技术指标\n")
            ti = report.technical_indicators
            md.append("| 指标 | 当前值 |")
            md.append("|------|--------|")
            for key, value in ti.items():
                if value is not None and not pd.isna(value):
                    md.append(f"| {key} | {value:.2f} |")
            md.append("")

        # 溢价分析
        if report.premium_analysis:
            md.append("## 💎 溢价/折价分析\n")
            pa = report.premium_analysis
            md.append(f"- **当前溢价率**: {pa['current_premium']:.2f}%")
            md.append(f"- **平均溢价率**: {pa['avg_premium']:.2f}%")
            md.append(f"- **最高溢价率**: {pa['max_premium']:.2f}%")
            md.append(f"- **最低溢价率**: {pa['min_premium']:.2f}%")

            if pa['current_premium'] < -1:
                md.append(f"\n💡 **提示**: 当前处于折价状态，可能存在买入机会")
            elif pa['current_premium'] > 1:
                md.append(f"\n⚠️ **提示**: 当前处于溢价状态，需谨慎买入")
            md.append("")

        # 持仓信息
        if report.holdings_summary:
            md.append("## 📊 持仓分析\n")
            hs = report.holdings_summary
            md.append(f"- **持仓数量**: {hs['持仓数量']}")
            md.append(f"- **前5大持仓权重**: {hs['前5大持仓权重(%)']}%")
            md.append(f"- **前10大持仓权重**: {hs['前10大持仓权重(%)']}%\n")

            if report.holdings:
                md.append("### 前10大持仓\n")
                md.append("| 排名 | 代码 | 名称 | 权重 |")
                md.append("|------|------|------|------|")
                for i, holding in enumerate(report.holdings[:10], 1):
                    md.append(f"| {i} | {holding['code']} | {holding['name']} | {holding['weight']:.2f}% |")
                md.append("")

        # 最近交易日
        if report.recent_prices:
            md.append("## 📅 近期走势\n")
            md.append("| 日期 | 收盘价 | 涨跌幅 |")
            md.append("|------|--------|--------|")
            for price in report.recent_prices[-10:]:
                change_emoji = "📈" if price.get('change_pct', 0) > 0 else "📉" if price.get('change_pct', 0) < 0 else "➡️"
                md.append(f"| {price['date']} | {price['close']:.3f} | {change_emoji} {price.get('change_pct', 0):+.2f}% |")
            md.append("")

        # 风险提示
        md.append("## ⚠️ 风险提示\n")
        md.append("- 本报告仅供参考，不构成投资建议")
        md.append("- 技术分析存在滞后性，市场随时可能变化")
        md.append("- 请结合基本面分析和自身风险承受能力做决策")
        md.append("- 投资有风险，入市需谨慎\n")

        md.append("---")
        md.append(f"*报告由 ETF Challenger 自动生成*")

        return "\n".join(md)

    def generate_html(self, report: ETFAnalysisReport) -> str:
        """生成HTML格式报告"""
        # 先生成markdown，然后转换为HTML
        md_content = self.generate_markdown(report)

        # 简单的markdown到HTML转换
        html = []
        html.append("<!DOCTYPE html>")
        html.append("<html lang='zh-CN'>")
        html.append("<head>")
        html.append("  <meta charset='UTF-8'>")
        html.append("  <meta name='viewport' content='width=device-width, initial-scale=1.0'>")
        html.append(f"  <title>{report.name} ({report.code}) 分析报告</title>")
        html.append("  <style>")
        html.append(self._get_html_style())
        html.append("  </style>")
        html.append("</head>")
        html.append("<body>")
        html.append("  <div class='container'>")

        # 转换markdown内容为HTML
        html_content = self._markdown_to_html(md_content)
        html.append(html_content)

        html.append("  </div>")
        html.append("</body>")
        html.append("</html>")

        return "\n".join(html)

    def generate_json(self, report: ETFAnalysisReport) -> str:
        """生成JSON格式报告"""
        report_dict = asdict(report)
        return json.dumps(report_dict, ensure_ascii=False, indent=2)

    def _format_number(self, value: float) -> str:
        """格式化数字"""
        if value >= 1e8:
            return f"{value / 1e8:.2f}亿"
        elif value >= 1e4:
            return f"{value / 1e4:.2f}万"
        else:
            return f"{value:.2f}"

    def _get_signal_emoji(self, signal_type: str) -> str:
        """获取信号表情"""
        emoji_map = {
            "强烈买入": "🚀",
            "买入": "📈",
            "持有": "➡️",
            "卖出": "📉",
            "强烈卖出": "💥"
        }
        return emoji_map.get(signal_type, "❓")

    def _get_status_display(self, status: str) -> str:
        """获取状态显示"""
        if status == "看涨":
            return "🟢 看涨"
        elif status == "看跌":
            return "🔴 看跌"
        else:
            return "🟡 中性"

    def _get_html_style(self) -> str:
        """获取HTML样式"""
        return """
        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB',
                         'Microsoft YaHei', 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            min-height: 100vh;
        }

        .container {
            max-width: 900px;
            margin: 0 auto;
            background: white;
            padding: 40px;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.15);
        }

        h1 {
            color: #667eea;
            border-bottom: 3px solid #667eea;
            padding-bottom: 15px;
            margin-bottom: 20px;
            font-size: 1.8em;
        }

        h2 {
            color: #764ba2;
            margin: 35px 0 20px 0;
            padding-bottom: 10px;
            border-bottom: 2px solid #e0e0e0;
            font-size: 1.4em;
        }

        h3 {
            color: #555;
            margin: 20px 0 12px 0;
            font-size: 1.15em;
        }

        h4 {
            color: #666;
            margin: 15px 0 10px 0;
            font-size: 1em;
        }

        p { margin: 10px 0; line-height: 1.8; }

        /* 表格样式 */
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            font-size: 0.95em;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            border-radius: 8px;
            overflow: hidden;
        }

        thead {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }

        th {
            padding: 14px 12px;
            text-align: left;
            font-weight: 600;
            letter-spacing: 0.5px;
        }

        td {
            padding: 12px;
            border-bottom: 1px solid #f0f0f0;
        }

        tbody tr:hover {
            background-color: #f8f9fa;
            transition: background-color 0.2s;
        }

        tbody tr:last-child td { border-bottom: none; }

        /* 列表样式 */
        ul {
            margin: 15px 0 15px 25px;
            list-style-type: none;
        }

        li {
            margin: 8px 0;
            padding-left: 20px;
            position: relative;
        }

        li::before {
            content: "•";
            color: #667eea;
            font-weight: bold;
            position: absolute;
            left: 0;
        }

        /* 中国市场习惯：红涨绿跌 */
        .positive { color: #ef4444; font-weight: bold; }
        .negative { color: #22c55e; font-weight: bold; }
        .neutral { color: #6b7280; }

        hr {
            margin: 30px 0;
            border: none;
            border-top: 1px solid #e0e0e0;
        }

        code {
            background: #f3f4f6;
            padding: 3px 8px;
            border-radius: 4px;
            font-family: 'SF Mono', 'Consolas', monospace;
            font-size: 0.9em;
        }

        /* 信号卡片 */
        .signal-card {
            background: linear-gradient(to right, #f0fdf4 0%, #fafafa 100%);
            border-left: 4px solid #22c55e;
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
        }

        /* 风险提示 */
        .disclaimer {
            padding: 15px;
            background: #fff3cd;
            border-left: 4px solid #ffc107;
            border-radius: 4px;
            color: #856404;
            font-size: 0.95em;
            margin: 20px 0;
        }

        /* 页脚 */
        .footer {
            margin-top: 40px;
            padding-top: 20px;
            border-top: 2px solid #e0e0e0;
            font-size: 12px;
            color: #666;
            text-align: center;
        }

        /* 响应式设计 */
        @media (max-width: 768px) {
            body { padding: 10px; }
            .container { padding: 20px; }
            h1 { font-size: 1.5em; }
            h2 { font-size: 1.2em; }
            table { font-size: 0.85em; }
            th, td { padding: 8px 6px; }
        }
        """

    def _markdown_to_html(self, md: str) -> str:
        """简单的Markdown到HTML转换"""
        import re

        def convert_bold(text: str) -> str:
            """转换加粗语法 **text** 为 <strong>text</strong>"""
            return re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)

        def convert_italic(text: str) -> str:
            """转换斜体语法 *text* 为 <em>text</em>"""
            return re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)

        def process_inline(text: str) -> str:
            """处理行内格式"""
            text = convert_bold(text)
            text = convert_italic(text)
            return text

        html = []
        in_table = False
        in_list = False

        for line in md.split('\n'):
            line = line.strip()

            if not line:
                if in_list:
                    html.append("</ul>")
                    in_list = False
                if in_table:
                    html.append("</tbody></table>")
                    in_table = False
                continue

            # 标题
            if line.startswith('#### '):
                html.append(f"<h4>{process_inline(line[5:])}</h4>")
            elif line.startswith('### '):
                html.append(f"<h3>{process_inline(line[4:])}</h3>")
            elif line.startswith('## '):
                html.append(f"<h2>{process_inline(line[3:])}</h2>")
            elif line.startswith('# '):
                html.append(f"<h1>{process_inline(line[2:])}</h1>")

            # 表格
            elif line.startswith('|'):
                if not in_table:
                    html.append("<table>")
                    in_table = True

                cells = [cell.strip() for cell in line.split('|')[1:-1]]

                if all(c.replace('-', '').replace(':', '') == '' for c in cells):
                    continue  # 跳过分隔行

                if not any('<tr>' in h for h in html[-5:]):
                    html.append("<thead><tr>")
                    for cell in cells:
                        html.append(f"<th>{process_inline(cell)}</th>")
                    html.append("</tr></thead><tbody>")
                else:
                    html.append("<tr>")
                    for cell in cells:
                        html.append(f"<td>{process_inline(cell)}</td>")
                    html.append("</tr>")

            # 列表
            elif line.startswith('- '):
                if not in_list:
                    html.append("<ul>")
                    in_list = True
                html.append(f"<li>{process_inline(line[2:])}</li>")

            # 分隔线
            elif line == '---':
                if in_table:
                    html.append("</tbody></table>")
                    in_table = False
                if in_list:
                    html.append("</ul>")
                    in_list = False
                html.append("<hr/>")

            # 普通文本
            else:
                html.append(f"<p>{process_inline(line)}</p>")

        if in_table:
            html.append("</tbody></table>")
        if in_list:
            html.append("</ul>")

        return "\n".join(html)
