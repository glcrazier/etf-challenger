"""统一决策引擎

编排4层分析并生成 UnifiedAnalysis 结果。
债券ETF自动路由到 BondAdvisor。
"""

from datetime import datetime, timedelta

from ..models.decision import UnifiedAnalysis
from ..analysis.analyzer import ETFAnalyzer
from ..analysis.regime import RegimeDetector
from ..analysis.fund_evaluator import FundEvaluator
from ..analysis.timing import TimingAnalyzer
from ..analysis.portfolio_advisor import PortfolioAdvisor
from ..analysis.narrative import NarrativeReporter
from ..analysis.advisor import TradingAdvisor, TradingSignal, SignalType


class DecisionEngine:
    """统一决策引擎"""

    def __init__(self, data_service, portfolio_path=None):
        self.data_service = data_service
        self.regime_detector = RegimeDetector(data_service)
        self.fund_evaluator = FundEvaluator(data_service)
        self.timing_analyzer = TimingAnalyzer()
        self.portfolio_advisor = PortfolioAdvisor(data_service, portfolio_path)
        self.narrative_reporter = NarrativeReporter()
        self.analyzer = ETFAnalyzer()

    def analyze(self, code: str, days: int = 60) -> UnifiedAnalysis:
        """
        执行完整的4层分析

        Args:
            code: ETF代码
            days: 历史数据天数

        Returns:
            UnifiedAnalysis 统一分析结果
        """
        # 获取ETF名称
        etf_name = self._get_etf_name(code)

        # 获取ETF历史数据
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")
        df = self.data_service.get_historical_data(code, start_date, end_date)

        if df is None or df.empty:
            raise Exception(f"ETF {code} 历史数据为空")

        # 计算技术指标
        df = self.analyzer.calculate_returns(df)
        df = self.analyzer.calculate_moving_averages(df, windows=[5, 10, 20, 60])
        df = self.analyzer.calculate_rsi(df)
        df = self.analyzer.calculate_macd(df)
        df = self.analyzer.calculate_bollinger_bands(df)
        df = self.analyzer.calculate_volatility(df, window=20)

        # 获取溢价率
        premium_rate = None
        premium_history = None
        try:
            premium_list = self.data_service.calculate_premium_discount(code, 30)
            if premium_list:
                premium_rate = premium_list[-1].premium_rate
                premium_history = premium_list
        except Exception:
            pass

        # Layer 1: 市场状态
        regime = self.regime_detector.detect()

        # Layer 2: 基金评级
        fund_grade = self.fund_evaluator.evaluate(code, df, days)

        # Layer 3: 时机分析
        timing = self.timing_analyzer.analyze(df, regime, premium_rate, premium_history)

        # Layer 4: 持仓建议（可选）
        portfolio = None
        if self.portfolio_advisor.available:
            try:
                portfolio = self.portfolio_advisor.advise(code, df)
            except Exception:
                pass

        # 综合结论
        conclusion, risks = self.narrative_reporter.generate_conclusion(
            regime, fund_grade, timing, portfolio
        )

        return UnifiedAnalysis(
            code=code,
            name=etf_name,
            regime=regime,
            fund_grade=fund_grade,
            timing=timing,
            portfolio=portfolio,
            conclusion=conclusion,
            risks=risks,
        )

    def is_bond_etf(self, code: str) -> bool:
        """判断是否为债券ETF"""
        name = self._get_etf_name(code)
        return "债" in name

    def to_legacy_signal(self, result: UnifiedAnalysis) -> TradingSignal:
        """
        将 UnifiedAnalysis 转换为向后兼容的 TradingSignal

        供 report 等需要旧格式的地方使用。
        """
        timing = result.timing

        # 映射 action → SignalType
        score = timing.composite_score
        if score >= 0.6:
            signal_type = SignalType.STRONG_BUY
        elif score >= 0.2:
            signal_type = SignalType.BUY
        elif score <= -0.6:
            signal_type = SignalType.STRONG_SELL
        elif score <= -0.2:
            signal_type = SignalType.SELL
        else:
            signal_type = SignalType.HOLD

        # 指标状态
        indicators = {}
        for ch in timing.channels:
            if ch.score > 0.1:
                indicators[ch.name] = "看涨"
            elif ch.score < -0.1:
                indicators[ch.name] = "看跌"
            else:
                indicators[ch.name] = "中性"

        # 风险等级
        if result.regime.volatility_20d > 30:
            risk_level = "高"
        elif result.regime.volatility_20d > 20:
            risk_level = "中"
        else:
            risk_level = "低"

        # 原因
        reasons = []
        reasons.append(f"• {result.regime.narrative}")
        reasons.append(f"• 基金评级{result.fund_grade.grade.value}（{result.fund_grade.total_score:.0f}分）")
        for ch in timing.channels:
            reasons.append(f"• {ch.detail}")

        # 价格
        entry_price = None
        price_target = None
        stop_loss = None
        if result.portfolio and result.portfolio.tranches:
            entry_price = result.portfolio.tranches[0].price

        return TradingSignal(
            signal_type=signal_type,
            confidence=timing.confidence,
            reasons=reasons,
            indicators=indicators,
            risk_level=risk_level,
            entry_price=entry_price,
            price_target=price_target,
            stop_loss=stop_loss,
        )

    def _get_etf_name(self, code: str) -> str:
        """获取ETF名称"""
        try:
            quote = self.data_service.get_realtime_quote(code)
            if quote:
                return quote.name
        except Exception:
            pass
        return "未知"
