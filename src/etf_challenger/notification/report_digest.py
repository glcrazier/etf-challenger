"""
报告摘要生成器

生成HTML格式的邮件摘要内容。
"""

import logging
from datetime import datetime
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class ReportDigest:
    """
    报告摘要生成器

    生成HTML格式的邮件内容，汇总所有ETF池的分析结果。
    """

    @staticmethod
    def generate_html_digest(
        session: str,
        recommendations: List[Dict[str, Any]],
        pools: List[str]
    ) -> str:
        """
        生成HTML格式的邮件摘要

        Args:
            session: 时段 ('morning' 或 'afternoon')
            recommendations: 所有ETF的投资建议列表
            pools: ETF池名称列表

        Returns:
            HTML格式的邮件内容
        """
        session_cn = '早盘' if session == 'morning' else '尾盘'
        date_str = datetime.now().strftime('%Y-%m-%d')
        time_str = datetime.now().strftime('%H:%M:%S')

        # 计算统计数据
        stats = ReportDigest._calculate_statistics(recommendations)

        # 分类建议
        categorized = ReportDigest._categorize_recommendations(recommendations)

        # 生成HTML
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ETF投资建议日报 - {date_str} {session_cn}</title>
    {ReportDigest._get_css_style()}
</head>
<body>
    <div class="container">
        <h1>📊 ETF投资建议日报</h1>
        <p class="subtitle">{date_str} {session_cn} | 生成时间: {time_str}</p>

        <div class="summary">
            <h2>📋 执行摘要</h2>
            <div class="stats-grid">
                <div class="stat-item">
                    <div class="stat-label">监控池</div>
                    <div class="stat-value">{len(pools)}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">监控ETF</div>
                    <div class="stat-value">{stats['total']}</div>
                </div>
                <div class="stat-item strong-buy">
                    <div class="stat-label">强烈买入</div>
                    <div class="stat-value">{stats['strong_buy']}</div>
                </div>
                <div class="stat-item buy">
                    <div class="stat-label">买入</div>
                    <div class="stat-value">{stats['buy']}</div>
                </div>
                <div class="stat-item hold">
                    <div class="stat-label">持有</div>
                    <div class="stat-value">{stats['hold']}</div>
                </div>
                <div class="stat-item sell">
                    <div class="stat-label">卖出</div>
                    <div class="stat-value">{stats['sell']}</div>
                </div>
                <div class="stat-item strong-sell">
                    <div class="stat-label">强烈卖出</div>
                    <div class="stat-value">{stats['strong_sell']}</div>
                </div>
            </div>
            <p class="pool-list"><strong>监控池:</strong> {', '.join(pools)}</p>
        </div>

        {ReportDigest._generate_strong_buy_section(categorized['强烈买入'])}
        {ReportDigest._generate_buy_section(categorized['买入'])}
        {ReportDigest._generate_hold_section(categorized['持有'])}
        {ReportDigest._generate_sell_section(categorized['卖出'], categorized['强烈卖出'])}
        {ReportDigest._generate_full_table(recommendations)}

        <div class="footer">
            <p><strong>风险提示:</strong> 本报告仅供参考，不构成投资建议。请结合基本面分析和自身风险承受能力做决策。</p>
            <p>详细报告已保存至本地文件系统</p>
            <p>ETF Challenger - 智能ETF分析工具</p>
        </div>
    </div>
</body>
</html>
"""
        return html

    @staticmethod
    def _calculate_statistics(recommendations: List[Dict[str, Any]]) -> Dict[str, int]:
        """计算统计数据"""
        stats = {
            'total': len(recommendations),
            'strong_buy': 0,
            'buy': 0,
            'hold': 0,
            'sell': 0,
            'strong_sell': 0
        }

        for rec in recommendations:
            signal = rec.get('signal', 'HOLD')
            if signal == '强烈买入' or signal == 'STRONG_BUY':
                stats['strong_buy'] += 1
            elif signal == '买入' or signal == 'BUY':
                stats['buy'] += 1
            elif signal == '持有' or signal == 'HOLD':
                stats['hold'] += 1
            elif signal == '卖出' or signal == 'SELL':
                stats['sell'] += 1
            elif signal == '强烈卖出' or signal == 'STRONG_SELL':
                stats['strong_sell'] += 1

        return stats

    @staticmethod
    def _categorize_recommendations(
        recommendations: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """分类投资建议"""
        categorized = {
            '强烈买入': [],
            '买入': [],
            '持有': [],
            '卖出': [],
            '强烈卖出': []
        }

        signal_mapping = {
            'STRONG_BUY': '强烈买入',
            'BUY': '买入',
            'HOLD': '持有',
            'SELL': '卖出',
            'STRONG_SELL': '强烈卖出'
        }

        for rec in recommendations:
            signal = rec.get('signal', 'HOLD')
            signal_cn = signal_mapping.get(signal, signal)

            if signal_cn in categorized:
                categorized[signal_cn].append(rec)

        return categorized

    @staticmethod
    def _generate_strong_buy_section(recommendations: List[Dict[str, Any]]) -> str:
        """生成强烈买入部分"""
        if not recommendations:
            return ""

        rows = []
        for rec in recommendations:
            # 建议买入价
            entry_price = f"{rec.get('entry_price', 0):.3f}" if rec.get('entry_price') else "-"

            # 止盈价（含潜在收益）
            target_gain = "-"
            if rec.get('price_target') and rec.get('current_price'):
                gain_pct = (rec['price_target'] - rec['current_price']) / rec['current_price'] * 100
                target_gain = f"{rec['price_target']:.3f} ({gain_pct:+.2f}%)"

            # 止损价
            stop_loss_text = f"{rec.get('stop_loss', 0):.3f}" if rec.get('stop_loss') else "-"

            reasons_text = '<br>'.join([f"• {r}" for r in rec.get('reasons', [])[:3]])

            rows.append(f"""
                <tr>
                    <td>{rec.get('code', 'N/A')}</td>
                    <td>{rec.get('name', 'N/A')}</td>
                    <td>{rec.get('current_price', 0):.3f}</td>
                    <td class="{'positive' if rec.get('change_pct', 0) > 0 else 'negative'}">{rec.get('change_pct', 0):+.2f}%</td>
                    <td>{rec.get('score', 0):.1f}</td>
                    <td>{rec.get('confidence', 0):.0f}%</td>
                    <td class="entry-price">{entry_price}</td>
                    <td class="price-target">{target_gain}</td>
                    <td class="stop-loss">{stop_loss_text}</td>
                    <td>{reasons_text}</td>
                </tr>
            """)

        return f"""
        <div class="section">
            <h2>🌟 重点关注 (强烈买入)</h2>
            <table>
                <thead>
                    <tr>
                        <th>代码</th>
                        <th>名称</th>
                        <th>当前价</th>
                        <th>涨跌幅</th>
                        <th>评分</th>
                        <th>置信度</th>
                        <th>建议买入价</th>
                        <th>止盈价</th>
                        <th>止损价</th>
                        <th>建议理由</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(rows)}
                </tbody>
            </table>
        </div>
        """

    @staticmethod
    def _generate_buy_section(recommendations: List[Dict[str, Any]]) -> str:
        """生成买入部分"""
        if not recommendations:
            return ""

        rows = []
        for rec in recommendations:
            entry_price = f"{rec.get('entry_price', 0):.3f}" if rec.get('entry_price') else "-"
            target_price = f"{rec.get('price_target', 0):.3f}" if rec.get('price_target') else "-"
            stop_loss = f"{rec.get('stop_loss', 0):.3f}" if rec.get('stop_loss') else "-"
            reasons_text = ', '.join(rec.get('reasons', [])[:2])

            rows.append(f"""
                <tr>
                    <td>{rec.get('code', 'N/A')}</td>
                    <td>{rec.get('name', 'N/A')}</td>
                    <td>{rec.get('current_price', 0):.3f}</td>
                    <td class="{'positive' if rec.get('change_pct', 0) > 0 else 'negative'}">{rec.get('change_pct', 0):+.2f}%</td>
                    <td>{rec.get('score', 0):.1f}</td>
                    <td class="entry-price">{entry_price}</td>
                    <td class="price-target">{target_price}</td>
                    <td class="stop-loss">{stop_loss}</td>
                    <td>{reasons_text}</td>
                </tr>
            """)

        return f"""
        <div class="section">
            <h2>🟢 买入建议</h2>
            <table>
                <thead>
                    <tr>
                        <th>代码</th>
                        <th>名称</th>
                        <th>当前价</th>
                        <th>涨跌幅</th>
                        <th>评分</th>
                        <th>建议买入价</th>
                        <th>止盈价</th>
                        <th>止损价</th>
                        <th>建议理由</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(rows)}
                </tbody>
            </table>
        </div>
        """

    @staticmethod
    def _generate_hold_section(recommendations: List[Dict[str, Any]]) -> str:
        """生成持有部分"""
        if not recommendations or len(recommendations) > 10:
            # 持有的太多，只显示数量
            return f"""
        <div class="section">
            <h2>🟡 持有建议</h2>
            <p>共 {len(recommendations)} 只ETF建议持有，详见完整清单。</p>
        </div>
        """

        rows = []
        for rec in recommendations:
            rows.append(f"""
                <tr>
                    <td>{rec.get('code', 'N/A')}</td>
                    <td>{rec.get('name', 'N/A')}</td>
                    <td>{rec.get('current_price', 0):.3f}</td>
                    <td class="{'positive' if rec.get('change_pct', 0) > 0 else 'negative'}">{rec.get('change_pct', 0):+.2f}%</td>
                    <td>{rec.get('score', 0):.1f}</td>
                </tr>
            """)

        return f"""
        <div class="section">
            <h2>🟡 持有建议</h2>
            <table>
                <thead>
                    <tr>
                        <th>代码</th>
                        <th>名称</th>
                        <th>当前价</th>
                        <th>涨跌幅</th>
                        <th>评分</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(rows)}
                </tbody>
            </table>
        </div>
        """

    @staticmethod
    def _generate_sell_section(
        sell_recommendations: List[Dict[str, Any]],
        strong_sell_recommendations: List[Dict[str, Any]]
    ) -> str:
        """生成卖出部分"""
        all_sell = strong_sell_recommendations + sell_recommendations
        if not all_sell:
            return ""

        rows = []
        for rec in all_sell:
            signal_class = 'strong-sell' if rec.get('signal') in ['强烈卖出', 'STRONG_SELL'] else 'sell'
            reasons_text = ', '.join(rec.get('reasons', [])[:2])

            rows.append(f"""
                <tr class="{signal_class}">
                    <td>{rec.get('code', 'N/A')}</td>
                    <td>{rec.get('name', 'N/A')}</td>
                    <td>{rec.get('current_price', 0):.3f}</td>
                    <td class="negative">{rec.get('change_pct', 0):+.2f}%</td>
                    <td>{rec.get('score', 0):.1f}</td>
                    <td>{rec.get('signal', 'N/A')}</td>
                    <td>{reasons_text}</td>
                </tr>
            """)

        return f"""
        <div class="section">
            <h2>🔴 卖出建议</h2>
            <table>
                <thead>
                    <tr>
                        <th>代码</th>
                        <th>名称</th>
                        <th>当前价</th>
                        <th>涨跌幅</th>
                        <th>评分</th>
                        <th>信号</th>
                        <th>卖出理由</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(rows)}
                </tbody>
            </table>
        </div>
        """

    @staticmethod
    def _generate_full_table(recommendations: List[Dict[str, Any]]) -> str:
        """生成完整清单表格"""
        # 按评分排序
        sorted_recs = sorted(recommendations, key=lambda x: x.get('score', 0), reverse=True)

        rows = []
        for i, rec in enumerate(sorted_recs, 1):
            entry_price = f"{rec.get('entry_price', 0):.3f}" if rec.get('entry_price') else "-"
            target_price = f"{rec.get('price_target', 0):.3f}" if rec.get('price_target') else "-"
            stop_loss = f"{rec.get('stop_loss', 0):.3f}" if rec.get('stop_loss') else "-"

            rows.append(f"""
                <tr>
                    <td>#{i}</td>
                    <td>{rec.get('code', 'N/A')}</td>
                    <td>{rec.get('name', 'N/A')}</td>
                    <td>{rec.get('current_price', 0):.3f}</td>
                    <td class="{'positive' if rec.get('change_pct', 0) > 0 else 'negative'}">{rec.get('change_pct', 0):+.2f}%</td>
                    <td>{rec.get('score', 0):.1f}</td>
                    <td>{rec.get('signal', 'N/A')}</td>
                    <td class="entry-price">{entry_price}</td>
                    <td class="price-target">{target_price}</td>
                    <td class="stop-loss">{stop_loss}</td>
                    <td>{rec.get('annual_return', 0):+.2f}%</td>
                </tr>
            """)

        return f"""
        <div class="section">
            <h2>📊 完整清单 (按评分排序)</h2>
            <table>
                <thead>
                    <tr>
                        <th>排名</th>
                        <th>代码</th>
                        <th>名称</th>
                        <th>当前价</th>
                        <th>涨跌幅</th>
                        <th>评分</th>
                        <th>建议</th>
                        <th>建议买入价</th>
                        <th>止盈价</th>
                        <th>止损价</th>
                        <th>年化收益</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(rows)}
                </tbody>
            </table>
        </div>
        """

    @staticmethod
    def _get_css_style() -> str:
        """获取CSS样式"""
        return """
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            background-color: #f5f5f5;
            margin: 0;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 {
            color: #667eea;
            border-bottom: 3px solid #667eea;
            padding-bottom: 10px;
            margin-bottom: 10px;
        }
        .subtitle {
            color: #666;
            font-size: 14px;
            margin-bottom: 20px;
        }
        h2 {
            color: #764ba2;
            margin-top: 30px;
            margin-bottom: 15px;
        }
        .summary {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }
        .stat-item {
            background: white;
            padding: 15px;
            border-radius: 6px;
            text-align: center;
            border: 2px solid #e0e0e0;
        }
        .stat-item.strong-buy { border-color: #22c55e; background: #f0fdf4; }
        .stat-item.buy { border-color: #86efac; background: #f7fee7; }
        .stat-item.hold { border-color: #fbbf24; background: #fffbeb; }
        .stat-item.sell { border-color: #fca5a5; background: #fef2f2; }
        .stat-item.strong-sell { border-color: #ef4444; background: #fef2f2; }
        .stat-label {
            font-size: 12px;
            color: #666;
            margin-bottom: 5px;
        }
        .stat-value {
            font-size: 24px;
            font-weight: bold;
            color: #333;
        }
        .pool-list {
            margin-top: 15px;
            font-size: 14px;
        }
        .section {
            margin: 30px 0;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
            font-size: 14px;
        }
        th {
            background-color: #667eea;
            color: white;
            padding: 12px 8px;
            text-align: left;
            font-weight: 600;
        }
        td {
            padding: 10px 8px;
            border-bottom: 1px solid #e0e0e0;
        }
        tr:hover {
            background-color: #f8f9fa;
        }
        .positive {
            color: #ef4444;
            font-weight: bold;
        }
        .negative {
            color: #22c55e;
            font-weight: bold;
        }
        .entry-price {
            color: #8b5cf6;
            font-weight: bold;
        }
        .price-target {
            color: #667eea;
            font-weight: bold;
        }
        .stop-loss {
            color: #f59e0b;
            font-weight: bold;
        }
        .footer {
            margin-top: 40px;
            padding-top: 20px;
            border-top: 2px solid #e0e0e0;
            font-size: 12px;
            color: #666;
            text-align: center;
        }
    </style>
        """
