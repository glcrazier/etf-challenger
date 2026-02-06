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

        # 数据时效性说明
        data_note = ""
        if session == 'morning':
            data_note = "💡 <strong>数据说明：</strong>早盘数据基于昨日收盘K线+今日实时行情，采用保守策略（提高买入阈值）"
        else:
            data_note = "💡 <strong>数据说明：</strong>尾盘数据基于昨日收盘K线+今日实时行情，采用标准策略（接近收盘，数据更准确）"

        # 计算统计数据
        stats = ReportDigest._calculate_statistics(recommendations)

        # 分类建议
        categorized = ReportDigest._categorize_recommendations(recommendations)

        # 按评分排序
        sorted_recommendations = sorted(recommendations, key=lambda x: x.get('score', 0), reverse=True)

        # 计算买入/持有/卖出数量（用于执行摘要）
        buy_count = stats['strong_buy'] + stats['buy']
        hold_count = stats['hold']
        sell_count = stats['sell'] + stats['strong_sell']

        # 最佳和最弱
        best = sorted_recommendations[0] if sorted_recommendations else None
        worst = sorted_recommendations[-1] if sorted_recommendations else None

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
        <h1>📊 ETF投资建议日报 - {', '.join(pools)}</h1>
        <p class="subtitle">{date_str} {session_cn} | 生成时间: {time_str} | 分析周期: 60天 | ETF数量: {stats['total']}只</p>

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
            <p class="pool-list">🟢 买入 {buy_count}只 | 🟡 持有 {hold_count}只 | 🔴 卖出 {sell_count}只{' | 🏆 最佳: ' + best['name'] + f"({best['score']:.0f}分) | 📉 最弱: " + worst['name'] + f"({worst['score']:.0f}分)" if best and worst else ""}</p>
            <p class="data-note">{data_note}</p>
        </div>

        <hr>

        {ReportDigest._generate_investment_table(sorted_recommendations)}

        <hr>

        {ReportDigest._generate_analysis_cards(sorted_recommendations)}

        <hr>

        <div class="section">
            <h2>⚠️ 风险提示</h2>
            <div class="disclaimer">
                <p>本报告仅供参考，不构成投资建议。技术分析存在滞后性，市场随时可能变化。请结合基本面分析和自身风险承受能力做决策，建议分散投资、控制仓位、严格止损。</p>
            </div>
        </div>

        <div class="footer">
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
    def _generate_investment_table(recommendations: List[Dict[str, Any]]) -> str:
        """生成投资建议清单表格（单一大表格）"""
        if not recommendations:
            return ""

        rows = []
        for i, rec in enumerate(recommendations, 1):
            # 信号emoji
            signal = rec.get('signal', 'N/A')
            signal_emoji = {
                '强烈买入': '🚀',
                'STRONG_BUY': '🚀',
                '买入': '📈',
                'BUY': '📈',
                '持有': '➡️',
                'HOLD': '➡️',
                '卖出': '📉',
                'SELL': '📉',
                '强烈卖出': '💥',
                'STRONG_SELL': '💥'
            }.get(signal, '❓')

            entry_price = f"{rec.get('entry_price', 0):.3f}" if rec.get('entry_price') else "-"
            target_price = f"{rec.get('price_target', 0):.3f}" if rec.get('price_target') else "-"
            stop_loss = f"{rec.get('stop_loss', 0):.3f}" if rec.get('stop_loss') else "-"

            # 中国市场习惯：涨红跌绿
            change_class = 'positive' if rec.get('change_pct', 0) >= 0 else 'negative'
            return_class = 'positive' if rec.get('annual_return', 0) >= 0 else 'negative'

            # 行样式
            row_class = ""
            if signal in ['强烈买入', 'STRONG_BUY', '买入', 'BUY']:
                row_class = ' class="buy-row"'
            elif signal in ['强烈卖出', 'STRONG_SELL', '卖出', 'SELL']:
                row_class = ' class="sell-row"'

            rows.append(f"""
                <tr{row_class}>
                    <td>#{i}</td>
                    <td>{rec.get('code', 'N/A')}</td>
                    <td>{rec.get('name', 'N/A')}</td>
                    <td>{rec.get('current_price', 0):.3f}</td>
                    <td class="{change_class}">{rec.get('change_pct', 0):+.1f}%</td>
                    <td>{signal_emoji} {signal}</td>
                    <td><strong>{rec.get('score', 0):.0f}</strong></td>
                    <td>{rec.get('confidence', 0):.0f}%</td>
                    <td class="entry-price">{entry_price}</td>
                    <td class="price-target">{target_price}</td>
                    <td class="stop-loss">{stop_loss}</td>
                    <td class="{return_class}">{rec.get('annual_return', 0):+.1f}%</td>
                    <td>{rec.get('risk_level', 'N/A')}</td>
                </tr>
            """)

        return f"""
        <div class="section">
            <h2>📊 投资建议清单</h2>
            <table>
                <thead>
                    <tr>
                        <th>排名</th>
                        <th>代码</th>
                        <th>名称</th>
                        <th>当前价</th>
                        <th>涨跌</th>
                        <th>建议</th>
                        <th>评分</th>
                        <th>置信度</th>
                        <th>建议买入价</th>
                        <th>止盈价</th>
                        <th>止损价</th>
                        <th>年化收益</th>
                        <th>风险</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(rows)}
                </tbody>
            </table>
        </div>
        """

    @staticmethod
    def _generate_analysis_cards(recommendations: List[Dict[str, Any]]) -> str:
        """生成个股分析卡片"""
        if not recommendations:
            return ""

        cards = []
        for i, rec in enumerate(recommendations, 1):
            signal = rec.get('signal', 'N/A')

            # 根据信号类型设置颜色
            if signal in ['强烈买入', 'STRONG_BUY', '买入', 'BUY']:
                emoji = '🟢'
                card_class = 'analysis-card buy-card'
            elif signal in ['强烈卖出', 'STRONG_SELL', '卖出', 'SELL']:
                emoji = '🔴'
                card_class = 'analysis-card sell-card'
            else:
                emoji = '🟡'
                card_class = 'analysis-card hold-card'

            # 价格参考
            price_ref_html = ""
            if rec.get('price_target') or rec.get('stop_loss'):
                price_parts = []
                if rec.get('entry_price'):
                    price_parts.append(f"<strong>建议买入价</strong>: {rec['entry_price']:.3f}")
                if rec.get('price_target'):
                    gain = (rec['price_target'] - rec['current_price']) / rec['current_price'] * 100
                    price_parts.append(f"<strong>止盈</strong>: {rec['price_target']:.3f} (+{gain:.1f}%)")
                if rec.get('stop_loss'):
                    loss = (rec['stop_loss'] - rec['current_price']) / rec['current_price'] * 100
                    price_parts.append(f"<strong>止损</strong>: {rec['stop_loss']:.3f} ({loss:+.1f}%)")
                price_ref_html = f"<p class='price-ref'>{' | '.join(price_parts)}</p>"

            # 分析要点
            reasons_html = ""
            if rec.get('reasons'):
                reasons_text = ' | '.join(rec['reasons'][:3])
                reasons_html = f"<p class='reasons'><strong>分析要点</strong>: {reasons_text}</p>"

            cards.append(f"""
                <div class='{card_class}'>
                    <h3>{emoji} #{i} {rec.get('name', 'N/A')} ({rec.get('code', 'N/A')})</h3>
                    <p class='core-data'>
                        <strong>当前价</strong>: {rec.get('current_price', 0):.3f} ({rec.get('change_pct', 0):+.2f}%) |
                        <strong>建议</strong>: {signal} |
                        <strong>评分</strong>: {rec.get('score', 0):.0f}/100 |
                        <strong>置信度</strong>: {rec.get('confidence', 0):.0f}%
                    </p>
                    {price_ref_html}
                    <p class='metrics'>
                        <strong>年化收益</strong>: {rec.get('annual_return', 0):+.2f}% |
                        <strong>夏普比率</strong>: {rec.get('sharpe_ratio', 0):.2f} |
                        <strong>风险等级</strong>: {rec.get('risk_level', 'N/A')}
                    </p>
                    {reasons_html}
                </div>
            """)

        return f"""
        <div class="section">
            <h2>📝 个股分析</h2>
            {''.join(cards)}
        </div>
        """

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

            # 中国市场习惯：涨红跌绿
            change_class = 'positive' if rec.get('change_pct', 0) >= 0 else 'negative'

            rows.append(f"""
                <tr class="buy-row">
                    <td>{rec.get('code', 'N/A')}</td>
                    <td>{rec.get('name', 'N/A')}</td>
                    <td>{rec.get('current_price', 0):.3f}</td>
                    <td class="{change_class}">{rec.get('change_pct', 0):+.2f}%</td>
                    <td><strong>{rec.get('score', 0):.1f}</strong></td>
                    <td>{rec.get('confidence', 0):.0f}%</td>
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
    def _generate_hold_section(recommendations: List[Dict[str, Any]]) -> str:
        """生成持有部分"""
        if not recommendations:
            return ""

        # 如果持有的太多，可以考虑只显示前15只
        display_recs = recommendations[:15] if len(recommendations) > 15 else recommendations

        rows = []
        for rec in display_recs:
            entry_price = f"{rec.get('entry_price', 0):.3f}" if rec.get('entry_price') else "-"
            target_price = f"{rec.get('price_target', 0):.3f}" if rec.get('price_target') else "-"
            stop_loss = f"{rec.get('stop_loss', 0):.3f}" if rec.get('stop_loss') else "-"

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
                </tr>
            """)

        more_note = ""
        if len(recommendations) > 15:
            more_note = f"<p class='note'>还有 {len(recommendations) - 15} 只持有建议，详见完整清单。</p>"

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
                        <th>建议买入价</th>
                        <th>止盈价</th>
                        <th>止损价</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(rows)}
                </tbody>
            </table>
            {more_note}
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

            # 信号emoji
            signal = rec.get('signal', 'N/A')
            signal_emoji = {
                '强烈买入': '🚀',
                'STRONG_BUY': '🚀',
                '买入': '📈',
                'BUY': '📈',
                '持有': '➡️',
                'HOLD': '➡️',
                '卖出': '📉',
                'SELL': '📉',
                '强烈卖出': '💥',
                'STRONG_SELL': '💥'
            }.get(signal, '❓')

            # 中国市场习惯：涨红跌绿
            change_class = 'positive' if rec.get('change_pct', 0) >= 0 else 'negative'
            return_class = 'positive' if rec.get('annual_return', 0) >= 0 else 'negative'

            # 行样式：买入/卖出建议添加背景色
            row_class = ""
            if signal in ['强烈买入', 'STRONG_BUY', '买入', 'BUY']:
                row_class = ' class="buy-row"'
            elif signal in ['强烈卖出', 'STRONG_SELL', '卖出', 'SELL']:
                row_class = ' class="sell-row"'

            rows.append(f"""
                <tr{row_class}>
                    <td>#{i}</td>
                    <td>{rec.get('code', 'N/A')}</td>
                    <td>{rec.get('name', 'N/A')}</td>
                    <td>{rec.get('current_price', 0):.3f}</td>
                    <td class="{change_class}">{rec.get('change_pct', 0):+.2f}%</td>
                    <td><strong>{rec.get('score', 0):.1f}</strong></td>
                    <td>{signal_emoji} {signal}</td>
                    <td class="entry-price">{entry_price}</td>
                    <td class="price-target">{target_price}</td>
                    <td class="stop-loss">{stop_loss}</td>
                    <td class="{return_class}">{rec.get('annual_return', 0):+.2f}%</td>
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
        """获取CSS样式（与batch_reporter.py保持一致）"""
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

        .subtitle {
            color: #666;
            font-size: 14px;
            margin-bottom: 20px;
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

        .data-note {
            margin-top: 12px;
            padding: 10px;
            background: #fef3c7;
            border-left: 4px solid #f59e0b;
            font-size: 13px;
            border-radius: 4px;
        }

        .note {
            margin-top: 10px;
            font-size: 13px;
            color: #666;
            font-style: italic;
        }

        .section {
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

        /* 中国市场习惯：红涨绿跌 */
        .positive {
            color: #ef4444;
            font-weight: bold;
        }

        .negative {
            color: #22c55e;
            font-weight: bold;
        }

        /* 价格字段特殊样式 */
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

            .stats-grid {
                grid-template-columns: repeat(auto-fit, minmax(100px, 1fr));
            }
        }
    </style>
        """
