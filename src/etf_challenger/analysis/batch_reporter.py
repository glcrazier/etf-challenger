"""批量ETF投资建议报告生成器"""

import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from collections import defaultdict

from ..data.service import ETFDataService
from ..analysis.analyzer import ETFAnalyzer
from ..analysis.advisor import TradingAdvisor, SignalType


@dataclass
class ETFRecommendation:
    """ETF投资建议"""
    code: str
    name: str
    signal_type: str
    confidence: float
    risk_level: str
    current_price: float
    entry_price: Optional[float]
    price_target: Optional[float]
    stop_loss: Optional[float]
    change_pct: float
    annual_return: float
    sharpe_ratio: float
    reasons: List[str]
    score: float  # 综合评分


class BatchReportGenerator:
    """批量报告生成器"""

    def __init__(self, config_path: str = "etf_pool.json"):
        """
        初始化批量报告生成器

        Args:
            config_path: ETF池配置文件路径
        """
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.data_service = ETFDataService()
        self.analyzer = ETFAnalyzer()
        self.advisor = TradingAdvisor()

    def _load_config(self) -> Dict:
        """加载配置文件"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {self.config_path}")

        with open(self.config_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def get_pool_list(self) -> List[str]:
        """获取所有池的名称"""
        return list(self.config['pools'].keys())

    def get_pool_etfs(self, pool_name: str = None) -> List[str]:
        """
        获取指定池的ETF列表

        Args:
            pool_name: 池名称，None则使用默认池

        Returns:
            ETF代码列表
        """
        if pool_name is None:
            pool_name = self.config.get('default_pool', '宽基指数')

        if pool_name not in self.config['pools']:
            raise ValueError(f"池 '{pool_name}' 不存在")

        return self.config['pools'][pool_name]['etfs']

    def analyze_single_etf(
        self,
        code: str,
        days: int = 60
    ) -> Optional[ETFRecommendation]:
        """
        分析单个ETF

        Args:
            code: ETF代码
            days: 分析天数

        Returns:
            ETF投资建议，失败返回None
        """
        try:
            # 获取基本信息
            quote = self.data_service.get_realtime_quote(code)
            if not quote:
                return None

            # 获取历史数据
            end_date = datetime.now().strftime("%Y%m%d")
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

            # 分析表现
            performance = self.analyzer.analyze_performance(df)

            # 获取溢价率
            premium_rate = None
            try:
                premium_list = self.data_service.calculate_premium_discount(code, 5)
                if premium_list:
                    premium_rate = premium_list[-1].premium_rate
            except:
                pass

            # 生成交易建议
            signal = self.advisor.analyze(df, premium_rate)

            # 计算综合评分 (基于信号类型、置信度、收益、风险)
            score = self._calculate_comprehensive_score(
                signal.signal_type,
                signal.confidence,
                performance['年化收益率(%)'],
                performance['夏普比率']
            )

            return ETFRecommendation(
                code=code,
                name=quote.name,
                signal_type=signal.signal_type.value,
                confidence=signal.confidence,
                risk_level=signal.risk_level,
                current_price=quote.price,
                entry_price=signal.entry_price,
                price_target=signal.price_target,
                stop_loss=signal.stop_loss,
                change_pct=quote.change_pct,
                annual_return=performance['年化收益率(%)'],
                sharpe_ratio=performance['夏普比率'],
                reasons=signal.reasons,
                score=score
            )

        except Exception as e:
            print(f"分析 {code} 失败: {e}")
            return None

    def _calculate_comprehensive_score(
        self,
        signal_type: SignalType,
        confidence: float,
        annual_return: float,
        sharpe_ratio: float
    ) -> float:
        """
        计算综合评分

        Args:
            signal_type: 信号类型
            confidence: 置信度
            annual_return: 年化收益率
            sharpe_ratio: 夏普比率

        Returns:
            综合评分 (0-100)
        """
        score = 50.0  # 基础分

        # 信号类型 (40分)
        signal_scores = {
            SignalType.STRONG_BUY: 40,
            SignalType.BUY: 30,
            SignalType.HOLD: 0,
            SignalType.SELL: -30,
            SignalType.STRONG_SELL: -40,
        }
        score += signal_scores.get(signal_type, 0)

        # 置信度 (20分)
        score += (confidence - 50) / 5 * 2

        # 年化收益 (20分)
        if annual_return > 20:
            score += 20
        elif annual_return > 10:
            score += 15
        elif annual_return > 5:
            score += 10
        elif annual_return > 0:
            score += 5
        else:
            score -= 10

        # 夏普比率 (20分)
        if sharpe_ratio > 2:
            score += 20
        elif sharpe_ratio > 1:
            score += 15
        elif sharpe_ratio > 0.5:
            score += 10
        elif sharpe_ratio > 0:
            score += 5
        else:
            score -= 10

        return max(0, min(100, score))

    def generate_batch_report(
        self,
        pool_name: str = None,
        days: int = 60,
        output_format: str = 'markdown'
    ) -> Tuple[str, List[ETFRecommendation]]:
        """
        生成批量投资建议报告

        Args:
            pool_name: 池名称
            days: 分析天数
            output_format: 输出格式 (markdown/html)

        Returns:
            (报告内容, ETF建议列表)
        """
        # 获取ETF列表
        etf_codes = self.get_pool_etfs(pool_name)

        if not etf_codes:
            raise ValueError(f"ETF池 '{pool_name}' 为空")

        pool_name = pool_name or self.config.get('default_pool', '宽基指数')
        pool_desc = self.config['pools'][pool_name].get('description', '')

        # 批量分析
        recommendations = []
        for code in etf_codes:
            rec = self.analyze_single_etf(code, days)
            if rec:
                recommendations.append(rec)

        if not recommendations:
            raise Exception("所有ETF分析均失败")

        # 按评分排序
        recommendations.sort(key=lambda x: x.score, reverse=True)

        # 分类建议
        categorized = self._categorize_recommendations(recommendations)

        # 生成报告
        if output_format == 'markdown':
            content = self._generate_markdown_report(
                pool_name, pool_desc, recommendations, categorized, days
            )
        else:  # html
            content = self._generate_html_report(
                pool_name, pool_desc, recommendations, categorized, days
            )

        return content, recommendations

    def _categorize_recommendations(
        self,
        recommendations: List[ETFRecommendation]
    ) -> Dict[str, List[ETFRecommendation]]:
        """分类投资建议"""
        categorized = {
            '强烈买入': [],
            '买入': [],
            '持有': [],
            '卖出': [],
            '强烈卖出': []
        }

        for rec in recommendations:
            categorized[rec.signal_type].append(rec)

        return categorized

    def _generate_markdown_report(
        self,
        pool_name: str,
        pool_desc: str,
        recommendations: List[ETFRecommendation],
        categorized: Dict[str, List[ETFRecommendation]],
        days: int
    ) -> str:
        """生成Markdown格式报告"""
        lines = []

        # 标题
        lines.append(f"# ETF投资建议报告 - {pool_name}")
        lines.append(f"\n**池描述**: {pool_desc}")
        lines.append(f"\n**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"\n**分析天数**: {days}天")
        lines.append(f"\n**ETF数量**: {len(recommendations)}只")
        lines.append("\n---\n")

        # 执行摘要
        lines.append("## 📋 执行摘要\n")

        buy_count = len(categorized['强烈买入']) + len(categorized['买入'])
        sell_count = len(categorized['强烈卖出']) + len(categorized['卖出'])
        hold_count = len(categorized['持有'])

        lines.append(f"- 🟢 **建议买入**: {buy_count}只 ({buy_count/len(recommendations)*100:.1f}%)")
        lines.append(f"- 🔴 **建议卖出**: {sell_count}只 ({sell_count/len(recommendations)*100:.1f}%)")
        lines.append(f"- 🟡 **建议持有**: {hold_count}只 ({hold_count/len(recommendations)*100:.1f}%)")

        # 最佳/最差
        if recommendations:
            best = recommendations[0]
            worst = recommendations[-1]
            lines.append(f"\n**最佳标的**: {best.name} ({best.code}) - 评分 {best.score:.1f}")
            lines.append(f"**最弱标的**: {worst.name} ({worst.code}) - 评分 {worst.score:.1f}")

        lines.append("\n---\n")

        # 买入建议详情
        if categorized['强烈买入'] or categorized['买入']:
            lines.append("## 🟢 买入建议\n")

            if categorized['强烈买入']:
                lines.append("### 💚 强烈买入\n")
                for rec in categorized['强烈买入']:
                    lines.append(f"#### {rec.name} ({rec.code})\n")
                    lines.append(f"- **当前价格**: {rec.current_price:.3f} ({rec.change_pct:+.2f}%)")
                    lines.append(f"- **置信度**: {rec.confidence:.0f}%")
                    lines.append(f"- **综合评分**: {rec.score:.1f}/100")
                    lines.append(f"- **年化收益**: {rec.annual_return:+.2f}%")
                    lines.append(f"- **夏普比率**: {rec.sharpe_ratio:.2f}")
                    if rec.price_target:
                        target_gain = (rec.price_target - rec.current_price) / rec.current_price * 100
                        lines.append(f"- **目标价位**: {rec.price_target:.3f} (潜在收益 {target_gain:+.2f}%)")
                    if rec.stop_loss:
                        stop_loss_pct = (rec.stop_loss - rec.current_price) / rec.current_price * 100
                        lines.append(f"- **止损价位**: {rec.stop_loss:.3f} ({stop_loss_pct:+.2f}%)")
                    lines.append(f"- **风险等级**: {rec.risk_level}")
                    lines.append(f"- **建议理由**:")
                    for reason in rec.reasons:
                        lines.append(f"  - {reason}")
                    lines.append("")

            if categorized['买入']:
                lines.append("### 🟢 买入\n")
                for rec in categorized['买入']:
                    lines.append(f"#### {rec.name} ({rec.code})\n")
                    lines.append(f"- **当前价格**: {rec.current_price:.3f} ({rec.change_pct:+.2f}%)")
                    lines.append(f"- **置信度**: {rec.confidence:.0f}%")
                    lines.append(f"- **综合评分**: {rec.score:.1f}/100")
                    if rec.price_target:
                        target_gain = (rec.price_target - rec.current_price) / rec.current_price * 100
                        lines.append(f"- **目标价位**: {rec.price_target:.3f} ({target_gain:+.2f}%)")
                    lines.append(f"- **建议理由**: {', '.join(rec.reasons[:3])}")
                    lines.append("")

        # 持有建议
        if categorized['持有']:
            lines.append("## 🟡 持有建议\n")
            lines.append("| 代码 | 名称 | 当前价 | 涨跌幅 | 评分 | 年化收益 | 风险 |\n")
            lines.append("|------|------|--------|--------|------|----------|------|\n")
            for rec in categorized['持有']:
                lines.append(
                    f"| {rec.code} | {rec.name[:10]} | {rec.current_price:.3f} | "
                    f"{rec.change_pct:+.2f}% | {rec.score:.1f} | {rec.annual_return:+.2f}% | {rec.risk_level} |\n"
                )
            lines.append("")

        # 卖出建议
        if categorized['卖出'] or categorized['强烈卖出']:
            lines.append("## 🔴 卖出建议\n")

            if categorized['强烈卖出']:
                lines.append("### ❌ 强烈卖出\n")
                for rec in categorized['强烈卖出']:
                    lines.append(f"#### {rec.name} ({rec.code})\n")
                    lines.append(f"- **当前价格**: {rec.current_price:.3f} ({rec.change_pct:+.2f}%)")
                    lines.append(f"- **置信度**: {rec.confidence:.0f}%")
                    lines.append(f"- **综合评分**: {rec.score:.1f}/100")
                    lines.append(f"- **年化收益**: {rec.annual_return:+.2f}%")
                    if rec.stop_loss:
                        lines.append(f"- **止损价位**: {rec.stop_loss:.3f}")
                    lines.append(f"- **卖出理由**: {', '.join(rec.reasons[:3])}")
                    lines.append("")

            if categorized['卖出']:
                lines.append("### 🔴 卖出\n")
                lines.append("| 代码 | 名称 | 当前价 | 涨跌幅 | 评分 | 建议理由 |\n")
                lines.append("|------|------|--------|--------|------|----------|\n")
                for rec in categorized['卖出']:
                    lines.append(
                        f"| {rec.code} | {rec.name[:10]} | {rec.current_price:.3f} | "
                        f"{rec.change_pct:+.2f}% | {rec.score:.1f} | {rec.reasons[0] if rec.reasons else 'N/A'} |\n"
                    )
                lines.append("")

        # 综合排名
        lines.append("## 📊 综合排名 (按评分)\n")
        lines.append("| 排名 | 代码 | 名称 | 评分 | 建议 | 置信度 | 年化收益 | 夏普比率 |\n")
        lines.append("|------|------|------|------|------|--------|----------|----------|\n")
        for i, rec in enumerate(recommendations, 1):
            lines.append(
                f"| #{i} | {rec.code} | {rec.name[:12]} | {rec.score:.1f} | "
                f"{rec.signal_type} | {rec.confidence:.0f}% | {rec.annual_return:+.2f}% | {rec.sharpe_ratio:.2f} |\n"
            )

        # 风险提示
        lines.append("\n---\n")
        lines.append("## ⚠️ 风险提示\n")
        lines.append("- 本报告仅供参考，不构成投资建议")
        lines.append("- 技术分析存在滞后性，市场随时可能变化")
        lines.append("- 请结合基本面分析和自身风险承受能力做决策")
        lines.append("- 建议分散投资，控制单一标的仓位")
        lines.append("- 设置止损位，严格执行风险管理")
        lines.append("\n---\n")
        lines.append(f"\n*报告生成工具: ETF Challenger v0.2.0*\n")

        return "".join(lines)

    def _generate_html_report(
        self,
        pool_name: str,
        pool_desc: str,
        recommendations: List[ETFRecommendation],
        categorized: Dict[str, List[ETFRecommendation]],
        days: int
    ) -> str:
        """生成HTML格式报告"""
        # 先生成Markdown
        md_content = self._generate_markdown_report(
            pool_name, pool_desc, recommendations, categorized, days
        )

        # 转换为HTML并添加样式
        html_content = self._markdown_to_html(md_content)

        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ETF投资建议报告 - {pool_name}</title>
    {self._get_html_style()}
</head>
<body>
    <div class="container">
        {html_content}
    </div>
</body>
</html>"""

    def _markdown_to_html(self, md_content: str) -> str:
        """简单的Markdown到HTML转换"""
        html = md_content

        # 标题转换
        html = html.replace('# ', '<h1>').replace('\n', '</h1>\n', html.count('# '))
        html = html.replace('## ', '<h2>').replace('\n', '</h2>\n', html.count('## '))
        html = html.replace('### ', '<h3>').replace('\n', '</h3>\n', html.count('### '))
        html = html.replace('#### ', '<h4>').replace('\n', '</h4>\n', html.count('#### '))

        # 粗体
        import re
        html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)

        # 列表
        html = re.sub(r'\n- ', r'\n<li>', html)
        html = re.sub(r'(<li>.*?\n)(?!<li>)', r'<ul>\1</ul>', html, flags=re.DOTALL)

        # 段落
        html = re.sub(r'\n\n', r'</p><p>', html)
        html = f'<p>{html}</p>'

        # 表格 (简化处理)
        html = html.replace('|', '</td><td>').replace('\n<td>', '\n<tr><td>').replace('</td>\n', '</td></tr>\n')

        return html

    def _get_html_style(self) -> str:
        """获取HTML样式"""
        return """
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }
        .container {
            background: white;
            padding: 40px;
            border-radius: 10px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
        }
        h1 {
            color: #667eea;
            border-bottom: 3px solid #667eea;
            padding-bottom: 10px;
        }
        h2 {
            color: #764ba2;
            margin-top: 30px;
        }
        h3 {
            color: #555;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        th {
            background-color: #667eea;
            color: white;
        }
        tr:hover {
            background-color: #f5f5f5;
        }
        .buy { color: #22c55e; font-weight: bold; }
        .sell { color: #ef4444; font-weight: bold; }
        .hold { color: #f59e0b; font-weight: bold; }
    </style>
        """
