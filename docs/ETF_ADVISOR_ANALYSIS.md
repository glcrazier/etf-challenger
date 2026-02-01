# ETF交易建议系统核心算法分析

> 本文档详细解析 etf-challenger 项目中的智能交易建议系统的实现原理和算法逻辑

## 📋 目录

- [系统概述](#系统概述)
- [核心技术指标](#核心技术指标)
- [评分机制](#评分机制)
- [信号生成](#信号生成)
- [风险管理](#风险管理)
- [使用示例](#使用示例)
- [算法优化建议](#算法优化建议)

---

## 系统概述

### 架构设计

**核心类**：`TradingAdvisor` (src/etf_challenger/analysis/advisor.py)

**设计思路**：
- 多指标综合评分系统
- 加权平均法整合不同信号
- 量化评估生成交易建议
- 动态计算目标价位和止损位

### 数据流

```
历史价格数据 (DataFrame)
    ↓
技术指标计算 (ETFAnalyzer)
    ↓
多维度信号分析 (TradingAdvisor)
    ↓
加权综合评分 (-100 ~ +100)
    ↓
交易信号生成 (强烈买入/买入/持有/卖出/强烈卖出)
    ↓
风险评估 + 价格目标
```

---

## 核心技术指标

### 1. 均线交叉 (MA Cross) - 权重 20%

**计算方法**：
- 短期均线：MA5 (5日移动平均)
- 长期均线：MA20 (20日移动平均)

**信号判断**：

| 条件 | 信号 | 评分 |
|------|------|------|
| MA5上穿MA20（金叉） | 强烈看涨 | +1.0 |
| MA5下穿MA20（死叉） | 强烈看跌 | -1.0 |
| MA5 > MA20（多头排列） | 看涨 | +0.5 |
| MA5 < MA20（空头排列） | 看跌 | -0.5 |

**代码位置**：`advisor.py:133-159`

**算法逻辑**：
```python
# 金叉检测
if ma5_prev <= ma20_prev and ma5 > ma20:
    return BULLISH, 1.0

# 死叉检测
if ma5_prev >= ma20_prev and ma5 < ma20:
    return BEARISH, -1.0
```

---

### 2. RSI (相对强弱指标) - 权重 15%

**计算公式**：
```
RSI = 100 - (100 / (1 + RS))
RS = 平均涨幅 / 平均跌幅 (14日周期)
```

**信号阈值**：

| RSI区间 | 判断 | 信号 | 评分 |
|---------|------|------|------|
| < 20 | 严重超卖 | 强烈买入 | +1.0 |
| 20-30 | 超卖 | 买入 | +0.8 |
| 30-40 | 偏弱 | 偏多 | +0.3 |
| 40-60 | 中性 | 观望 | 0 |
| 60-70 | 偏强 | 偏空 | -0.3 |
| 70-80 | 超买 | 卖出 | -0.8 |
| > 80 | 严重超买 | 强烈卖出 | -1.0 |

**代码位置**：`advisor.py:161-199`, `analyzer.py:82-111`

**交易含义**：
- RSI < 30：市场超卖，可能反弹
- RSI > 70：市场超买，可能回调

---

### 3. MACD (指数平滑异同移动平均线) - 权重 20%

**计算公式**：
```
MACD线 = EMA(12) - EMA(26)
信号线 = EMA(MACD, 9)
柱状图 = MACD - 信号线
```

**信号判断**：

| 条件 | 信号 | 评分 |
|------|------|------|
| MACD上穿信号线（金叉） | 强烈看涨 | +1.0 |
| MACD下穿信号线（死叉） | 强烈看跌 | -1.0 |
| MACD > 0 且柱状图 > 0 | 看涨 | +0.6 |
| MACD < 0 且柱状图 < 0 | 看跌 | -0.6 |

**代码位置**：`advisor.py:201-229`, `analyzer.py:113-149`

**核心逻辑**：
```python
# 金叉：动能转强
if macd_prev <= signal_prev and macd > signal:
    return BULLISH, 1.0

# 零轴位置判断趋势强度
if macd > 0 and histogram > 0:
    return BULLISH, 0.6
```

---

### 4. 布林带 (Bollinger Bands) - 权重 15%

**计算公式**：
```
中轨 = MA(20)
上轨 = 中轨 + 2 × σ
下轨 = 中轨 - 2 × σ
```

**信号判断**：

| 价格位置 | 判断 | 信号 | 评分 |
|----------|------|------|------|
| ≤ 下轨 | 超卖 | 买入 | +0.8 |
| 下轨～中轨 | 偏弱 | 偏多 | +0.3 |
| ≥ 上轨 | 超买 | 卖出 | -0.8 |
| 中轨～上轨 | 偏强 | 偏空 | -0.3 |

**代码位置**：`advisor.py:231-257`, `analyzer.py:151-182`

**统计意义**：
- 价格在2个标准差外的概率约5%
- 触及边界意味着极端状态，可能反转

---

### 5. 趋势分析 (Trend) - 权重 15%

**计算方法**：
- 线性回归斜率（最近20天）
- 涨跌幅百分比

**信号阈值**：

| 条件 | 信号 | 评分 |
|------|------|------|
| 斜率 > 0 且涨幅 > 5% | 强上升 | +0.8 |
| 斜率 > 0 且涨幅 > 0 | 上升 | +0.5 |
| 斜率 < 0 且跌幅 > 5% | 强下降 | -0.8 |
| 斜率 < 0 且跌幅 > 0 | 下降 | -0.5 |

**代码位置**：`advisor.py:259-289`

**算法实现**：
```python
# 使用numpy多项式拟合
slope = np.polyfit(x, prices, 1)[0]
price_change_pct = (prices[-1] - prices[0]) / prices[0] * 100
```

---

### 6. 成交量分析 (Volume) - 权重 10%

**计算方法**：
- 近5日平均成交量 vs 全周期平均成交量
- 量价配合关系

**信号判断**：

| 条件 | 信号 | 评分 |
|------|------|------|
| 放量（>1.5倍）且上涨 | 看涨 | +0.7 |
| 放量（>1.5倍）且下跌 | 看跌 | -0.7 |
| 缩量（<0.7倍）且上涨 | 中性 | +0.2 |

**代码位置**：`advisor.py:291-318`

**量价理论**：
- 放量上涨：买盘强劲，趋势可靠
- 放量下跌：卖压沉重，趋势可靠
- 缩量上涨：缺乏动能，可能乏力

---

### 7. 溢价率 (Premium/Discount) - 权重 5%

**计算公式**：
```
溢价率 = (市场价格 - 净值) / 净值 × 100%
```

**信号阈值**：

| 溢价率 | 判断 | 信号 | 评分 |
|--------|------|------|------|
| < -3% | 高折价（低估） | 买入 | +0.8 |
| -3% ~ -1% | 折价 | 偏多 | +0.5 |
| -1% ~ +1% | 正常 | 中性 | 0 |
| +1% ~ +3% | 溢价 | 偏空 | -0.5 |
| > +3% | 高溢价（高估） | 卖出 | -0.8 |

**代码位置**：`advisor.py:320-339`

**ETF特性**：
- 折价：市场价 < 净值，可能套利机会
- 溢价：市场价 > 净值，可能存在泡沫

---

## 评分机制

### 加权综合评分公式

```
总得分 = Σ(指标得分 × 指标权重) / 总权重

最终得分范围：-100 ~ +100
```

### 权重配置

```python
weights = {
    'ma_cross': 20,    # 均线交叉
    'rsi': 15,         # RSI
    'macd': 20,        # MACD
    'bollinger': 15,   # 布林带
    'trend': 15,       # 趋势
    'volume': 10,      # 成交量
    'premium': 5,      # 溢价率
}
```

### 权重设计思路

**趋势类指标（55%）**：
- 均线交叉（20%）+ MACD（20%）+ 趋势（15%）
- 捕捉中长期趋势变化

**超买超卖指标（30%）**：
- RSI（15%）+ 布林带（15%）
- 识别短期极端状态

**辅助指标（15%）**：
- 成交量（10%）+ 溢价率（5%）
- 验证信号可靠性

---

## 信号生成

### 得分转换规则

```python
def _get_signal_type(score: float):
    if score >= 0.6:
        return STRONG_BUY, confidence=min(score*100, 95)
    elif score >= 0.2:
        return BUY, confidence=min(score*100, 80)
    elif score <= -0.6:
        return STRONG_SELL, confidence=min(score*100, 95)
    elif score <= -0.2:
        return SELL, confidence=min(score*100, 80)
    else:
        return HOLD, confidence=50
```

### 五级信号体系

| 得分区间 | 信号类型 | 置信度上限 | 操作建议 |
|----------|----------|-----------|---------|
| ≥ 0.6 | 强烈买入 | 95% | 积极建仓/加仓 |
| 0.2 ~ 0.6 | 买入 | 80% | 适量买入 |
| -0.2 ~ 0.2 | 持有 | 50% | 观望等待 |
| -0.6 ~ -0.2 | 卖出 | 80% | 适量减仓 |
| ≤ -0.6 | 强烈卖出 | 95% | 积极减仓/清仓 |

### 建议原因生成

**示例输出**：
```
强烈买入 (置信度: 85%)

原因：
✓ 短期均线金叉，买入信号
✓ RSI=25.3，处于超卖区域
✓ MACD金叉，动能转强
✓ 近期上涨8.5%，强势上升趋势
✓ 折价2.5%，价格可能被低估
```

**代码位置**：`advisor.py:356-417`

---

## 风险管理

### 1. 风险等级评估

**基于年化波动率**：

```python
volatility = returns.std() × sqrt(252) × 100

if volatility > 30%:
    risk_level = "高"
elif volatility > 20%:
    risk_level = "中"
else:
    risk_level = "低"
```

**代码位置**：`advisor.py:419-434`

### 2. 动态止盈止损

**使用ATR（平均真实波幅）**：

```python
# 计算14日ATR
TR = max(High - Low, abs(High - Close_prev), abs(Low - Close_prev))
ATR = mean(TR, 14)

# 买入建议
目标价 = 当前价 + 2 × ATR
止损价 = 当前价 - ATR

# 卖出建议
目标价 = 当前价 - 2 × ATR
止损价 = 当前价 + ATR
```

**风险回报比**：2:1

**代码位置**：`advisor.py:436-467`

### 3. 完整交易信号结构

```python
@dataclass
class TradingSignal:
    signal_type: SignalType         # 信号类型
    confidence: float               # 置信度 (0-100)
    reasons: List[str]              # 建议原因
    indicators: Dict[str, str]      # 各指标状态
    risk_level: str                 # 风险等级
    price_target: Optional[float]   # 目标价位
    stop_loss: Optional[float]      # 止损价位
```

---

## 使用示例

### 命令行使用

```bash
# 基础交易建议
etf suggest 510300

# 指定分析周期
etf suggest 515880 --days 90

# 生成完整报告（包含建议）
etf report 510300 --format html
```

### 编程调用

```python
from etf_challenger.data.service import ETFDataService
from etf_challenger.analysis.analyzer import ETFAnalyzer
from etf_challenger.analysis.advisor import TradingAdvisor

# 1. 获取历史数据
service = ETFDataService()
df = service.get_historical_data("510300", days=90)

# 2. 计算技术指标
analyzer = ETFAnalyzer()
df = analyzer.calculate_moving_averages(df)
df = analyzer.calculate_rsi(df)
df = analyzer.calculate_macd(df)
df = analyzer.calculate_bollinger_bands(df)

# 3. 获取溢价率
quote = service.get_realtime_quote("510300")
premium_rate = quote.premium_rate

# 4. 生成交易建议
advisor = TradingAdvisor()
signal = advisor.analyze(df, premium_rate)

# 5. 输出结果
print(f"信号: {signal.signal_type.value}")
print(f"置信度: {signal.confidence:.1f}%")
print(f"风险等级: {signal.risk_level}")
print(f"目标价: {signal.price_target}")
print(f"止损价: {signal.stop_loss}")
for reason in signal.reasons:
    print(reason)
```

---

## 算法优化建议

### 当前系统的优势

1. **多维度综合**：7大指标覆盖趋势、动量、波动、量能
2. **权重平衡**：趋势类55% + 震荡类30% + 辅助15%
3. **动态风险管理**：ATR自适应止盈止损
4. **清晰可解释**：每个建议都有具体原因

### 潜在改进方向

#### 1. 自适应权重调整

**问题**：固定权重在不同市场环境下可能不适用

**改进方案**：
```python
# 震荡市：提高RSI和布林带权重
# 趋势市：提高均线和MACD权重
# 高波动：提高成交量权重
```

#### 2. 市场环境识别

**新增指标**：
- ADX (平均趋向指数)：判断趋势强度
- VIX (波动率指数)：衡量市场恐慌程度

**应用**：
```python
if ADX > 25:  # 强趋势市
    weights['ma_cross'] += 5
    weights['trend'] += 5
else:  # 震荡市
    weights['rsi'] += 5
    weights['bollinger'] += 5
```

#### 3. 机器学习增强

**传统方法 → ML方法**：
- 固定权重 → 特征重要性（随机森林）
- 线性评分 → 非线性模型（XGBoost）
- 规则阈值 → 数据驱动阈值

**保留优势**：
- 保持可解释性
- 技术指标作为特征输入
- 历史回测验证

#### 4. 回测验证框架

**必要性**：当前缺少历史表现验证

**建议实现**：
```python
class BacktestEngine:
    def run(self, symbol, start_date, end_date):
        # 1. 获取历史数据
        # 2. 逐日生成信号
        # 3. 模拟交易
        # 4. 计算收益率、胜率、最大回撤
        # 5. 对比基准（买入持有策略）
        pass
```

#### 5. 行业/板块轮动

**ETF特性**：跟踪特定板块/主题

**新增维度**：
- 行业景气度
- 板块资金流向
- 相对强弱（vs 大盘）

#### 6. 情绪指标

**数据源**：
- 换手率（流动性）
- 北向资金流入（外资情绪）
- 融资融券余额（杠杆情绪）

---

## 技术指标速查表

| 指标 | 周期 | 买入信号 | 卖出信号 | 权重 |
|------|------|---------|---------|------|
| MA Cross | 5/20日 | 金叉 | 死叉 | 20% |
| RSI | 14日 | <30 | >70 | 15% |
| MACD | 12/26/9 | 金叉 | 死叉 | 20% |
| Bollinger | 20日/2σ | 触下轨 | 触上轨 | 15% |
| Trend | 20日 | 涨幅>5% | 跌幅>5% | 15% |
| Volume | 5日均 | 放量涨 | 放量跌 | 10% |
| Premium | 实时 | 折价>3% | 溢价>3% | 5% |

---

## 关键文件索引

| 文件路径 | 核心功能 | 关键方法 |
|---------|---------|---------|
| `analysis/advisor.py` | 交易建议引擎 | `analyze()`, `_analyze_*()` |
| `analysis/analyzer.py` | 技术指标计算 | `calculate_*()` |
| `analysis/report.py` | 报告生成 | `generate()` |
| `cli/main.py` | CLI命令 | `suggest`, `report` |
| `data/service.py` | 数据获取 | `get_historical_data()` |

---

## 参考资料

### 技术分析经典理论

1. **道氏理论** - 趋势分析基础
2. **江恩理论** - 时间周期和价格关系
3. **波浪理论** - 市场心理和波动模式
4. **量价理论** - 成交量与价格配合

### 推荐阅读

- 《技术分析实战》- 约翰·墨菲
- 《股市趋势技术分析》- 罗伯特·爱德华
- 《Python金融大数据分析》- Yves Hilpisch

### 在线资源

- [Investopedia - Technical Indicators](https://www.investopedia.com/terms/t/technicalindicator.asp)
- [TA-Lib 技术分析库](https://ta-lib.org/)
- [Backtrader 回测框架](https://www.backtrader.com/)

---

## 版本历史

- **v1.0** (当前版本) - 7指标综合评分系统
- 未来计划：机器学习增强、回测验证、实时监控

---

**文档生成时间**：2026-02-01
**项目仓库**：etf-challenger
**维护者**：参考 CLAUDE.md
