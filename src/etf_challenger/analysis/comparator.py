"""ETF批量对比分析模块"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from datetime import datetime
import pandas as pd

from ..data.service import ETFDataService
from ..analysis.analyzer import ETFAnalyzer
from ..analysis.advisor import TradingAdvisor, SignalType


@dataclass
class ETFComparison:
    """ETF对比数据"""
    code: str
    name: str

    # 实时数据
    price: float
    change_pct: float

    # 交易建议
    signal_type: str
    confidence: float
    risk_level: str

    # 历史表现
    total_return: float
    annual_return: float
    volatility: float
    max_drawdown: float
    sharpe_ratio: float

    # 技术指标状态（看涨/看跌/中性的数量）
    bullish_count: int
    bearish_count: int
    neutral_count: int

    # 综合评分（0-100）
    score: float


class ETFComparator:
    """ETF对比分析器"""

    def __init__(self):
        self.data_service = ETFDataService()
        self.analyzer = ETFAnalyzer()
        self.advisor = TradingAdvisor()

    def compare(
        self,
        codes: List[str],
        days: int = 60
    ) -> List[ETFComparison]:
        """
        批量分析并对比多个ETF

        Args:
            codes: ETF代码列表
            days: 分析天数

        Returns:
            对比结果列表
        """
        results = []

        for code in codes:
            try:
                comparison = self._analyze_single(code, days)
                if comparison:
                    results.append(comparison)
            except Exception as e:
                print(f"分析 {code} 失败: {e}")
                continue

        # 按综合评分排序
        results.sort(key=lambda x: x.score, reverse=True)

        return results

    def _analyze_single(self, code: str, days: int) -> Optional[ETFComparison]:
        """分析单个ETF"""
        # 获取基本信息
        quote = self.data_service.get_realtime_quote(code)
        if not quote:
            return None

        # 获取历史数据
        end_date = datetime.now().strftime("%Y%m%d")
        from datetime import timedelta
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")

        df = self.data_service.get_historical_data(code, start_date, end_date)
        if df.empty:
            return None

        # 计算技术指标
        df = self.analyzer.calculate_returns(df)
        df = self.analyzer.calculate_moving_averages(df)
        df = self.analyzer.calculate_rsi(df)
        df = self.analyzer.calculate_macd(df)
        df = self.analyzer.calculate_bollinger_bands(df)

        # 分析历史表现
        performance = self.analyzer.analyze_performance(df)

        # 生成交易建议
        premium_rate = None
        try:
            premium_list = self.data_service.calculate_premium_discount(code, 5)
            if premium_list:
                premium_rate = premium_list[-1].premium_rate
        except:
            pass

        signal = self.advisor.analyze(df, premium_rate)

        # 统计技术指标状态
        bullish_count = sum(1 for status in signal.indicators.values() if status == "看涨")
        bearish_count = sum(1 for status in signal.indicators.values() if status == "看跌")
        neutral_count = sum(1 for status in signal.indicators.values() if status == "中性")

        # 计算综合评分
        score = self._calculate_score(signal, performance)

        return ETFComparison(
            code=code,
            name=quote.name,
            price=quote.price,
            change_pct=quote.change_pct,
            signal_type=signal.signal_type.value,
            confidence=signal.confidence,
            risk_level=signal.risk_level,
            total_return=performance['总收益率(%)'],
            annual_return=performance['年化收益率(%)'],
            volatility=performance['年化波动率(%)'],
            max_drawdown=performance['最大回撤(%)'],
            sharpe_ratio=performance['夏普比率'],
            bullish_count=bullish_count,
            bearish_count=bearish_count,
            neutral_count=neutral_count,
            score=score
        )

    def _calculate_score(self, signal, performance: Dict[str, float]) -> float:
        """计算综合评分（0-100）"""
        score = 50.0  # 基础分

        # 1. 交易信号得分（30分）
        signal_scores = {
            SignalType.STRONG_BUY: 30,
            SignalType.BUY: 20,
            SignalType.HOLD: 0,
            SignalType.SELL: -20,
            SignalType.STRONG_SELL: -30
        }
        score += signal_scores.get(signal.signal_type, 0)

        # 2. 置信度加成（10分）
        score += (signal.confidence - 50) / 5  # 置信度每高5%加1分

        # 3. 收益率得分（20分）
        annual_return = performance['年化收益率(%)']
        if annual_return > 20:
            score += 20
        elif annual_return > 10:
            score += 15
        elif annual_return > 5:
            score += 10
        elif annual_return > 0:
            score += 5
        elif annual_return > -5:
            score += 0
        else:
            score -= 10

        # 4. 夏普比率得分（15分）
        sharpe = performance['夏普比率']
        if sharpe > 2:
            score += 15
        elif sharpe > 1:
            score += 10
        elif sharpe > 0.5:
            score += 5
        elif sharpe > 0:
            score += 0
        else:
            score -= 5

        # 5. 风险惩罚（15分）
        volatility = performance['年化波动率(%)']
        if volatility < 10:
            score += 15
        elif volatility < 20:
            score += 10
        elif volatility < 30:
            score += 5
        else:
            score -= 5

        # 6. 最大回撤惩罚（10分）
        max_drawdown = abs(performance['最大回撤(%)'])
        if max_drawdown < 5:
            score += 10
        elif max_drawdown < 10:
            score += 5
        elif max_drawdown < 15:
            score += 0
        else:
            score -= 10

        # 确保分数在0-100范围内
        return max(0, min(100, score))

    def generate_comparison_report(
        self,
        comparisons: List[ETFComparison],
        format: str = "markdown"
    ) -> str:
        """
        生成对比报告

        Args:
            comparisons: 对比结果列表
            format: 报告格式（markdown/html）

        Returns:
            报告内容
        """
        if format == "markdown":
            return self._generate_markdown_report(comparisons)
        elif format == "html":
            return self._generate_html_report(comparisons)
        else:
            raise ValueError(f"不支持的格式: {format}")

    def _generate_markdown_report(self, comparisons: List[ETFComparison]) -> str:
        """生成Markdown格式对比报告"""
        md = []

        md.append("# ETF对比分析报告\n")
        md.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        md.append(f"**对比数量**: {len(comparisons)} 只ETF\n")
        md.append("---\n")

        # 综合排名
        md.append("## 📊 综合排名\n")
        md.append("| 排名 | 代码 | 名称 | 综合评分 | 交易建议 | 置信度 |")
        md.append("|------|------|------|----------|----------|--------|")
        for i, comp in enumerate(comparisons, 1):
            signal_emoji = self._get_signal_emoji(comp.signal_type)
            md.append(f"| {i} | {comp.code} | {comp.name} | {comp.score:.1f} | {signal_emoji} {comp.signal_type} | {comp.confidence:.0f}% |")
        md.append("")

        # 实时行情对比
        md.append("## 📈 实时行情对比\n")
        md.append("| 代码 | 名称 | 最新价 | 涨跌幅 |")
        md.append("|------|------|--------|--------|")
        for comp in comparisons:
            change_emoji = "📈" if comp.change_pct > 0 else "📉" if comp.change_pct < 0 else "➡️"
            md.append(f"| {comp.code} | {comp.name} | {comp.price:.3f} | {change_emoji} {comp.change_pct:+.2f}% |")
        md.append("")

        # 交易建议对比
        md.append("## 🎯 交易建议对比\n")
        md.append("| 代码 | 交易建议 | 置信度 | 风险等级 | 看涨指标 | 看跌指标 | 中性指标 |")
        md.append("|------|----------|--------|----------|----------|----------|----------|")
        for comp in comparisons:
            signal_emoji = self._get_signal_emoji(comp.signal_type)
            md.append(f"| {comp.code} | {signal_emoji} {comp.signal_type} | {comp.confidence:.0f}% | {comp.risk_level} | {comp.bullish_count} | {comp.bearish_count} | {comp.neutral_count} |")
        md.append("")

        # 历史表现对比
        md.append("## 📊 历史表现对比\n")
        md.append("| 代码 | 总收益率 | 年化收益 | 波动率 | 最大回撤 | 夏普比率 |")
        md.append("|------|----------|----------|--------|----------|----------|")
        for comp in comparisons:
            md.append(f"| {comp.code} | {comp.total_return:+.2f}% | {comp.annual_return:+.2f}% | {comp.volatility:.2f}% | {comp.max_drawdown:.2f}% | {comp.sharpe_ratio:.2f} |")
        md.append("")

        # 推荐建议
        md.append("## 💡 推荐建议\n")

        # 最佳选择
        if comparisons:
            best = comparisons[0]
            md.append(f"### 🏆 综合评分最高\n")
            md.append(f"**{best.name} ({best.code})**")
            md.append(f"- 综合评分: {best.score:.1f}")
            md.append(f"- 交易建议: {best.signal_type}")
            md.append(f"- 年化收益: {best.annual_return:+.2f}%")
            md.append(f"- 夏普比率: {best.sharpe_ratio:.2f}\n")

        # 最佳收益
        best_return = max(comparisons, key=lambda x: x.annual_return)
        md.append(f"### 📈 最高收益\n")
        md.append(f"**{best_return.name} ({best_return.code})**")
        md.append(f"- 年化收益: {best_return.annual_return:+.2f}%")
        md.append(f"- 总收益率: {best_return.total_return:+.2f}%\n")

        # 最低风险
        best_risk = min(comparisons, key=lambda x: x.volatility)
        md.append(f"### 🛡️ 最低风险\n")
        md.append(f"**{best_risk.name} ({best_risk.code})**")
        md.append(f"- 年化波动率: {best_risk.volatility:.2f}%")
        md.append(f"- 风险等级: {best_risk.risk_level}\n")

        # 最佳夏普比率
        best_sharpe = max(comparisons, key=lambda x: x.sharpe_ratio)
        md.append(f"### ⚖️ 最佳风险收益比\n")
        md.append(f"**{best_sharpe.name} ({best_sharpe.code})**")
        md.append(f"- 夏普比率: {best_sharpe.sharpe_ratio:.2f}")
        md.append(f"- 年化收益: {best_sharpe.annual_return:+.2f}%")
        md.append(f"- 年化波动率: {best_sharpe.volatility:.2f}%\n")

        # 风险提示
        md.append("## ⚠️ 风险提示\n")
        md.append("- 本对比报告仅供参考，不构成投资建议")
        md.append("- 历史表现不代表未来收益")
        md.append("- 请根据自身风险承受能力选择投资标的")
        md.append("- 建议分散投资，控制单一标的仓位\n")

        md.append("---")
        md.append("*报告由 ETF Challenger 自动生成*")

        return "\n".join(md)

    def _generate_html_report(self, comparisons: List[ETFComparison]) -> str:
        """生成HTML格式对比报告"""
        # 先生成markdown，然后包装为HTML
        md_content = self._generate_markdown_report(comparisons)

        html = []
        html.append("<!DOCTYPE html>")
        html.append("<html lang='zh-CN'>")
        html.append("<head>")
        html.append("  <meta charset='UTF-8'>")
        html.append("  <meta name='viewport' content='width=device-width, initial-scale=1.0'>")
        html.append("  <title>ETF对比分析报告</title>")
        html.append("  <style>")
        html.append(self._get_html_style())
        html.append("  </style>")
        html.append("</head>")
        html.append("<body>")
        html.append("  <div class='container'>")

        # 转换markdown为HTML（简化版）
        html_content = self._markdown_to_html(md_content)
        html.append(html_content)

        html.append("  </div>")
        html.append("</body>")
        html.append("</html>")

        return "\n".join(html)

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

    def _get_html_style(self) -> str:
        """获取HTML样式"""
        return """
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 30px;
            background: white;
            border-radius: 12px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
        }
        h1 {
            color: #667eea;
            margin-bottom: 10px;
            border-bottom: 4px solid #667eea;
            padding-bottom: 15px;
            font-size: 2.2em;
        }
        h2 {
            color: #764ba2;
            margin-top: 35px;
            margin-bottom: 20px;
            border-bottom: 2px solid #e8e8e8;
            padding-bottom: 10px;
        }
        h3 {
            color: #667eea;
            margin-top: 20px;
            margin-bottom: 12px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            background: white;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }
        th, td {
            padding: 14px;
            text-align: left;
            border-bottom: 1px solid #e8e8e8;
        }
        th {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.9em;
            letter-spacing: 0.5px;
        }
        tr:hover {
            background-color: #f8f9ff;
            transition: background-color 0.2s;
        }
        tr:first-child td {
            background-color: #fff9e6;
            font-weight: 600;
        }
        ul { margin: 10px 0 10px 20px; }
        li { margin: 8px 0; }
        hr {
            margin: 40px 0;
            border: none;
            border-top: 2px solid #e8e8e8;
        }
        """

    def _markdown_to_html(self, md: str) -> str:
        """简单的Markdown到HTML转换"""
        html = []
        in_table = False

        for line in md.split('\n'):
            line = line.strip()

            if not line:
                if in_table:
                    html.append("</tbody></table>")
                    in_table = False
                html.append("<br/>")
                continue

            # 标题
            if line.startswith('# '):
                html.append(f"<h1>{line[2:]}</h1>")
            elif line.startswith('## '):
                html.append(f"<h2>{line[3:]}</h2>")
            elif line.startswith('### '):
                html.append(f"<h3>{line[4:]}</h3>")

            # 表格
            elif line.startswith('|'):
                if not in_table:
                    html.append("<table>")
                    in_table = True

                cells = [cell.strip() for cell in line.split('|')[1:-1]]

                if all(c.startswith('-') for c in cells):
                    continue

                if not any('<tr>' in h for h in html[-5:]):
                    html.append("<thead><tr>")
                    for cell in cells:
                        html.append(f"<th>{cell}</th>")
                    html.append("</tr></thead><tbody>")
                else:
                    html.append("<tr>")
                    for cell in cells:
                        html.append(f"<td>{cell}</td>")
                    html.append("</tr>")

            # 列表
            elif line.startswith('- '):
                html.append(f"<li>{line[2:]}</li>")

            # 分隔线
            elif line == '---':
                if in_table:
                    html.append("</tbody></table>")
                    in_table = False
                html.append("<hr/>")

            # 普通文本
            else:
                line = line.replace('**', '<strong>').replace('**', '</strong>')
                html.append(f"<p>{line}</p>")

        if in_table:
            html.append("</tbody></table>")

        return "\n".join(html)
