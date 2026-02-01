#!/usr/bin/env python3
"""
数据源性能基准测试工具

测试各个akshare数据源的:
1. 响应速度
2. 成功率
3. 数据完整性
"""

import time
import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from rich.console import Console
from rich.table import Table
from rich.progress import Progress


console = Console()


class DataSourceBenchmark:
    """数据源基准测试"""

    def __init__(self, test_rounds: int = 5):
        self.test_rounds = test_rounds
        self.results = {}

    def test_etf_spot_em(self) -> Dict:
        """测试东方财富实时行情数据源"""
        console.print("\n[cyan]测试 fund_etf_spot_em (东方财富实时行情)...[/cyan]")

        times = []
        successes = 0
        data_quality = []

        for i in range(self.test_rounds):
            try:
                start = time.time()
                df = ak.fund_etf_spot_em()
                elapsed = time.time() - start

                times.append(elapsed)
                successes += 1

                # 检查数据完整性
                required_cols = ['代码', '名称', '最新价', '涨跌幅', '成交量', '成交额']
                has_all_cols = all(col in df.columns for col in required_cols)
                has_data = len(df) > 0
                no_null_key_fields = df[['代码', '名称', '最新价']].notna().all().all()

                quality_score = sum([has_all_cols, has_data, no_null_key_fields]) / 3 * 100
                data_quality.append(quality_score)

                console.print(f"  轮次 {i+1}: ✓ {elapsed:.2f}s, 数据行数: {len(df)}")

            except Exception as e:
                console.print(f"  轮次 {i+1}: ✗ 失败 - {str(e)[:50]}")
                time.sleep(1)

        return {
            'name': 'fund_etf_spot_em',
            'description': '东方财富实时行情',
            'success_rate': successes / self.test_rounds * 100,
            'avg_time': sum(times) / len(times) if times else None,
            'min_time': min(times) if times else None,
            'max_time': max(times) if times else None,
            'avg_quality': sum(data_quality) / len(data_quality) if data_quality else 0,
            'successes': successes
        }

    def test_etf_spot_ths(self) -> Dict:
        """测试同花顺实时行情数据源"""
        console.print("\n[cyan]测试 fund_etf_spot_ths (同花顺实时行情)...[/cyan]")

        times = []
        successes = 0
        data_quality = []

        for i in range(self.test_rounds):
            try:
                start = time.time()
                df = ak.fund_etf_spot_ths()
                elapsed = time.time() - start

                times.append(elapsed)
                successes += 1

                # 检查数据完整性
                required_cols = ['基金代码', '基金名称', '当前-单位净值']
                has_all_cols = all(col in df.columns for col in required_cols)
                has_data = len(df) > 0
                no_null_key_fields = df[['基金代码', '基金名称']].notna().all().all()

                quality_score = sum([has_all_cols, has_data, no_null_key_fields]) / 3 * 100
                data_quality.append(quality_score)

                console.print(f"  轮次 {i+1}: ✓ {elapsed:.2f}s, 数据行数: {len(df)}")

            except Exception as e:
                console.print(f"  轮次 {i+1}: ✗ 失败 - {str(e)[:50]}")
                time.sleep(1)

        return {
            'name': 'fund_etf_spot_ths',
            'description': '同花顺实时行情',
            'success_rate': successes / self.test_rounds * 100,
            'avg_time': sum(times) / len(times) if times else None,
            'min_time': min(times) if times else None,
            'max_time': max(times) if times else None,
            'avg_quality': sum(data_quality) / len(data_quality) if data_quality else 0,
            'successes': successes
        }

    def test_etf_hist_em(self) -> Dict:
        """测试东方财富历史数据源"""
        console.print("\n[cyan]测试 fund_etf_hist_em (东方财富历史行情)...[/cyan]")

        times = []
        successes = 0
        data_quality = []
        test_code = "510300"  # 沪深300ETF

        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")

        for i in range(self.test_rounds):
            try:
                start = time.time()
                df = ak.fund_etf_hist_em(
                    symbol=test_code,
                    period="daily",
                    start_date=start_date,
                    end_date=end_date,
                    adjust="qfq"
                )
                elapsed = time.time() - start

                times.append(elapsed)
                successes += 1

                # 检查数据完整性
                required_cols = ['日期', '开盘', '收盘', '最高', '最低', '成交量']
                has_all_cols = all(col in df.columns for col in required_cols)
                has_data = len(df) > 0
                no_null = df[required_cols].notna().all().all()

                quality_score = sum([has_all_cols, has_data, no_null]) / 3 * 100
                data_quality.append(quality_score)

                console.print(f"  轮次 {i+1}: ✓ {elapsed:.2f}s, 数据行数: {len(df)}")

            except Exception as e:
                console.print(f"  轮次 {i+1}: ✗ 失败 - {str(e)[:50]}")
                time.sleep(1)

        return {
            'name': 'fund_etf_hist_em',
            'description': '东方财富历史行情',
            'success_rate': successes / self.test_rounds * 100,
            'avg_time': sum(times) / len(times) if times else None,
            'min_time': min(times) if times else None,
            'max_time': max(times) if times else None,
            'avg_quality': sum(data_quality) / len(data_quality) if data_quality else 0,
            'successes': successes
        }

    def test_portfolio_hold_em(self) -> Dict:
        """测试持仓数据源"""
        console.print("\n[cyan]测试 fund_portfolio_hold_em (持仓数据)...[/cyan]")

        times = []
        successes = 0
        data_quality = []
        test_code = "510300"
        test_year = "2024"

        for i in range(self.test_rounds):
            try:
                start = time.time()
                df = ak.fund_portfolio_hold_em(symbol=test_code, date=test_year)
                elapsed = time.time() - start

                times.append(elapsed)
                successes += 1

                # 检查数据完整性
                required_cols = ['股票代码', '股票名称', '占净值比例']
                has_all_cols = all(col in df.columns for col in required_cols)
                has_data = len(df) > 0
                no_null = df[required_cols].notna().all().all() if has_data else False

                quality_score = sum([has_all_cols, has_data, no_null]) / 3 * 100
                data_quality.append(quality_score)

                console.print(f"  轮次 {i+1}: ✓ {elapsed:.2f}s, 数据行数: {len(df)}")

            except Exception as e:
                console.print(f"  轮次 {i+1}: ✗ 失败 - {str(e)[:50]}")
                time.sleep(1)

        return {
            'name': 'fund_portfolio_hold_em',
            'description': 'ETF持仓成分',
            'success_rate': successes / self.test_rounds * 100,
            'avg_time': sum(times) / len(times) if times else None,
            'min_time': min(times) if times else None,
            'max_time': max(times) if times else None,
            'avg_quality': sum(data_quality) / len(data_quality) if data_quality else 0,
            'successes': successes
        }

    def test_etf_fund_info_em(self) -> Dict:
        """测试净值数据源"""
        console.print("\n[cyan]测试 fund_etf_fund_info_em (净值数据)...[/cyan]")

        times = []
        successes = 0
        data_quality = []
        test_code = "510300"

        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")

        for i in range(self.test_rounds):
            try:
                start = time.time()
                df = ak.fund_etf_fund_info_em(
                    fund=test_code,
                    start_date=start_date,
                    end_date=end_date
                )
                elapsed = time.time() - start

                times.append(elapsed)
                successes += 1

                # 检查数据完整性
                required_cols = ['净值日期', '单位净值', '累计净值']
                has_all_cols = all(col in df.columns for col in required_cols)
                has_data = len(df) > 0
                no_null = df[required_cols].notna().all().all() if has_data else False

                quality_score = sum([has_all_cols, has_data, no_null]) / 3 * 100
                data_quality.append(quality_score)

                console.print(f"  轮次 {i+1}: ✓ {elapsed:.2f}s, 数据行数: {len(df)}")

            except Exception as e:
                console.print(f"  轮次 {i+1}: ✗ 失败 - {str(e)[:50]}")
                time.sleep(1)

        return {
            'name': 'fund_etf_fund_info_em',
            'description': 'ETF净值数据',
            'success_rate': successes / self.test_rounds * 100,
            'avg_time': sum(times) / len(times) if times else None,
            'min_time': min(times) if times else None,
            'max_time': max(times) if times else None,
            'avg_quality': sum(data_quality) / len(data_quality) if data_quality else 0,
            'successes': successes
        }

    def run_all_tests(self):
        """运行所有测试"""
        console.print("\n[bold yellow]开始数据源性能基准测试...[/bold yellow]")
        console.print(f"测试轮次: {self.test_rounds}\n")

        # 测试所有数据源
        self.results['etf_spot_em'] = self.test_etf_spot_em()
        time.sleep(2)  # 避免请求过快

        self.results['etf_spot_ths'] = self.test_etf_spot_ths()
        time.sleep(2)

        self.results['etf_hist_em'] = self.test_etf_hist_em()
        time.sleep(2)

        self.results['portfolio_hold_em'] = self.test_portfolio_hold_em()
        time.sleep(2)

        self.results['etf_fund_info_em'] = self.test_etf_fund_info_em()

        # 显示汇总结果
        self.display_summary()

        # 生成建议
        self.generate_recommendations()

    def display_summary(self):
        """显示测试结果汇总"""
        console.print("\n[bold green]测试结果汇总[/bold green]\n")

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("数据源", style="cyan")
        table.add_column("描述")
        table.add_column("成功率", justify="right")
        table.add_column("平均耗时", justify="right")
        table.add_column("最快", justify="right")
        table.add_column("最慢", justify="right")
        table.add_column("数据质量", justify="right")
        table.add_column("评级", justify="center")

        for key, result in self.results.items():
            # 计算综合评级
            if result['success_rate'] >= 80 and result['avg_time'] and result['avg_time'] < 3:
                rating = "[green]⭐⭐⭐⭐⭐[/green]"
            elif result['success_rate'] >= 60 and result['avg_time'] and result['avg_time'] < 5:
                rating = "[yellow]⭐⭐⭐⭐[/yellow]"
            elif result['success_rate'] >= 40:
                rating = "[yellow]⭐⭐⭐[/yellow]"
            elif result['success_rate'] >= 20:
                rating = "[red]⭐⭐[/red]"
            else:
                rating = "[red]⭐[/red]"

            # 成功率颜色
            if result['success_rate'] >= 80:
                success_color = "green"
            elif result['success_rate'] >= 50:
                success_color = "yellow"
            else:
                success_color = "red"

            table.add_row(
                result['name'],
                result['description'],
                f"[{success_color}]{result['success_rate']:.0f}%[/{success_color}]",
                f"{result['avg_time']:.2f}s" if result['avg_time'] else "N/A",
                f"{result['min_time']:.2f}s" if result['min_time'] else "N/A",
                f"{result['max_time']:.2f}s" if result['max_time'] else "N/A",
                f"{result['avg_quality']:.0f}%",
                rating
            )

        console.print(table)

    def generate_recommendations(self):
        """生成数据源使用建议"""
        console.print("\n[bold blue]数据源使用建议[/bold blue]\n")

        # 找出最佳实时行情数据源
        spot_sources = {
            'etf_spot_em': self.results.get('etf_spot_em'),
            'etf_spot_ths': self.results.get('etf_spot_ths')
        }

        best_spot = max(
            spot_sources.items(),
            key=lambda x: (x[1]['success_rate'], -x[1]['avg_time'] if x[1]['avg_time'] else 999)
        )

        console.print(f"1. [green]实时行情数据源推荐[/green]:")
        console.print(f"   首选: {best_spot[1]['name']} (成功率: {best_spot[1]['success_rate']:.0f}%)")

        # 备用方案
        backup_spot = [k for k in spot_sources.keys() if k != best_spot[0]][0]
        console.print(f"   备用: {self.results[backup_spot]['name']} (成功率: {self.results[backup_spot]['success_rate']:.0f}%)")

        # 历史数据
        hist_result = self.results.get('etf_hist_em')
        console.print(f"\n2. [green]历史数据源[/green]:")
        console.print(f"   {hist_result['name']} - 成功率: {hist_result['success_rate']:.0f}%, 平均耗时: {hist_result['avg_time']:.2f}s")
        if hist_result['success_rate'] >= 80:
            console.print(f"   [green]✓ 推荐使用，稳定可靠[/green]")

        # 持仓数据
        holding_result = self.results.get('portfolio_hold_em')
        console.print(f"\n3. [green]持仓数据源[/green]:")
        console.print(f"   {holding_result['name']} - 成功率: {holding_result['success_rate']:.0f}%, 平均耗时: {holding_result['avg_time']:.2f}s" if holding_result['avg_time'] else f"   {holding_result['name']} - 成功率: {holding_result['success_rate']:.0f}%")

        # 净值数据
        nav_result = self.results.get('etf_fund_info_em')
        console.print(f"\n4. [green]净值数据源[/green]:")
        console.print(f"   {nav_result['name']} - 成功率: {nav_result['success_rate']:.0f}%, 平均耗时: {nav_result['avg_time']:.2f}s" if nav_result['avg_time'] else f"   {nav_result['name']} - 成功率: {nav_result['success_rate']:.0f}%")

        # 优化建议
        console.print("\n[bold yellow]优化建议[/bold yellow]:")
        console.print("1. 实时行情使用主备切换策略")
        console.print("2. 历史数据和净值数据相对稳定,可适当延长缓存时间")
        console.print("3. 持仓数据按需获取,建议添加本地缓存")
        console.print("4. 所有数据源都应配置重试机制")


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='数据源性能基准测试')
    parser.add_argument('--rounds', '-r', type=int, default=5, help='测试轮次')
    args = parser.parse_args()

    benchmark = DataSourceBenchmark(test_rounds=args.rounds)
    benchmark.run_all_tests()

    console.print("\n[green]测试完成![/green]")


if __name__ == '__main__':
    main()
