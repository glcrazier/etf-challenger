"""命令行主程序"""

import click
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress
from datetime import datetime, timedelta

from ..data.service import ETFDataService
from ..analysis.analyzer import ETFAnalyzer
from ..analysis.advisor import TradingAdvisor, SignalType
from ..recommendation.scorer import ETFScorer, ScoringStrategy
from ..recommendation.explainer import RecommendationExplainer
from ..utils.helpers import format_number, format_percentage, get_color_by_value

console = Console()
data_service = ETFDataService()
analyzer = ETFAnalyzer()
advisor = TradingAdvisor()


@click.group()
@click.version_option(version="1.1.0-dev")
def cli():
    """
    ETF Challenger - A股场内ETF基金分析工具

    提供实时行情监控、溢价/折价分析、历史数据分析和持仓成分分析功能。
    """
    pass


@cli.command()
@click.option('--keyword', '-k', default=None, help='搜索关键词（代码或名称）')
@click.option('--limit', '-l', default=20, help='显示数量限制')
def list(keyword, limit):
    """列出所有ETF或搜索ETF"""
    try:
        with Progress() as progress:
            task = progress.add_task("[cyan]正在获取ETF列表...", total=None)

            if keyword:
                df = data_service.search_etf(keyword)
                title = f"搜索结果: {keyword}"
            else:
                df = data_service.get_etf_list()
                title = "场内ETF列表"

            progress.update(task, completed=True)

        if df.empty:
            console.print("[yellow]未找到匹配的ETF[/yellow]")
            return

        # 限制显示数量
        df = df.head(limit)

        # 创建表格
        table = Table(title=title, show_header=True, header_style="bold magenta")
        table.add_column("代码", style="cyan")
        table.add_column("名称", style="white")
        table.add_column("最新价", justify="right")
        table.add_column("涨跌幅", justify="right")
        table.add_column("成交额", justify="right")

        for _, row in df.iterrows():
            change_pct = float(row['涨跌幅'])
            color = get_color_by_value(change_pct)

            table.add_row(
                row['代码'],
                row['名称'],
                f"{row['最新价']:.3f}",
                f"[{color}]{format_percentage(change_pct)}[/{color}]",
                format_number(row['成交额'])
            )

        console.print(table)
        console.print(f"\n共 {len(df)} 只ETF")

    except Exception as e:
        console.print(f"[red]错误: {str(e)}[/red]")


@cli.command()
@click.argument('code')
def quote(code):
    """查看ETF实时行情"""
    try:
        with Progress() as progress:
            task = progress.add_task("[cyan]正在获取实时行情...", total=None)
            quote_data = data_service.get_realtime_quote(code)
            progress.update(task, completed=True)

        if not quote_data:
            console.print(f"[red]未找到ETF: {code}[/red]")
            return

        # 创建行情面板
        color = get_color_by_value(quote_data.change_pct)

        info = f"""
[bold]{quote_data.name}[/bold] ({quote_data.code})

最新价: [{color}]{quote_data.price:.3f}[/{color}]
涨跌额: [{color}]{quote_data.change:+.3f}[/{color}]
涨跌幅: [{color}]{format_percentage(quote_data.change_pct)}[/{color}]

开盘价: {quote_data.open_price:.3f}
最高价: {quote_data.high:.3f}
最低价: {quote_data.low:.3f}
昨收价: {quote_data.pre_close:.3f}

成交量: {format_number(quote_data.volume)}
成交额: {format_number(quote_data.amount)}

更新时间: {quote_data.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
        """

        panel = Panel(info.strip(), title="实时行情", border_style=color)
        console.print(panel)

    except Exception as e:
        console.print(f"[red]错误: {str(e)}[/red]")


@cli.command()
@click.argument('code')
@click.option('--days', '-d', default=30, help='分析天数')
def premium(code, days):
    """分析ETF溢价/折价率"""
    try:
        with Progress() as progress:
            task = progress.add_task("[cyan]正在计算溢价率...", total=None)
            premium_list = data_service.calculate_premium_discount(code, days)
            progress.update(task, completed=True)

        if not premium_list:
            console.print(f"[yellow]暂无溢价数据[/yellow]")
            return

        # 创建表格
        table = Table(title=f"溢价/折价分析 ({code})", show_header=True)
        table.add_column("日期", style="cyan")
        table.add_column("市价", justify="right")
        table.add_column("净值", justify="right")
        table.add_column("溢价率", justify="right")

        # 只显示最近10条
        for item in premium_list[-10:]:
            color = get_color_by_value(item.premium_rate)
            table.add_row(
                item.date,
                f"{item.market_price:.4f}",
                f"{item.net_value:.4f}",
                f"[{color}]{format_percentage(item.premium_rate)}[/{color}]"
            )

        console.print(table)

        # 统计信息
        avg_premium = sum(p.premium_rate for p in premium_list) / len(premium_list)
        max_premium = max(p.premium_rate for p in premium_list)
        min_premium = min(p.premium_rate for p in premium_list)

        console.print(f"\n平均溢价率: {format_percentage(avg_premium)}")
        console.print(f"最高溢价率: {format_percentage(max_premium)}")
        console.print(f"最低溢价率: {format_percentage(min_premium)}")

    except Exception as e:
        console.print(f"[red]错误: {str(e)}[/red]")


@cli.command()
@click.argument('code')
@click.option('--days', '-d', default=90, help='分析天数')
def analyze(code, days):
    """分析ETF历史表现"""
    try:
        with Progress() as progress:
            task = progress.add_task("[cyan]正在分析历史数据...", total=None)

            end_date = datetime.now().strftime("%Y%m%d")
            start_date = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")

            df = data_service.get_historical_data(code, start_date, end_date)
            progress.update(task, completed=True)

        if df.empty:
            console.print(f"[red]未找到历史数据[/red]")
            return

        # 计算技术指标
        df = analyzer.calculate_returns(df)
        df = analyzer.calculate_moving_averages(df)
        df = analyzer.calculate_rsi(df)

        # 计算表现指标
        performance = analyzer.analyze_performance(df)

        # 显示表现统计
        table = Table(title=f"历史表现分析 ({code})", show_header=True)
        table.add_column("指标", style="cyan")
        table.add_column("数值", justify="right", style="yellow")

        for key, value in performance.items():
            if key == '交易天数':
                table.add_row(key, str(value))
            else:
                color = get_color_by_value(value) if '收益' in key else "yellow"
                table.add_row(key, f"[{color}]{value}[/{color}]")

        console.print(table)

        # 显示最近数据
        console.print("\n[bold]最近10个交易日:[/bold]")
        recent_table = Table(show_header=True)
        recent_table.add_column("日期", style="cyan")
        recent_table.add_column("收盘价", justify="right")
        recent_table.add_column("日收益率", justify="right")
        recent_table.add_column("MA5", justify="right")
        recent_table.add_column("MA20", justify="right")
        recent_table.add_column("RSI", justify="right")

        for _, row in df.tail(10).iterrows():
            daily_return = row.get('日收益率', 0)
            color = get_color_by_value(daily_return)

            recent_table.add_row(
                row['日期'],
                f"{row['收盘']:.3f}",
                f"[{color}]{format_percentage(daily_return)}[/{color}]",
                f"{row.get('MA5', 0):.3f}",
                f"{row.get('MA20', 0):.3f}",
                f"{row.get('RSI', 0):.1f}"
            )

        console.print(recent_table)

    except Exception as e:
        console.print(f"[red]错误: {str(e)}[/red]")


@cli.command()
@click.argument('code')
@click.option('--limit', '-l', default=10, help='显示数量')
@click.option('--year', '-y', default=None, help='查询年份（默认当前年份）')
def holdings(code, limit, year):
    """查看ETF持仓成分"""
    try:
        with Progress() as progress:
            task = progress.add_task("[cyan]正在获取持仓数据...", total=None)
            holdings_list = data_service.get_etf_holdings(code, year)
            progress.update(task, completed=True)

        if not holdings_list:
            console.print(f"[yellow]暂无持仓数据[/yellow]")
            return

        # 分析持仓
        analysis = analyzer.analyze_holdings(holdings_list)

        # 显示统计信息
        console.print(f"\n[bold]持仓统计:[/bold]")
        console.print(f"持仓数量: {analysis['持仓数量']}")
        console.print(f"前5大持仓权重: {analysis['前5大持仓权重(%)']}%")
        console.print(f"前10大持仓权重: {analysis['前10大持仓权重(%)']}%")

        # 显示持仓明细
        table = Table(title=f"\n前{limit}大持仓 ({code})", show_header=True)
        table.add_column("排名", style="cyan")
        table.add_column("股票代码", style="cyan")
        table.add_column("股票名称", style="white")
        table.add_column("权重", justify="right", style="yellow")

        for i, holding in enumerate(holdings_list[:limit], 1):
            table.add_row(
                str(i),
                holding.stock_code,
                holding.stock_name,
                f"{holding.weight:.2f}%"
            )

        console.print(table)

    except Exception as e:
        console.print(f"[red]错误: {str(e)}[/red]")


@cli.command()
@click.argument('code')
@click.option('--days', '-d', default=60, help='分析天数（建议30-90天）')
def suggest(code, days):
    """获取ETF买卖建议（综合技术分析）"""
    try:
        with Progress() as progress:
            task = progress.add_task("[cyan]正在分析数据...", total=None)

            # 获取历史数据
            end_date = datetime.now().strftime("%Y%m%d")
            start_date = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")
            df = data_service.get_historical_data(code, start_date, end_date)

            if df.empty:
                console.print(f"[red]未找到历史数据[/red]")
                return

            # 计算技术指标
            df = analyzer.calculate_returns(df)
            df = analyzer.calculate_moving_averages(df)
            df = analyzer.calculate_rsi(df)
            df = analyzer.calculate_macd(df)
            df = analyzer.calculate_bollinger_bands(df)

            # 尝试获取溢价率
            premium_rate = None
            try:
                premium_list = data_service.calculate_premium_discount(code, 5)
                if premium_list:
                    premium_rate = premium_list[-1].premium_rate
            except:
                pass

            # 生成建议
            signal = advisor.analyze(df, premium_rate)

            progress.update(task, completed=True)

        # 获取ETF名称
        etf_name = "未知"
        try:
            quote = data_service.get_realtime_quote(code)
            if quote:
                etf_name = quote.name
        except:
            pass

        # 显示建议
        _display_trading_signal(code, etf_name, signal, df)

    except Exception as e:
        console.print(f"[red]错误: {str(e)}[/red]")
        import traceback
        traceback.print_exc()


def _display_trading_signal(code, name, signal, df):
    """显示交易信号"""
    # 确定颜色
    if signal.signal_type in [SignalType.STRONG_BUY, SignalType.BUY]:
        signal_color = "green"
        signal_emoji = "📈"
    elif signal.signal_type in [SignalType.STRONG_SELL, SignalType.SELL]:
        signal_color = "red"
        signal_emoji = "📉"
    else:
        signal_color = "yellow"
        signal_emoji = "➡️"

    # 创建标题面板
    current_price = df['收盘'].iloc[-1]
    header = f"""
[bold]{name}[/bold] ({code})
当前价格: {current_price:.3f}

[{signal_color}]{signal_emoji} {signal.signal_type.value}[/{signal_color}]
置信度: [{signal_color}]{signal.confidence:.0f}%[/{signal_color}]
风险等级: {signal.risk_level}
    """

    console.print(Panel(header.strip(), title="交易建议", border_style=signal_color))

    # 显示建议原因
    console.print("\n[bold]分析依据:[/bold]")
    for reason in signal.reasons:
        console.print(f"  {reason}")

    # 显示各项指标状态
    console.print("\n[bold]技术指标状态:[/bold]")
    table = Table(show_header=True, box=None)
    table.add_column("指标", style="cyan")
    table.add_column("状态", justify="center")

    for indicator, status in signal.indicators.items():
        if status == "看涨":
            status_display = "[green]看涨 ↗[/green]"
        elif status == "看跌":
            status_display = "[red]看跌 ↘[/red]"
        else:
            status_display = "[yellow]中性 →[/yellow]"

        table.add_row(indicator, status_display)

    console.print(table)

    # 显示目标价位和止损位
    if signal.price_target or signal.stop_loss:
        console.print("\n[bold]价格参考:[/bold]")
        if signal.price_target:
            change_pct = (signal.price_target - current_price) / current_price * 100
            console.print(f"  目标价位: {signal.price_target:.3f} ({format_percentage(change_pct)})")
        if signal.stop_loss:
            loss_pct = (signal.stop_loss - current_price) / current_price * 100
            console.print(f"  止损价位: {signal.stop_loss:.3f} ({format_percentage(loss_pct)})")

    # 风险提示
    console.print("\n[bold yellow]⚠️ 风险提示:[/bold yellow]")
    console.print("  • 本建议仅供参考，不构成投资建议")
    console.print("  • 技术分析存在滞后性，市场随时可能变化")
    console.print("  • 请结合基本面分析和自身风险承受能力做决策")
    console.print(f"  • 当前风险等级: [bold]{signal.risk_level}[/bold]")


@cli.command()
@click.option('--pool', '-p', default=None, help='ETF池名称(不指定则使用默认池)')
@click.option('--days', '-d', default=60, help='分析天数')
@click.option('--output', '-o', type=click.Path(), help='输出文件路径')
@click.option('--format', '-f', type=click.Choice(['markdown', 'html']), default='markdown', help='报告格式')
@click.option('--list-pools', is_flag=True, help='列出所有可用的ETF池')
def batch(pool, days, output, format, list_pools):
    """批量生成ETF投资建议报告

    从配置的ETF池中批量分析所有ETF，生成综合投资建议报告。
    报告包含买入/卖出建议、综合评分排名等。

    示例:
        etf batch                           # 使用默认池
        etf batch --pool 行业主题           # 指定池
        etf batch --format html -o report.html  # 生成HTML报告
        etf batch --list-pools              # 查看所有池
    """
    from ..analysis.batch_reporter import BatchReportGenerator

    try:
        generator = BatchReportGenerator()

        # 列出所有池
        if list_pools:
            pools = generator.get_pool_list()
            console.print("\n[bold]可用的ETF池:[/bold]\n")

            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("池名称", style="cyan")
            table.add_column("描述")
            table.add_column("ETF数量", justify="right")

            for pool_name in pools:
                pool_info = generator.config['pools'][pool_name]
                table.add_row(
                    pool_name,
                    pool_info.get('description', 'N/A'),
                    str(len(pool_info['etfs']))
                )

            console.print(table)
            console.print(f"\n[dim]默认池: {generator.config.get('default_pool', 'N/A')}[/dim]")
            console.print(f"[dim]配置文件: {generator.config_path}[/dim]\n")
            return

        # 生成报告
        pool_name = pool or generator.config.get('default_pool', '宽基指数')

        with Progress() as progress:
            etf_codes = generator.get_pool_etfs(pool_name)
            task = progress.add_task(
                f"[cyan]正在分析 {len(etf_codes)} 只ETF...",
                total=None
            )

            content, recommendations = generator.generate_batch_report(
                pool_name=pool_name,
                days=days,
                output_format=format
            )

            progress.update(task, completed=True)

        # 保存报告
        if output:
            output_path = output
        else:
            ext = 'md' if format == 'markdown' else 'html'
            output_path = f"etf_batch_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{ext}"

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)

        console.print(f"\n[green]✓ 批量报告已生成: {output_path}[/green]\n")

        # 显示摘要
        categorized = {}
        for rec in recommendations:
            if rec.signal_type not in categorized:
                categorized[rec.signal_type] = []
            categorized[rec.signal_type].append(rec)

        console.print("[bold]📊 报告摘要[/bold]\n")
        console.print(f"ETF池: {pool_name}")
        console.print(f"分析天数: {days}天")
        console.print(f"成功分析: {len(recommendations)}只\n")

        # 分类统计
        buy_count = len(categorized.get('强烈买入', [])) + len(categorized.get('买入', []))
        sell_count = len(categorized.get('强烈卖出', [])) + len(categorized.get('卖出', []))
        hold_count = len(categorized.get('持有', []))

        console.print(f"[green]🟢 建议买入: {buy_count}只[/green]")
        if categorized.get('强烈买入'):
            console.print("  [bold green]强烈买入:[/bold green]")
            for rec in categorized['强烈买入'][:3]:
                console.print(f"    • {rec.name} ({rec.code}) - 评分 {rec.score:.1f}")

        console.print(f"\n[yellow]🟡 建议持有: {hold_count}只[/yellow]")

        console.print(f"\n[red]🔴 建议卖出: {sell_count}只[/red]")
        if categorized.get('强烈卖出'):
            console.print("  [bold red]强烈卖出:[/bold red]")
            for rec in categorized['强烈卖出']:
                console.print(f"    • {rec.name} ({rec.code}) - 评分 {rec.score:.1f}")

        # 综合排名前3
        if len(recommendations) >= 3:
            console.print("\n[bold]🏆 综合评分Top3[/bold]\n")
            for i, rec in enumerate(recommendations[:3], 1):
                score_color = "green" if rec.score >= 70 else "yellow" if rec.score >= 50 else "red"
                console.print(
                    f"{i}. {rec.name} ({rec.code}) - "
                    f"[{score_color}]{rec.score:.1f}分[/{score_color}] - "
                    f"{rec.signal_type}"
                )

        console.print("\n[dim]详细报告请查看生成的文件[/dim]\n")

    except FileNotFoundError as e:
        console.print(f"[red]错误: {str(e)}[/red]")
        console.print("\n[yellow]提示: 请确保 etf_pool.json 配置文件存在[/yellow]")
    except Exception as e:
        console.print(f"[red]错误: {str(e)}[/red]")
        import traceback
        traceback.print_exc()


@cli.command()
@click.option('--top', '-t', default=10, help='返回前N支ETF')
@click.option('--min-scale', '-s', default=5.0, help='最小规模(亿份)')
@click.option('--max-fee', '-f', default=0.60, help='最大费率(%)')
@click.option('--with-volume', '-v', is_flag=True, help='包含成交量分析(耗时较长)')
@click.option('--dedup/--no-dedup', default=True, help='是否按指数去重(默认开启)')
def screen(top, min_scale, max_fee, with_volume, dedup):
    """筛选流动性好、费率低的ETF

    根据基金规模和成交量筛选流动性最好的ETF。
    默认启用指数去重,相同指数只保留最优一支。

    示例:
        etf screen                           # 使用默认参数(去重)
        etf screen --no-dedup                # 关闭去重
        etf screen --top 20                  # 返回前20支
        etf screen --min-scale 10            # 最小规模10亿份
        etf screen --max-fee 0.50            # 最大费率0.50%
        etf screen --with-volume             # 包含成交量分析
    """
    from ..analysis.screener import ETFScreener

    try:
        with Progress() as progress:
            task = progress.add_task("[cyan]正在筛选ETF...", total=None)

            screener = ETFScreener()
            results = screener.screen_etfs(
                top_n=top,
                min_scale=min_scale,
                max_fee_rate=max_fee,
                include_volume=with_volume,
                etf_type='股票',
                dedup_by_index=dedup
            )

            progress.update(task, completed=True)

        if not results:
            console.print("[yellow]未找到符合条件的ETF[/yellow]")
            return

        # 显示筛选结果
        console.print(f"\n[green]✓ 找到 {len(results)} 支符合条件的ETF[/green]\n")
        console.print(f"[dim]筛选条件: 最小规模 {min_scale}亿份, 最大费率 {max_fee}%[/dim]")
        if dedup:
            console.print(f"[dim]指数去重: 已启用(相同指数只保留最优一支)[/dim]\n")
        else:
            console.print(f"[dim]指数去重: 已关闭[/dim]\n")

        # 创建结果表格
        table = Table(title="流动性优选ETF", show_header=True, header_style="bold magenta")
        table.add_column("排名", style="cyan", justify="center")
        table.add_column("代码", style="cyan")
        table.add_column("名称")
        table.add_column("指数类型", style="green")
        table.add_column("交易所", justify="center")
        table.add_column("规模(亿份)", justify="right")
        table.add_column("流动性评分", justify="right")

        if with_volume:
            table.add_column("平均成交额(亿)", justify="right")

        table.add_column("管理人")

        for i, result in enumerate(results, 1):
            # 流动性评分颜色
            if result.liquidity_score >= 80:
                score_color = "green"
            elif result.liquidity_score >= 60:
                score_color = "yellow"
            else:
                score_color = "white"

            # 提取指数类型
            index_type = screener.extract_index_name(result.name)

            row_data = [
                f"#{i}",
                result.code,
                result.name[:20],  # 限制名称长度
                index_type[:12],  # 限制指数类型长度
                result.exchange,
                f"{result.scale:.2f}",
                f"[{score_color}]{result.liquidity_score:.1f}[/{score_color}]"
            ]

            if with_volume:
                amount_str = f"{result.avg_amount:.2f}" if result.avg_amount else "N/A"
                row_data.append(amount_str)

            manager_str = result.fund_manager[:10] if result.fund_manager else "N/A"
            row_data.append(manager_str)

            table.add_row(*row_data)

        console.print(table)

        # 显示统计信息
        console.print("\n[bold]📊 统计信息[/bold]\n")

        total_scale = sum(r.scale for r in results)
        avg_score = sum(r.liquidity_score for r in results) / len(results)

        console.print(f"总规模: {total_scale:.2f} 亿份")
        console.print(f"平均流动性评分: {avg_score:.1f}")

        if with_volume:
            valid_amounts = [r.avg_amount for r in results if r.avg_amount]
            if valid_amounts:
                avg_amount = sum(valid_amounts) / len(valid_amounts)
                console.print(f"平均成交额: {avg_amount:.2f} 亿元/天")

        # 推荐说明
        console.print("\n[bold]💡 使用建议[/bold]\n")
        console.print("• 流动性评分 >= 80: 优秀,适合大额交易")
        console.print("• 流动性评分 60-80: 良好,适合中等规模交易")
        console.print("• 流动性评分 < 60: 一般,建议小额交易")
        console.print(f"• 当前筛选的ETF费率均 <= {max_fee}%")

        # 显示前3名的详细信息
        if len(results) >= 3:
            console.print("\n[bold]🏆 流动性前三名[/bold]\n")
            for i, result in enumerate(results[:3], 1):
                console.print(f"{i}. {result.name} ({result.code})")
                console.print(f"   规模: {result.scale:.2f}亿份, 评分: {result.liquidity_score:.1f}")
                if result.avg_amount:
                    console.print(f"   日均成交额: {result.avg_amount:.2f}亿元")
                if result.fund_manager:
                    console.print(f"   管理人: {result.fund_manager}")
                console.print()

    except Exception as e:
        console.print(f"[red]错误: {str(e)}[/red]")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    cli()


@cli.command()
@click.argument('code')
@click.option('--output', '-o', type=click.Path(), help='输出文件路径')
@click.option('--format', '-f', type=click.Choice(['markdown', 'html', 'json']), default='markdown', help='报告格式')
@click.option('--days', '-d', default=60, help='历史数据天数')
@click.option('--year', '-y', default='2024', help='持仓数据年份')
def report(code, output, format, days, year):
    """生成ETF综合分析报告"""
    from ..analysis.report import ReportGenerator, ETFAnalysisReport

    try:
        with Progress() as progress:
            task = progress.add_task("[cyan]正在生成报告...", total=None)

            # 获取基本信息
            etf_name = "未知ETF"
            quote_data = None
            try:
                quote = data_service.get_realtime_quote(code)
                if quote:
                    etf_name = quote.name
                    quote_data = {
                        'price': quote.price,
                        'change': quote.change,
                        'change_pct': quote.change_pct,
                        'open_price': quote.open_price,
                        'high': quote.high,
                        'low': quote.low,
                        'pre_close': quote.pre_close,
                        'volume': quote.volume,
                        'amount': quote.amount,
                    }
            except:
                pass

            # 获取历史数据
            end_date = datetime.now().strftime("%Y%m%d")
            start_date = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")
            df = data_service.get_historical_data(code, start_date, end_date)

            # 计算技术指标
            df = analyzer.calculate_returns(df)
            df = analyzer.calculate_moving_averages(df)
            df = analyzer.calculate_rsi(df)
            df = analyzer.calculate_macd(df)
            df = analyzer.calculate_bollinger_bands(df)

            # 分析表现
            performance = analyzer.analyze_performance(df)

            # 获取最新技术指标
            technical_indicators = {}
            if len(df) > 0:
                last_row = df.iloc[-1]
                technical_indicators = {
                    'MA5': last_row.get('MA5'),
                    'MA20': last_row.get('MA20'),
                    'RSI': last_row.get('RSI'),
                    'MACD': last_row.get('MACD'),
                    'Signal': last_row.get('Signal'),
                    'BB_Upper': last_row.get('BB_Upper'),
                    'BB_Middle': last_row.get('BB_Middle'),
                    'BB_Lower': last_row.get('BB_Lower'),
                }

            # 生成交易建议
            premium_rate = None
            try:
                premium_list = data_service.calculate_premium_discount(code, 5)
                if premium_list:
                    premium_rate = premium_list[-1].premium_rate
            except:
                pass

            signal = advisor.analyze(df, premium_rate)
            trading_signal_data = {
                'signal_type': signal.signal_type.value,
                'confidence': signal.confidence,
                'risk_level': signal.risk_level,
                'reasons': signal.reasons,
                'indicators': signal.indicators,
                'price_target': signal.price_target,
                'stop_loss': signal.stop_loss,
            }

            # 溢价分析
            premium_analysis = None
            try:
                premium_list = data_service.calculate_premium_discount(code, 30)
                if premium_list:
                    rates = [p.premium_rate for p in premium_list]
                    premium_analysis = {
                        'current_premium': premium_list[-1].premium_rate,
                        'avg_premium': sum(rates) / len(rates),
                        'max_premium': max(rates),
                        'min_premium': min(rates),
                    }
            except:
                pass

            # 持仓信息
            holdings_data = None
            holdings_summary = None
            try:
                holdings = data_service.get_etf_holdings(code, year)
                if holdings:
                    holdings_data = [
                        {
                            'code': h.stock_code,
                            'name': h.stock_name,
                            'weight': h.weight
                        }
                        for h in holdings[:20]
                    ]
                    holdings_summary = analyzer.analyze_holdings(holdings)
            except:
                pass

            # 最近价格
            recent_prices = []
            for _, row in df.tail(10).iterrows():
                recent_prices.append({
                    'date': row['日期'],
                    'close': row['收盘'],
                    'change_pct': row.get('涨跌幅', 0)
                })

            # 创建报告对象
            report_obj = ETFAnalysisReport(
                code=code,
                name=etf_name,
                report_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                quote=quote_data,
                performance=performance,
                technical_indicators=technical_indicators,
                trading_signal=trading_signal_data,
                holdings=holdings_data,
                holdings_summary=holdings_summary,
                premium_analysis=premium_analysis,
                recent_prices=recent_prices
            )

            # 生成报告
            generator = ReportGenerator()
            if format == 'markdown':
                content = generator.generate_markdown(report_obj)
                ext = 'md'
            elif format == 'html':
                content = generator.generate_html(report_obj)
                ext = 'html'
            else:  # json
                content = generator.generate_json(report_obj)
                ext = 'json'

            progress.update(task, completed=True)

        # 输出或保存
        if output:
            output_path = output
        else:
            output_path = f"{code}_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{ext}"

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)

        console.print(f"\n[green]✓ 报告已生成: {output_path}[/green]")

        # 显示摘要
        console.print(f"\n[bold]报告摘要:[/bold]")
        console.print(f"ETF: {etf_name} ({code})")
        console.print(f"格式: {format.upper()}")
        console.print(f"分析天数: {days}天")

        if quote_data:
            color = get_color_by_value(quote_data['change_pct'])
            console.print(f"当前价格: {quote_data['price']:.3f} ([{color}]{quote_data['change_pct']:+.2f}%[/{color}])")

        console.print(f"交易建议: {trading_signal_data['signal_type']} (置信度: {trading_signal_data['confidence']:.0f}%)")

    except Exception as e:
        console.print(f"[red]错误: {str(e)}[/red]")
        import traceback
        traceback.print_exc()


@cli.command()
@click.argument('codes', nargs=-1, required=True)
@click.option('--days', '-d', default=60, help='分析天数')
@click.option('--output', '-o', type=click.Path(), help='输出文件路径')
@click.option('--format', '-f', type=click.Choice(['table', 'markdown', 'html']), default='table', help='输出格式')
def compare(codes, days, output, format):
    """批量对比多个ETF

    示例：
        etf compare 510300 510500 159915
        etf compare 510300 510500 --format markdown --output compare.md
    """
    from ..analysis.comparator import ETFComparator

    if len(codes) < 2:
        console.print("[red]错误: 至少需要2个ETF代码进行对比[/red]")
        return

    try:
        with Progress() as progress:
            task = progress.add_task(f"[cyan]正在对比 {len(codes)} 只ETF...", total=None)

            comparator = ETFComparator()
            results = comparator.compare(list(codes), days)

            progress.update(task, completed=True)

        if not results:
            console.print("[red]未能获取任何ETF数据[/red]")
            return

        console.print(f"\n[green]✓ 成功分析 {len(results)}/{len(codes)} 只ETF[/green]\n")

        if format == 'table':
            # 在终端显示表格
            _display_comparison_table(results)

        elif format in ['markdown', 'html']:
            # 生成报告文件
            content = comparator.generate_comparison_report(results, format)

            if output:
                output_path = output
            else:
                ext = 'md' if format == 'markdown' else 'html'
                output_path = f"etf_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{ext}"

            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)

            console.print(f"[green]✓ 对比报告已生成: {output_path}[/green]")

    except Exception as e:
        console.print(f"[red]错误: {str(e)}[/red]")
        import traceback
        traceback.print_exc()


def _display_comparison_table(results):
    """在终端显示对比表格"""
    from ..analysis.comparator import ETFComparison

    # 综合排名表
    console.print("[bold]📊 综合排名[/bold]\n")
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("排名", style="cyan", justify="center")
    table.add_column("代码", style="cyan")
    table.add_column("名称")
    table.add_column("评分", justify="right")
    table.add_column("建议", justify="center")
    table.add_column("置信度", justify="right")

    for i, comp in enumerate(results, 1):
        # 确定颜色
        if comp.signal_type in ["强烈买入", "买入"]:
            signal_color = "green"
        elif comp.signal_type in ["强烈卖出", "卖出"]:
            signal_color = "red"
        else:
            signal_color = "yellow"

        # 评分颜色
        if comp.score >= 70:
            score_color = "green"
        elif comp.score >= 50:
            score_color = "yellow"
        else:
            score_color = "red"

        table.add_row(
            f"#{i}",
            comp.code,
            comp.name[:20],  # 限制名称长度
            f"[{score_color}]{comp.score:.1f}[/{score_color}]",
            f"[{signal_color}]{comp.signal_type}[/{signal_color}]",
            f"{comp.confidence:.0f}%"
        )

    console.print(table)

    # 实时行情对比
    console.print("\n[bold]📈 实时行情对比[/bold]\n")
    table2 = Table(show_header=True, header_style="bold magenta")
    table2.add_column("代码", style="cyan")
    table2.add_column("名称")
    table2.add_column("最新价", justify="right")
    table2.add_column("涨跌幅", justify="right")

    for comp in results:
        color = get_color_by_value(comp.change_pct)
        table2.add_row(
            comp.code,
            comp.name[:20],
            f"{comp.price:.3f}",
            f"[{color}]{comp.change_pct:+.2f}%[/{color}]"
        )

    console.print(table2)

    # 历史表现对比
    console.print("\n[bold]📊 历史表现对比[/bold]\n")
    table3 = Table(show_header=True, header_style="bold magenta")
    table3.add_column("代码", style="cyan")
    table3.add_column("年化收益", justify="right")
    table3.add_column("波动率", justify="right")
    table3.add_column("夏普比率", justify="right")
    table3.add_column("最大回撤", justify="right")
    table3.add_column("风险", justify="center")

    for comp in results:
        return_color = get_color_by_value(comp.annual_return)

        # 风险等级颜色
        risk_colors = {"低": "green", "中": "yellow", "高": "red"}
        risk_color = risk_colors.get(comp.risk_level, "white")

        table3.add_row(
            comp.code,
            f"[{return_color}]{comp.annual_return:+.2f}%[/{return_color}]",
            f"{comp.volatility:.2f}%",
            f"{comp.sharpe_ratio:.2f}",
            f"{comp.max_drawdown:.2f}%",
            f"[{risk_color}]{comp.risk_level}[/{risk_color}]"
        )

    console.print(table3)

    # 技术指标统计
    console.print("\n[bold]🔧 技术指标统计[/bold]\n")
    table4 = Table(show_header=True, header_style="bold magenta")
    table4.add_column("代码", style="cyan")
    table4.add_column("看涨", justify="center", style="green")
    table4.add_column("看跌", justify="center", style="red")
    table4.add_column("中性", justify="center", style="yellow")
    table4.add_column("综合", justify="center")

    for comp in results:
        total = comp.bullish_count + comp.bearish_count + comp.neutral_count
        trend = "↗" if comp.bullish_count > comp.bearish_count else "↘" if comp.bearish_count > comp.bullish_count else "→"

        table4.add_row(
            comp.code,
            str(comp.bullish_count),
            str(comp.bearish_count),
            str(comp.neutral_count),
            trend
        )

    console.print(table4)

    # 推荐建议
    if results:
        console.print("\n[bold]💡 推荐建议[/bold]\n")

        best = results[0]
        console.print(f"🏆 [green]综合评分最高[/green]: {best.name} ({best.code}) - 评分 {best.score:.1f}")

        best_return = max(results, key=lambda x: x.annual_return)
        console.print(f"📈 [green]最高年化收益[/green]: {best_return.name} ({best_return.code}) - {best_return.annual_return:+.2f}%")

        best_sharpe = max(results, key=lambda x: x.sharpe_ratio)
        console.print(f"⚖️ [green]最佳夏普比率[/green]: {best_sharpe.name} ({best_sharpe.code}) - {best_sharpe.sharpe_ratio:.2f}")

        best_risk = min(results, key=lambda x: x.volatility)
        console.print(f"🛡️ [green]最低波动率[/green]: {best_risk.name} ({best_risk.code}) - {best_risk.volatility:.2f}%")


@cli.group()
def monitor():
    """ETF定时监控和报告生成服务"""
    pass


@monitor.command()
@click.option('--daemon', '-d', is_flag=True, help='后台运行（守护进程模式）')
@click.option('--config', '-c', type=click.Path(), help='配置文件路径')
def start(daemon, config):
    """启动监控服务

    示例:
        etf monitor start                    # 前台运行
        etf monitor start --daemon           # 后台运行
        etf monitor start -c custom.toml     # 使用自定义配置
    """
    from ..scheduler.job_scheduler import ReportScheduler
    from ..scheduler.daemon import MonitorDaemon
    from ..config.scheduler_config import SchedulerConfig
    import logging

    # 配置日志
    log_dir = Path.home() / '.etf_challenger' / 'logs'
    log_dir.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_dir / 'scheduler.log'),
            logging.StreamHandler()
        ]
    )

    if daemon:
        console.print("[green]正在启动守护进程...[/green]")
        daemon_process = MonitorDaemon(config)
        success = daemon_process.start()
        if success:
            console.print("[green]✓ 监控服务已在后台启动[/green]")
        else:
            console.print("[red]✗ 守护进程启动失败[/red]")
    else:
        console.print("[cyan]启动监控服务（前台模式）...[/cyan]")
        config_obj = SchedulerConfig.from_file(Path(config) if config else None)

        # 验证配置
        errors = config_obj.validate()
        if errors:
            console.print("[red]配置错误:[/red]")
            for error in errors:
                console.print(f"  - {error}")
            console.print("\n[yellow]提示: 使用 'etf monitor config' 配置邮箱信息[/yellow]")
            return

        scheduler = ReportScheduler(config_obj)
        scheduler.start()

        console.print("[green]✓ 监控服务已启动[/green]")
        console.print(f"早盘报告: 每个交易日 {config_obj.market.morning_report_time}")
        console.print(f"尾盘报告: 每个交易日 {config_obj.market.afternoon_report_time}")
        console.print("\n按 Ctrl+C 停止服务...")

        try:
            import time
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            scheduler.stop()
            console.print("\n[yellow]监控服务已停止[/yellow]")


@monitor.command()
def stop():
    """停止监控服务"""
    from ..scheduler.daemon import MonitorDaemon

    daemon = MonitorDaemon()
    success = daemon.stop()

    if success:
        console.print("[green]✓ 监控服务已停止[/green]")
    else:
        console.print("[red]✗ 停止监控服务失败[/red]")


@monitor.command()
def status():
    """查看监控服务状态"""
    from ..scheduler.daemon import MonitorDaemon
    from pathlib import Path

    daemon = MonitorDaemon()
    status_info = daemon.get_status()

    console.print("\n[bold cyan]监控服务状态[/bold cyan]\n")

    if status_info['running']:
        console.print(f"运行状态: [green]运行中[/green]")
        console.print(f"进程ID: {status_info['pid']}")

        # 检查日志文件
        log_file = Path.home() / '.etf_challenger' / 'logs' / 'scheduler.log'
        if log_file.exists():
            console.print(f"日志文件: {log_file}")
            console.print(f"日志大小: {log_file.stat().st_size / 1024:.1f} KB")
    else:
        console.print(f"运行状态: [red]已停止[/red]")
        console.print("[yellow]提示: 使用 'etf monitor start' 启动服务[/yellow]")


@monitor.command()
@click.option('--session', type=click.Choice(['morning', 'afternoon']), required=True, help='时段')
@click.option('--pools', multiple=True, help='ETF池名称（不指定则生成所有池）')
def trigger(session, pools):
    """手动触发报告生成（不受调度限制）

    示例:
        etf monitor trigger --session morning
        etf monitor trigger --session afternoon --pools 精选组合 --pools 宽基指数
    """
    from ..scheduler.report_job import ReportJob
    from ..config.scheduler_config import SchedulerConfig

    config = SchedulerConfig.default()

    if pools:
        config.watchlists.pools = list(pools)

    job = ReportJob(config)

    with console.status(f"[cyan]正在生成{session}报告...[/cyan]"):
        result = job.execute(session)

    if result.success:
        console.print(f"[green]✓ 成功生成{result.reports_generated}个报告[/green]")
        console.print(f"处理池: {result.pools_processed}个")
        if result.summary_path:
            console.print(f"汇总文件: {result.summary_path}")
    else:
        console.print(f"[red]✗ 报告生成失败[/red]")
        for error in result.errors:
            console.print(f"  - {error}")


@monitor.command('send-email')
@click.option('--session', type=click.Choice(['morning', 'afternoon']), default='afternoon', help='时段（默认尾盘）')
@click.option('--date', type=str, default=None, help='日期（YYYY-MM-DD格式，默认今天）')
def send_email(session, date):
    """手动发送邮件日报

    发送已生成的报告邮件。如果当天没有生成报告，会先生成报告再发送。

    示例:
        etf monitor send-email                          # 发送今天的尾盘报告
        etf monitor send-email --session morning        # 发送今天的早盘报告
        etf monitor send-email --date 2026-02-10        # 发送指定日期的报告
    """
    from datetime import datetime
    from ..config.scheduler_config import SchedulerConfig
    from ..notification.email_service import EmailService
    from ..notification.report_digest import ReportDigest
    from ..storage.report_storage import ReportStorage
    from ..scheduler.report_job import ReportJob

    try:
        config = SchedulerConfig.from_file()

        # 验证邮件配置
        errors = config.email.validate()
        if errors:
            console.print("[red]邮件配置错误:[/red]")
            for error in errors:
                console.print(f"  - {error}")
            console.print("\n[yellow]请先使用 'etf monitor config' 配置邮箱信息[/yellow]")
            return

        # 解析日期
        if date:
            try:
                report_date = datetime.strptime(date, '%Y-%m-%d')
            except ValueError:
                console.print("[red]日期格式错误，请使用 YYYY-MM-DD 格式[/red]")
                return
        else:
            report_date = datetime.now()

        # 获取汇总数据
        storage = ReportStorage(config.storage.get_base_path())
        summary_data = storage.get_summary(report_date, session)

        # 如果没有数据，先生成报告
        if not summary_data:
            console.print(f"[yellow]未找到 {report_date:%Y-%m-%d} {session} 的报告，正在生成...[/yellow]")
            job = ReportJob(config)
            result = job.execute(session)
            if not result.success:
                console.print("[red]报告生成失败[/red]")
                return
            summary_data = storage.get_summary(report_date, session)

        if not summary_data:
            console.print("[red]无法获取报告数据[/red]")
            return

        # 生成邮件内容
        session_cn = '早盘' if session == 'morning' else '尾盘'
        subject = f"[ETF监控] {report_date:%Y-%m-%d} {session_cn}报告"

        with console.status(f"[cyan]正在生成邮件内容...[/cyan]"):
            html_content = ReportDigest.generate_html_digest(
                session=session,
                recommendations=summary_data.get('recommendations', []),
                pools=config.watchlists.pools
            )

        # 发送邮件
        with console.status(f"[cyan]正在发送邮件...[/cyan]"):
            email_service = EmailService(config.email)
            email_service.send_email(
                subject=subject,
                body=html_content,
                body_type='html'
            )

        console.print(f"[green]✓ 邮件已发送[/green]")
        console.print(f"  主题: {subject}")
        console.print(f"  收件人: {', '.join(config.email.recipients)}")

    except FileNotFoundError:
        console.print("[red]未找到配置文件[/red]")
        console.print("[yellow]请先使用 'etf monitor config' 配置邮箱信息[/yellow]")
    except Exception as e:
        console.print(f"[red]发送失败: {e}[/red]")


@monitor.command('config')
@click.option('--email', prompt='发件邮箱', help='163邮箱地址')
@click.option('--password', prompt='授权码', hide_input=True, help='163邮箱授权码')
@click.option('--recipients', prompt='收件人（逗号分隔）', help='收件人邮箱列表')
def configure(email, password, recipients):
    """配置监控服务参数

    注意: 163邮箱需要使用授权码，不是登录密码
    获取授权码: 登录163邮箱 -> 设置 -> POP3/SMTP/IMAP -> 开启服务 -> 获取授权码
    """
    from ..config.scheduler_config import SchedulerConfig
    from pathlib import Path

    config = SchedulerConfig.default()
    config.email.sender_email = email
    config.email.sender_password = password
    config.email.recipients = [r.strip() for r in recipients.split(',')]

    config_path = Path.home() / '.etf_challenger' / 'config' / 'scheduler_config.toml'

    config.save(config_path)

    console.print(f"\n[green]✓ 配置已保存到: {config_path}[/green]\n")
    console.print("配置摘要:")
    console.print(f"  发件邮箱: {email}")
    console.print(f"  收件人: {', '.join(config.email.recipients)}")
    console.print(f"\n[yellow]提示: 请使用 'etf monitor test-email' 测试邮件配置[/yellow]")


@monitor.command('test-email')
def test_email():
    """发送测试邮件"""
    from ..config.scheduler_config import SchedulerConfig
    from ..notification.email_service import EmailService

    try:
        config = SchedulerConfig.from_file()

        # 验证配置
        errors = config.email.validate()
        if errors:
            console.print("[red]邮件配置错误:[/red]")
            for error in errors:
                console.print(f"  - {error}")
            console.print("\n[yellow]请先使用 'etf monitor config' 配置邮箱信息[/yellow]")
            return

        email_service = EmailService(config.email)

        with console.status("[cyan]正在发送测试邮件...[/cyan]"):
            email_service.send_test_email()

        console.print("[green]✓ 测试邮件已发送，请检查收件箱[/green]")

    except Exception as e:
        console.print(f"[red]✗ 发送失败: {e}[/red]")


@monitor.command()
@click.option('--date', type=click.DateTime(formats=['%Y-%m-%d']), help='日期（默认今天）')
@click.option('--session', type=click.Choice(['morning', 'afternoon']), help='时段（不指定则显示全天）')
def reports(date, session):
    """查看已生成的报告列表"""
    from ..storage.report_storage import ReportStorage
    from pathlib import Path

    storage = ReportStorage()
    target_date = date or datetime.now()

    report_files = storage.list_reports(target_date, session)

    if not report_files:
        console.print(f"[yellow]未找到{target_date:%Y-%m-%d}的报告[/yellow]")
        return

    table = Table(title=f"报告列表 - {target_date:%Y-%m-%d}")
    table.add_column("时段", style="cyan")
    table.add_column("ETF池", style="green")
    table.add_column("格式", style="yellow")
    table.add_column("文件大小", style="magenta")
    table.add_column("路径", style="blue")

    for report_file in report_files:
        # 解析文件名: 精选组合_20260201_1000.html
        parts = report_file.stem.split('_')
        if len(parts) >= 3:
            pool_name = parts[0]
            time_part = parts[2]
            session_name = 'morning' if int(time_part) < 1200 else 'afternoon'

            table.add_row(
                session_name,
                pool_name,
                report_file.suffix[1:],
                f"{report_file.stat().st_size / 1024:.1f} KB",
                str(report_file)
            )

    console.print(table)

@cli.command()
@click.option('--strategy', '-s', 
              type=click.Choice(['conservative', 'balanced', 'aggressive']), 
              default='balanced',
              help='推荐策略（保守/稳健/激进）')
@click.option('--top', '-t', default=10, help='返回前N支推荐')
@click.option('--industry', '-i', multiple=True, help='筛选特定行业（可多选）')
@click.option('--min-scale', default=10.0, help='最小规模（亿份）')
@click.option('--detail', is_flag=True, help='显示详细评分明细')
def recommend(strategy, top, industry, min_scale, detail):
    """智能ETF推荐

    基于多维度评分系统（收益、风险、流动性、费率、技术面）为您推荐优质ETF。
    支持三种推荐策略，满足不同风险偏好。

    示例：
        etf recommend                            # 稳健型推荐
        etf recommend --strategy conservative    # 保守型推荐
        etf recommend --strategy aggressive      # 激进型推荐
        etf recommend --top 20                   # 返回前20支
        etf recommend --industry 科技 医药       # 特定行业
        etf recommend --detail                   # 显示详细评分
    """
    from ..analysis.screener import ETFScreener
    
    try:
        # 初始化评分器和解释器
        strategy_enum = {
            'conservative': ScoringStrategy.CONSERVATIVE,
            'balanced': ScoringStrategy.BALANCED,
            'aggressive': ScoringStrategy.AGGRESSIVE
        }[strategy]
        
        scorer = ETFScorer(strategy=strategy_enum)
        explainer = RecommendationExplainer()
        screener = ETFScreener()
        
        with Progress() as progress:
            task = progress.add_task(f"[cyan]正在分析ETF并生成推荐...", total=None)
            
            # 1. 获取候选ETF列表（使用筛选器，带去重）
            candidates = screener.screen_etfs(
                top_n=top * 3,  # 多获取一些用于后续评分排序
                min_scale=min_scale,
                max_fee_rate=0.6,
                include_volume=False,
                etf_type='股票',
                dedup_by_index=True
            )
            
            if not candidates:
                console.print("[yellow]未找到符合条件的ETF[/yellow]")
                return
            
            # 2. 对每个ETF进行详细评分
            recommendations = []
            
            for candidate in candidates:
                try:
                    # 获取历史数据和技术指标
                    end_date = datetime.now().strftime("%Y%m%d")
                    start_date = (datetime.now() - timedelta(days=90)).strftime("%Y%m%d")
                    
                    df = data_service.get_historical_data(candidate.code, start_date, end_date)
                    
                    if df.empty:
                        continue
                    
                    # 计算技术指标
                    df = analyzer.calculate_returns(df)
                    df = analyzer.calculate_moving_averages(df)
                    df = analyzer.calculate_rsi(df)
                    df = analyzer.calculate_macd(df)
                    
                    # 分析表现指标
                    performance = analyzer.analyze_performance(df)
                    
                    # 提取评分所需数据
                    annual_return = float(performance['年化收益率(%)'])
                    volatility = float(performance['年化波动率(%)'])
                    max_drawdown = float(performance['最大回撤(%)'])
                    sharpe_ratio = float(performance['夏普比率'])
                    
                    # 获取费率
                    fee_rate = screener.get_fee_rate(candidate.code)
                    
                    # 计算评分
                    score_breakdown = scorer.calculate_score(
                        etf_code=candidate.code,
                        etf_name=candidate.name,
                        annual_return=annual_return,
                        sharpe_ratio=sharpe_ratio,
                        volatility=volatility,
                        max_drawdown=max_drawdown,
                        scale=candidate.scale,
                        liquidity_score=candidate.liquidity_score,
                        fee_rate=fee_rate,
                        df=df
                    )
                    
                    # 生成推荐理由
                    reasons = explainer.generate_reasons(
                        etf_code=candidate.code,
                        etf_name=candidate.name,
                        score_breakdown=score_breakdown,
                        annual_return=annual_return,
                        volatility=volatility,
                        scale=candidate.scale,
                        fee_rate=fee_rate
                    )
                    
                    # 生成风险提示
                    warnings = explainer.generate_risk_warnings(
                        score_breakdown=score_breakdown,
                        annual_return=annual_return,
                        volatility=volatility,
                        max_drawdown=max_drawdown
                    )
                    
                    # 生成置信度
                    confidence = explainer.generate_confidence_level(score_breakdown)
                    
                    # 行业筛选
                    if industry:
                        index_type = screener.extract_index_name(candidate.name)
                        if not any(ind in index_type or ind in candidate.name for ind in industry):
                            continue
                    
                    recommendations.append({
                        'code': candidate.code,
                        'name': candidate.name,
                        'score_breakdown': score_breakdown,
                        'reasons': reasons,
                        'warnings': warnings,
                        'confidence': confidence,
                        'annual_return': annual_return,
                        'volatility': volatility,
                        'scale': candidate.scale,
                        'fee_rate': fee_rate,
                        'index_type': screener.extract_index_name(candidate.name)
                    })
                    
                except Exception as e:
                    # 跳过出错的ETF，但记录错误信息
                    console.print(f"[dim yellow]跳过 {candidate.code} {candidate.name}: {str(e)}[/dim yellow]")
                    continue
            
            progress.update(task, completed=True)
        
        # 3. 按评分排序
        recommendations.sort(key=lambda x: x['score_breakdown'].total_score, reverse=True)
        recommendations = recommendations[:top]
        
        if not recommendations:
            console.print("[yellow]未找到符合条件的推荐ETF[/yellow]")
            return
        
        # 4. 显示推荐结果
        _display_recommendations(recommendations, scorer, detail)
        
    except Exception as e:
        console.print(f"[red]错误: {str(e)}[/red]")
        import traceback
        traceback.print_exc()


def _display_recommendations(recommendations, scorer, show_detail):
    """显示推荐结果"""
    
    # 标题面板
    strategy_desc = scorer.get_strategy_description()
    header = f"""
[bold cyan]智能ETF推荐[/bold cyan]

策略: {strategy_desc}
推荐数量: {len(recommendations)}支
更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    """
    console.print(Panel(header.strip(), border_style="cyan"))
    
    # 推荐列表
    for i, rec in enumerate(recommendations, 1):
        score = rec['score_breakdown']
        
        # 根据评分确定颜色
        if score.total_score >= 80:
            score_color = "green"
            score_icon = "🌟"
        elif score.total_score >= 70:
            score_color = "yellow"
            score_icon = "⭐"
        else:
            score_color = "white"
            score_icon = "✦"
        
        # ETF信息面板
        info = f"""
[bold]{score_icon} #{i} {rec['name']}[/bold] ({rec['code']})

[{score_color}]综合评分: {score.total_score:.1f}分[/{score_color}]  |  置信度: {rec['confidence'][0]}
指数类型: {rec['index_type']}  |  规模: {rec['scale']:.0f}亿份  |  费率: {rec['fee_rate']:.2f}%

[bold green]✓ 推荐理由:[/bold green]
"""
        for reason in rec['reasons']:
            info += f"  {reason}\n"
        
        # 风险提示
        if rec['warnings']:
            info += "\n[bold yellow]⚠ 风险提示:[/bold yellow]\n"
            for warning in rec['warnings']:
                info += f"  {warning}\n"
        
        # 详细评分
        if show_detail:
            info += f"""
[bold]📊 评分明细:[/bold]
  收益潜力: {score.return_score:.1f}  风险评估: {score.risk_score:.1f}
  流动性: {score.liquidity_score:.1f}  费率优势: {score.fee_score:.1f}  技术面: {score.technical_score:.1f}

[dim]年化收益: {rec['annual_return']:+.1f}%  |  波动率: {rec['volatility']:.1f}%[/dim]
"""
        
        console.print(Panel(info.strip(), border_style=score_color))
        console.print()
    
    # 使用说明
    console.print("[bold]💡 使用建议[/bold]")
    console.print("  • 综合评分 ≥80: 强烈推荐，各项指标优秀")
    console.print("  • 综合评分 70-80: 推荐，整体表现良好")
    console.print("  • 综合评分 <70: 谨慎，建议深入研究")
    console.print()
    console.print("[dim]提示: 使用 --detail 选项查看详细评分明细[/dim]")
    console.print("[dim]提示: 推荐结果仅供参考，投资需谨慎[/dim]")
