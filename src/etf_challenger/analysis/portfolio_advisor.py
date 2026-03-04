"""持仓顾问（Layer 4）

读取 portfolio.json 计算相关性、建议仓位和分批买入策略。
如果 portfolio.json 不存在则跳过该层。
"""

import json
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Optional

from ..models.decision import PositionAdvice, TrancheEntry


class PortfolioAdvisor:
    """持仓顾问"""

    DEFAULT_CONFIG = {
        "max_single_position_pct": 20,   # 单只ETF最大仓位%
        "max_correlation": 0.8,          # 相关性警告阈值
        "prefer_scale_in": True,         # 是否分批建仓
        "scale_in_tranches": 3,          # 分批次数
    }

    def __init__(self, data_service, portfolio_path: Optional[str] = None):
        self.data_service = data_service
        self.portfolio_path = portfolio_path or str(
            Path(__file__).resolve().parents[3] / "portfolio.json"
        )
        self._portfolio = self._load_portfolio()

    def _load_portfolio(self) -> Optional[dict]:
        """加载用户持仓"""
        path = Path(self.portfolio_path)
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return None

    @property
    def available(self) -> bool:
        """portfolio.json 是否存在且有效"""
        return self._portfolio is not None and "holdings" in self._portfolio

    def advise(self, code: str, etf_df: pd.DataFrame) -> Optional[PositionAdvice]:
        """
        生成持仓建议

        Args:
            code: 目标ETF代码
            etf_df: 目标ETF历史数据

        Returns:
            PositionAdvice 或 None（如果 portfolio.json 不存在）
        """
        if not self.available:
            return None

        config = {**self.DEFAULT_CONFIG}
        config.update(self._portfolio.get("config", {}))
        holdings = self._portfolio.get("holdings", [])

        if not holdings:
            return self._no_holdings_advice(code, etf_df, config)

        # 计算与各持仓的相关性
        max_corr = 0.0
        corr_name = ""
        warnings = []

        etf_returns = etf_df['收盘'].pct_change().dropna()

        for holding in holdings:
            h_code = holding.get("code", "")
            h_name = holding.get("name", h_code)

            try:
                h_df = self.data_service.get_historical_data(h_code)
                if h_df is None or h_df.empty:
                    continue

                h_returns = h_df['收盘'].pct_change().dropna()

                # 对齐
                common = etf_returns.index.intersection(h_returns.index)
                if len(common) < 15:
                    # 用位置索引对齐（日期列可能不同）
                    min_len = min(len(etf_returns), len(h_returns), 30)
                    a = etf_returns.tail(min_len).values
                    b = h_returns.tail(min_len).values
                    if len(a) >= 15:
                        corr = np.corrcoef(a, b)[0, 1]
                    else:
                        continue
                else:
                    corr = etf_returns.loc[common].corr(h_returns.loc[common])

                if not np.isnan(corr) and abs(corr) > abs(max_corr):
                    max_corr = corr
                    corr_name = h_name

            except Exception:
                continue

        if abs(max_corr) > config["max_correlation"]:
            warnings.append(
                f"与现有持仓「{corr_name}」相关性{max_corr:.2f}，超过阈值{config['max_correlation']}，注意分散风险"
            )

        # 仓位建议：与波动率反比，上限 max_single_position_pct
        returns = etf_df['收盘'].pct_change().dropna()
        vol = returns.std() * np.sqrt(252) if len(returns) > 5 else 0.2
        # 基准波动率15%对应基准仓位15%
        base_vol = 0.15
        if vol > 0:
            raw_pct = (base_vol / vol) * 15
        else:
            raw_pct = 15
        suggested_pct = min(raw_pct, config["max_single_position_pct"])
        suggested_pct = max(5, suggested_pct)  # 下限5%

        # 分批建仓
        tranches = []
        if config.get("prefer_scale_in", True):
            n = config.get("scale_in_tranches", 3)
            current_price = etf_df['收盘'].iloc[-1]

            # ATR
            atr = self._calc_atr(etf_df)

            for i in range(n):
                entry_price = current_price - i * 0.5 * atr
                pct = suggested_pct / n
                tranches.append(TrancheEntry(
                    tranche_no=i + 1,
                    price=round(entry_price, 3),
                    pct_of_position=round(pct, 1),
                ))
        else:
            tranches.append(TrancheEntry(
                tranche_no=1,
                price=round(etf_df['收盘'].iloc[-1], 3),
                pct_of_position=round(suggested_pct, 1),
            ))

        narrative = self._build_narrative(
            max_corr, corr_name, suggested_pct, tranches, warnings, config
        )

        return PositionAdvice(
            suggested_pct=round(suggested_pct, 1),
            max_correlation=round(max_corr, 2),
            correlated_holding=corr_name,
            tranches=tranches,
            warnings=warnings,
            narrative=narrative,
        )

    def _no_holdings_advice(self, code, etf_df, config) -> PositionAdvice:
        """无持仓时的建议"""
        suggested_pct = min(15, config["max_single_position_pct"])
        current_price = etf_df['收盘'].iloc[-1]
        atr = self._calc_atr(etf_df)
        n = config.get("scale_in_tranches", 3)

        tranches = []
        for i in range(n):
            tranches.append(TrancheEntry(
                tranche_no=i + 1,
                price=round(current_price - i * 0.5 * atr, 3),
                pct_of_position=round(suggested_pct / n, 1),
            ))

        return PositionAdvice(
            suggested_pct=round(suggested_pct, 1),
            max_correlation=0,
            correlated_holding="",
            tranches=tranches,
            warnings=[],
            narrative=f"当前无持仓，建议配置{suggested_pct:.0f}%仓位，分{n}批买入。",
        )

    @staticmethod
    def _calc_atr(df: pd.DataFrame, period: int = 14) -> float:
        """计算ATR"""
        if len(df) < period:
            return df['收盘'].iloc[-1] * 0.02  # 回退：2%

        high = df['最高'].tail(period)
        low = df['最低'].tail(period)
        close = df['收盘'].tail(period)

        tr = np.maximum(high.values - low.values,
                        np.abs(high.values - np.roll(close.values, 1)))
        tr = np.maximum(tr, np.abs(low.values - np.roll(close.values, 1)))
        tr[0] = high.values[0] - low.values[0]  # 第一个用当日高低
        return float(np.mean(tr))

    @staticmethod
    def _build_narrative(max_corr, corr_name, suggested_pct, tranches, warnings, config):
        parts = []

        if corr_name:
            corr_status = "可接受" if abs(max_corr) <= config["max_correlation"] else "偏高"
            parts.append(f"与现有持仓「{corr_name}」相关性{max_corr:.2f}（{corr_status}）")

        parts.append(f"建议配置{suggested_pct:.0f}%仓位")

        if len(tranches) > 1:
            prices = "、".join([f"{t.price:.3f}" for t in tranches])
            parts.append(f"分{len(tranches)}批买入（{prices}）")

        for w in warnings:
            parts.append(w)

        return "，".join(parts) + "。"
