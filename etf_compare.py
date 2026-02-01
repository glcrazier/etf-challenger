#!/usr/bin/env python3
"""
ETF批量对比分析工具

使用方法:
    python etf_compare.py 510300 510500 159915
    python etf_compare.py 510300 510500 --format html --output compare.html
"""

import sys
import argparse
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from etf_challenger.analysis.comparator import ETFComparator
from rich.console import Console
from rich.table import Table
from rich.progress import Progress


def main():
    parser = argparse.ArgumentParser(description='批量对比多个ETF')
    parser.add_argument('codes', nargs='+', help='ETF代码列表')
    parser.add_argument('--days', '-d', type=int, default=60, help='分析天数')
    parser.add_argument('--output', '-o', help='输出文件路径')
    parser.add_argument('--format', '-f', choices=['table', 'markdown', 'html'],
                       default='table', help='输出格式')

    args = parser.parse_args()

    if len(args.codes) < 2:
        print("错误: 至少需要2个ETF代码进行对比")
        sys.exit(1)

    console = Console()

    try:
        with Progress() as progress:
            task = progress.add_task(f"[cyan]正在对比 {len(args.codes)} 只ETF...", total=None)

            comparator = ETFComparator()
            results = comparator.compare(args.codes, args.days)

            progress.update(task, completed=True)

        if not results:
            console.print("[red]未能获取任何ETF数据[/red]")
            return

        console.print(f"\n[green]✓ 成功分析 {len(results)}/{len(args.codes)} 只ETF[/green]\n")

        if args.format == 'table':
            # 在终端显示表格
            display_comparison_table(console, results)

        elif args.format in ['markdown', 'html']:
            # 生成报告文件
            content = comparator.generate_comparison_report(results, args.format)

            if args.output:
                output_path = args.output
            else:
                from datetime import datetime
                ext = 'md' if args.format == 'markdown' else 'html'
                output_path = f"etf_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{ext}"

            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)

            console.print(f"[green]✓ 对比报告已生成: {output_path}[/green]")

    except Exception as e:
        console.print(f"[red]错误: {str(e)}[/red]")
        import traceback
        traceback.print_exc()


def display_comparison_table(console, results):
    """在终端显示对比表格"""
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
            comp.name[:20],
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
        color = "green" if comp.change_pct > 0 else "red" if comp.change_pct < 0 else "white"
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
        return_color = "green" if comp.annual_return > 0 else "red"
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


if __name__ == '__main__':
    main()
