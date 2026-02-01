# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**etf-challenger** - A股场内ETF基金分析工具，提供实时行情监控、溢价/折价分析、历史数据分析、持仓成分分析和智能交易建议功能。

技术栈：
- Python 3.9+
- akshare（A股数据获取）
- pandas/numpy（数据处理和分析）
- click（CLI框架）
- rich（命令行美化）

## Development Setup

### 环境配置

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# macOS/Linux:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# 安装依赖
pip install -e .

# 或者使用requirements.txt
pip install -r requirements.txt
```

### 开发工具安装

```bash
# 安装开发依赖
pip install -e ".[dev]"
```

## 常用命令

### 运行应用

```bash
# 列出所有ETF
etf list

# 搜索ETF
etf list 沪深300

# 查看实时行情
etf quote 510300

# 获取交易建议（综合技术分析）⭐
etf suggest 510300
etf suggest 515880 --days 90

# 生成综合分析报告 📄
etf report 510300
etf report 510300 --format html --output report.html

# 溢价/折价分析
etf premium 510300 --days 30

# 历史表现分析
etf analyze 510300 --days 90

# 查看持仓成分
etf holdings 510300 --year 2024

# 筛选优质ETF（按流动性和费率）⭐
etf screen                              # 使用默认参数(去重)
etf screen --no-dedup                   # 关闭指数去重
etf screen --top 20 --min-scale 10      # 返回前20支,最小规模10亿
etf screen --with-volume                # 包含成交量分析
```

### 测试

```bash
# 运行测试
pytest

# 测试覆盖率
pytest --cov=src/etf_challenger --cov-report=html
```

### 代码质量

```bash
# 代码格式化
black src/ tests/

# 代码检查
ruff check src/ tests/

# 类型检查
mypy src/
```

## 项目架构

### 目录结构

```
src/etf_challenger/
├── cli/           # 命令行界面
│   └── main.py    # CLI主程序，定义所有命令（list, quote, suggest, analyze等）
├── data/          # 数据获取和处理
│   └── service.py # ETF数据服务，封装akshare API
├── analysis/      # 分析功能
│   ├── analyzer.py # ETF分析器，技术指标和表现分析
│   ├── advisor.py  # 交易建议引擎，综合多指标生成买卖建议
│   └── report.py   # 报告生成器，导出Markdown/HTML/JSON报告
├── models/        # 数据模型
│   └── etf.py     # ETF相关数据类（Quote、Info、NetValue等）
└── utils/         # 工具函数
    ├── helpers.py # 辅助函数（格式化、验证等）
    └── retry.py   # 重试装饰器
```

### 核心模块说明

**data/service.py** - ETFDataService类
- 封装akshare API调用
- 提供ETF列表、实时行情、历史数据、持仓成分、净值等数据获取
- 计算溢价/折价率
- 实现数据缓存机制

**analysis/analyzer.py** - ETFAnalyzer类
- 计算技术指标：MA、RSI、MACD、布林带等
- 分析收益率、波动率、最大回撤
- 计算夏普比率
- 持仓结构分析

**models/etf.py** - 数据模型
- ETFQuote: 实时行情
- ETFInfo: 基本信息
- ETFNetValue: 净值数据
- ETFHolding: 持仓成分
- ETFPremiumDiscount: 溢价/折价

**analysis/report.py** - ReportGenerator类
- 生成综合分析报告
- 支持Markdown、HTML、JSON三种格式
- 整合行情、技术指标、交易建议、持仓等所有数据
- 自动格式化和美化输出

**cli/main.py** - CLI命令
- `list`: 列出/搜索ETF
- `quote`: 实时行情
- `suggest`: 智能交易建议 ⭐
- `report`: 生成分析报告 📄
- `premium`: 溢价/折价分析
- `analyze`: 历史表现分析
- `holdings`: 持仓成分

### 数据源

使用akshare库获取A股ETF数据：
- `fund_etf_spot_em()`: 实时行情
- `fund_etf_hist_em()`: 历史K线
- `fund_etf_hold_em()`: 持仓成分
- `fund_etf_hist_sina()`: 净值数据

## 开发注意事项

### ETF代码格式
- A股ETF代码为6位数字（如：512880、159915）
- 沪市ETF以51开头，深市ETF以15、16开头

### 数据获取限制
- akshare数据免费但有频率限制
- ETFDataService实现了1小时缓存
- 避免短时间内大量请求

### 日期格式
- akshare历史数据使用YYYYMMDD格式
- 净值数据使用YYYY-MM-DD格式
- 内部统一使用datetime对象处理

### 错误处理
- 所有数据获取都有异常捕获
- 缺少净值数据时返回空列表而非报错
- CLI层面显示友好的错误信息
