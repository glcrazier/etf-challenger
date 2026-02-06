"""批量ETF投资建议报告生成器"""

import json
import pandas as pd
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
        days: int = 60,
        session: str = 'afternoon'
    ) -> Optional[ETFRecommendation]:
        """
        分析单个ETF

        Args:
            code: ETF代码
            days: 分析天数
            session: 时段 ('morning' 或 'afternoon')

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

            # 使用实时行情更新或添加当日K线
            df = self._update_with_realtime_data(df, quote)

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

            # 生成交易建议（传入session参数）
            signal = self.advisor.analyze(df, premium_rate, session=session)

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

    def _update_with_realtime_data(self, df: pd.DataFrame, quote) -> pd.DataFrame:
        """
        使用实时行情更新或添加当日K线

        Args:
            df: 历史K线数据
            quote: 实时行情

        Returns:
            更新后的DataFrame
        """
        today = datetime.now().strftime("%Y-%m-%d")

        # 检查最后一根K线是否是今天
        if not df.empty and '日期' in df.columns:
            last_date = pd.to_datetime(df['日期'].iloc[-1]).strftime("%Y-%m-%d")

            if last_date == today:
                # 更新今日K线
                df.loc[df.index[-1], '收盘'] = quote.price
                df.loc[df.index[-1], '最高'] = max(df.loc[df.index[-1], '最高'], quote.high)
                df.loc[df.index[-1], '最低'] = min(df.loc[df.index[-1], '最低'], quote.low)
                df.loc[df.index[-1], '成交量'] = quote.volume
                df.loc[df.index[-1], '成交额'] = quote.amount
            else:
                # 添加今日K线
                new_row = pd.DataFrame([{
                    '日期': today,
                    '开盘': quote.open_price,
                    '收盘': quote.price,
                    '最高': quote.high,
                    '最低': quote.low,
                    '成交量': quote.volume,
                    '成交额': quote.amount
                }])
                df = pd.concat([df, new_row], ignore_index=True)

        return df

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
        output_format: str = 'markdown',
        session: str = 'afternoon'
    ) -> Tuple[str, List[ETFRecommendation]]:
        """
        生成批量投资建议报告

        Args:
            pool_name: 池名称
            days: 分析天数
            output_format: 输出格式 (markdown/html)
            session: 时段 ('morning' 或 'afternoon')

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
            rec = self.analyze_single_etf(code, days, session=session)
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
        lines.append(f"\n**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | **分析周期**: {days}天 | **ETF数量**: {len(recommendations)}只")
        if pool_desc:
            lines.append(f" | **说明**: {pool_desc}")
        lines.append("\n\n---\n")

        # 执行摘要 - 紧凑版
        buy_count = len(categorized['强烈买入']) + len(categorized['买入'])
        sell_count = len(categorized['强烈卖出']) + len(categorized['卖出'])
        hold_count = len(categorized['持有'])

        lines.append("## 📋 执行摘要\n")
        lines.append(f"🟢 买入 {buy_count}只 | 🟡 持有 {hold_count}只 | 🔴 卖出 {sell_count}只")

        if recommendations:
            best = recommendations[0]
            worst = recommendations[-1]
            lines.append(f" | 🏆 最佳: {best.name}({best.score:.0f}分) | 📉 最弱: {worst.name}({worst.score:.0f}分)")

        lines.append("\n\n---\n")

        # 完整清单
        lines.append("## 📊 投资建议清单\n")
        lines.append("| 排名 | 代码 | 名称 | 当前价 | 涨跌 | 建议 | 评分 | 置信度 | 止盈价 | 止损价 | 年化收益 | 风险 |\n")
        lines.append("|:----:|------|------|-------:|-----:|:----:|-----:|-------:|-------:|-------:|---------:|:----:|\n")

        for i, rec in enumerate(recommendations, 1):
            # 信号emoji
            signal_emoji = {
                '强烈买入': '🚀',
                '买入': '📈',
                '持有': '➡️',
                '卖出': '📉',
                '强烈卖出': '💥'
            }.get(rec.signal_type, '❓')

            target = f"{rec.price_target:.3f}" if rec.price_target else "-"
            stop = f"{rec.stop_loss:.3f}" if rec.stop_loss else "-"

            lines.append(
                f"| #{i} | {rec.code} | {rec.name[:10]} | {rec.current_price:.3f} | "
                f"{rec.change_pct:+.1f}% | {signal_emoji} {rec.signal_type} | {rec.score:.0f} | "
                f"{rec.confidence:.0f}% | {target} | {stop} | {rec.annual_return:+.1f}% | {rec.risk_level} |\n"
            )

        lines.append("\n---\n")

        # 简洁的个股分析报告
        lines.append("## 📝 个股分析\n")

        for i, rec in enumerate(recommendations, 1):
            # 信号emoji和颜色标记
            if rec.signal_type in ['强烈买入', '买入']:
                emoji = '🟢'
            elif rec.signal_type in ['强烈卖出', '卖出']:
                emoji = '🔴'
            else:
                emoji = '🟡'

            lines.append(f"### {emoji} #{i} {rec.name} ({rec.code})\n")

            # 核心数据行
            lines.append(
                f"**当前价**: {rec.current_price:.3f} ({rec.change_pct:+.2f}%) | "
                f"**建议**: {rec.signal_type} | "
                f"**评分**: {rec.score:.0f}/100 | "
                f"**置信度**: {rec.confidence:.0f}%\n"
            )

            # 价格参考行
            if rec.price_target or rec.stop_loss:
                price_ref = []
                if rec.price_target:
                    gain = (rec.price_target - rec.current_price) / rec.current_price * 100
                    price_ref.append(f"**止盈**: {rec.price_target:.3f} (+{gain:.1f}%)")
                if rec.stop_loss:
                    loss = (rec.stop_loss - rec.current_price) / rec.current_price * 100
                    price_ref.append(f"**止损**: {rec.stop_loss:.3f} ({loss:.1f}%)")
                lines.append(" | ".join(price_ref) + "\n")

            # 表现指标行
            lines.append(
                f"**年化收益**: {rec.annual_return:+.2f}% | "
                f"**夏普比率**: {rec.sharpe_ratio:.2f} | "
                f"**风险等级**: {rec.risk_level}\n"
            )

            # 分析理由
            if rec.reasons:
                lines.append(f"\n**分析要点**: {' | '.join(rec.reasons[:3])}\n")

            lines.append("\n")

        # 风险提示
        lines.append("---\n")
        lines.append("## ⚠️ 风险提示\n")
        lines.append("本报告仅供参考，不构成投资建议。技术分析存在滞后性，市场随时可能变化。请结合基本面分析和自身风险承受能力做决策，建议分散投资、控制仓位、严格止损。\n")
        lines.append("\n---\n")
        lines.append(f"*报告生成工具: ETF Challenger v0.2.0*\n")

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

        # 尝试使用markdown库转换
        try:
            import markdown
            from markdown.extensions.tables import TableExtension
            html_body = markdown.markdown(
                md_content,
                extensions=['tables', 'fenced_code', 'nl2br']
            )
        except ImportError:
            # 如果没有markdown库，使用简化版HTML生成
            html_body = self._generate_simple_html(pool_name, pool_desc, recommendations, categorized, days)

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
        {html_body}
    </div>
</body>
</html>"""

    def _generate_simple_html(
        self,
        pool_name: str,
        pool_desc: str,
        recommendations: List[ETFRecommendation],
        categorized: Dict[str, List[ETFRecommendation]],
        days: int
    ) -> str:
        """直接生成HTML（不依赖markdown库）"""
        html = []

        # 标题
        html.append(f"<h1>ETF投资建议报告 - {pool_name}</h1>")
        html.append(f"<p><strong>生成时间</strong>: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
                   f"<strong>分析周期</strong>: {days}天 | <strong>ETF数量</strong>: {len(recommendations)}只")
        if pool_desc:
            html.append(f" | <strong>说明</strong>: {pool_desc}")
        html.append("</p>")
        html.append("<hr>")

        # 执行摘要
        buy_count = len(categorized['强烈买入']) + len(categorized['买入'])
        sell_count = len(categorized['强烈卖出']) + len(categorized['卖出'])
        hold_count = len(categorized['持有'])

        html.append("<h2>📋 执行摘要</h2>")
        html.append(f"<p>🟢 买入 {buy_count}只 | 🟡 持有 {hold_count}只 | 🔴 卖出 {sell_count}只")

        if recommendations:
            best = recommendations[0]
            worst = recommendations[-1]
            html.append(f" | 🏆 最佳: {best.name}({best.score:.0f}分) | 📉 最弱: {worst.name}({worst.score:.0f}分)")
        html.append("</p>")
        html.append("<hr>")

        # 投资建议清单表格
        html.append("<h2>📊 投资建议清单</h2>")
        html.append("<table>")
        html.append("<thead><tr>")
        html.append("<th>排名</th><th>代码</th><th>名称</th><th>当前价</th><th>涨跌</th>")
        html.append("<th>建议</th><th>评分</th><th>置信度</th><th>止盈价</th><th>止损价</th>")
        html.append("<th>年化收益</th><th>风险</th>")
        html.append("</tr></thead>")
        html.append("<tbody>")

        for i, rec in enumerate(recommendations, 1):
            signal_emoji = {
                '强烈买入': '🚀',
                '买入': '📈',
                '持有': '➡️',
                '卖出': '📉',
                '强烈卖出': '💥'
            }.get(rec.signal_type, '❓')

            # 根据建议类型设置行样式
            row_class = ""
            if rec.signal_type in ['强烈买入', '买入']:
                row_class = 'class="buy-row"'
            elif rec.signal_type in ['强烈卖出', '卖出']:
                row_class = 'class="sell-row"'

            target = f"{rec.price_target:.3f}" if rec.price_target else "-"
            stop = f"{rec.stop_loss:.3f}" if rec.stop_loss else "-"

            # 中国市场习惯：涨红跌绿
            change_color = "red" if rec.change_pct >= 0 else "green"

            html.append(f"<tr {row_class}>")
            html.append(f"<td>#{i}</td>")
            html.append(f"<td>{rec.code}</td>")
            html.append(f"<td>{rec.name}</td>")
            html.append(f"<td>{rec.current_price:.3f}</td>")
            html.append(f"<td style='color:{change_color}'>{rec.change_pct:+.1f}%</td>")
            html.append(f"<td>{signal_emoji} {rec.signal_type}</td>")
            html.append(f"<td><strong>{rec.score:.0f}</strong></td>")
            html.append(f"<td>{rec.confidence:.0f}%</td>")
            html.append(f"<td>{target}</td>")
            html.append(f"<td>{stop}</td>")
            # 中国市场习惯：涨红跌绿
            return_color = "red" if rec.annual_return >= 0 else "green"
            html.append(f"<td style='color:{return_color}'>{rec.annual_return:+.1f}%</td>")
            html.append(f"<td>{rec.risk_level}</td>")
            html.append("</tr>")

        html.append("</tbody></table>")
        html.append("<hr>")

        # 个股分析
        html.append("<h2>📝 个股分析</h2>")

        for i, rec in enumerate(recommendations, 1):
            # 根据信号类型设置颜色
            if rec.signal_type in ['强烈买入', '买入']:
                emoji = '🟢'
                card_class = 'analysis-card buy-card'
            elif rec.signal_type in ['强烈卖出', '卖出']:
                emoji = '🔴'
                card_class = 'analysis-card sell-card'
            else:
                emoji = '🟡'
                card_class = 'analysis-card hold-card'

            html.append(f"<div class='{card_class}'>")
            html.append(f"<h3>{emoji} #{i} {rec.name} ({rec.code})</h3>")

            # 核心数据
            html.append("<p class='core-data'>")
            html.append(f"<strong>当前价</strong>: {rec.current_price:.3f} ({rec.change_pct:+.2f}%) | ")
            html.append(f"<strong>建议</strong>: {rec.signal_type} | ")
            html.append(f"<strong>评分</strong>: {rec.score:.0f}/100 | ")
            html.append(f"<strong>置信度</strong>: {rec.confidence:.0f}%")
            html.append("</p>")

            # 价格参考
            if rec.price_target or rec.stop_loss:
                html.append("<p class='price-ref'>")
                if rec.price_target:
                    gain = (rec.price_target - rec.current_price) / rec.current_price * 100
                    html.append(f"<strong>止盈</strong>: {rec.price_target:.3f} (+{gain:.1f}%)")
                if rec.price_target and rec.stop_loss:
                    html.append(" | ")
                if rec.stop_loss:
                    loss = (rec.stop_loss - rec.current_price) / rec.current_price * 100
                    html.append(f"<strong>止损</strong>: {rec.stop_loss:.3f} ({loss:.1f}%)")
                html.append("</p>")

            # 表现指标
            html.append("<p class='metrics'>")
            html.append(f"<strong>年化收益</strong>: {rec.annual_return:+.2f}% | ")
            html.append(f"<strong>夏普比率</strong>: {rec.sharpe_ratio:.2f} | ")
            html.append(f"<strong>风险等级</strong>: {rec.risk_level}")
            html.append("</p>")

            # 分析要点
            if rec.reasons:
                html.append("<p class='reasons'>")
                html.append(f"<strong>分析要点</strong>: {' | '.join(rec.reasons[:3])}")
                html.append("</p>")

            html.append("</div>")

        # 风险提示
        html.append("<hr>")
        html.append("<h2>⚠️ 风险提示</h2>")
        html.append("<p class='disclaimer'>")
        html.append("本报告仅供参考，不构成投资建议。技术分析存在滞后性，市场随时可能变化。")
        html.append("请结合基本面分析和自身风险承受能力做决策，建议分散投资、控制仓位、严格止损。")
        html.append("</p>")

        html.append("<hr>")
        html.append("<p style='text-align:center; color:#999; font-size:0.9em;'>")
        html.append("报告生成工具: ETF Challenger v0.2.0")
        html.append("</p>")

        return "\n".join(html)

    def _get_html_style(self) -> str:
        """获取HTML样式"""
        return """
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB',
                         'Microsoft YaHei', 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
        }

        .container {
            max-width: 1200px;
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
            font-size: 2em;
        }

        h2 {
            color: #764ba2;
            margin: 35px 0 20px 0;
            padding-bottom: 10px;
            border-bottom: 2px solid #e0e0e0;
            font-size: 1.5em;
        }

        h3 {
            color: #555;
            margin: 15px 0 10px 0;
            font-size: 1.2em;
        }

        p {
            margin: 10px 0;
            line-height: 1.8;
        }

        hr {
            border: none;
            border-top: 1px solid #e0e0e0;
            margin: 30px 0;
        }

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
            text-align: center;
            font-weight: 600;
            letter-spacing: 0.5px;
        }

        td {
            padding: 12px;
            text-align: center;
            border-bottom: 1px solid #f0f0f0;
        }

        tbody tr:hover {
            background-color: #f8f9fa;
            transition: background-color 0.2s;
        }

        tbody tr:last-child td {
            border-bottom: none;
        }

        .buy-row {
            background-color: #f0fdf4;
        }

        .sell-row {
            background-color: #fef2f2;
        }

        /* 个股分析卡片 */
        .analysis-card {
            margin: 20px 0;
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #ddd;
            background: #fafafa;
        }

        .buy-card {
            border-left-color: #22c55e;
            background: linear-gradient(to right, #f0fdf4 0%, #fafafa 100%);
        }

        .sell-card {
            border-left-color: #ef4444;
            background: linear-gradient(to right, #fef2f2 0%, #fafafa 100%);
        }

        .hold-card {
            border-left-color: #f59e0b;
            background: linear-gradient(to right, #fffbeb 0%, #fafafa 100%);
        }

        .analysis-card h3 {
            margin-top: 0;
            margin-bottom: 15px;
            color: #333;
        }

        .core-data {
            font-size: 1.05em;
            margin: 10px 0;
            padding: 10px;
            background: white;
            border-radius: 4px;
        }

        .price-ref {
            font-size: 0.95em;
            color: #555;
            margin: 8px 0;
        }

        .metrics {
            font-size: 0.95em;
            color: #666;
            margin: 8px 0;
        }

        .reasons {
            font-size: 0.9em;
            color: #777;
            margin-top: 12px;
            padding-top: 12px;
            border-top: 1px dashed #ddd;
            font-style: italic;
        }

        .disclaimer {
            padding: 15px;
            background: #fff3cd;
            border-left: 4px solid #ffc107;
            border-radius: 4px;
            color: #856404;
            font-size: 0.95em;
        }

        /* 响应式设计 */
        @media (max-width: 768px) {
            .container {
                padding: 20px;
            }

            h1 {
                font-size: 1.5em;
            }

            h2 {
                font-size: 1.2em;
            }

            table {
                font-size: 0.85em;
            }

            th, td {
                padding: 8px 6px;
            }
        }
    </style>
        """
