# ETF Challenger

A股场内ETF基金分析工具，提供实时行情监控、溢价/折价分析、历史数据分析、持仓成分分析和智能交易建议功能。

## 功能特性

- **实时行情监控**：查看ETF最新价格、涨跌幅、成交量等实时数据
- **溢价/折价分析**：计算ETF市价与净值的偏离度，发现套利机会
- **历史数据分析**：技术指标分析、收益率计算、风险评估
- **持仓成分分析**：查看ETF持仓股票、行业分布、集中度等
- **智能交易建议** ⭐：综合多项技术指标，提供买入/卖出建议和目标价位
- **分析报告导出** 📄：生成Markdown/HTML/JSON格式的综合分析报告
- **批量对比分析** 📊：同时对比多只ETF，综合评分排名
- **ETF筛选器** 🎯：筛选流动性好、费率低的优质ETF
- **批量投资建议** 🔥：一键生成池中所有ETF的买卖建议报告

## 快速开始

### 安装

```bash
# 克隆仓库
git clone https://github.com/yourusername/etf-challenger.git
cd etf-challenger

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -e .
```

### 使用示例

```bash
# 列出所有ETF
etf list

# 搜索ETF（按代码或名称）
etf list 沪深300
etf list 512880

# 查看ETF实时行情
etf quote 510300

# 筛选优质ETF 🎯
etf screen                                # 默认筛选前10支
etf screen --top 20 --min-scale 10       # 规模≥10亿的前20支
etf screen --max-fee 0.50 --with-volume  # 低费率+成交量分析

# 批量投资建议 🔥
etf batch                                 # 使用默认池
etf batch --pool 行业主题                 # 指定ETF池
etf batch --format html -o report.html   # 生成HTML报告
etf batch --list-pools                   # 查看所有池

# 获取智能交易建议 ⭐
etf suggest 510300
etf suggest 515880 --days 90

# 生成综合分析报告 📄
etf report 510300
etf report 510300 --format html --output report.html
etf report 510300 --format json --output report.json

# 分析溢价/折价（默认30天）
etf premium 510300
etf premium 510300 --days 60

# 历史表现分析（默认90天）
etf analyze 510300
etf analyze 510300 --days 180

# 查看持仓成分（默认显示前10）
etf holdings 510300 --year 2024
etf holdings 159915 --limit 20 --year 2024
```

## 命令详解

### `etf list [关键词]`

列出所有场内ETF或搜索ETF

**选项**：
- `--limit, -l`：显示数量限制（默认20）

**示例**：
```bash
etf list                 # 列出所有ETF
etf list 科创50          # 搜索名称包含"科创50"的ETF
etf list 512             # 搜索代码包含"512"的ETF
etf list --limit 50      # 显示50只ETF
```

### `etf quote <代码>`

查看ETF实时行情

**示例**：
```bash
etf quote 512880         # 查看中证红利ETF实时行情
etf quote 159915         # 查看创业板ETF实时行情
```

**显示信息**：
- 最新价、涨跌额、涨跌幅
- 开盘价、最高价、最低价、昨收价
- 成交量、成交额
- 更新时间

### `etf premium <代码>`

分析ETF溢价/折价率

**选项**：
- `--days, -d`：分析天数（默认30天）

**示例**：
```bash
etf premium 512880           # 分析最近30天溢价率
etf premium 512880 --days 90 # 分析最近90天溢价率
```

**显示信息**：
- 每日市价、净值、溢价率
- 平均溢价率、最高/最低溢价率

### `etf analyze <代码>`

分析ETF历史表现

**选项**：
- `--days, -d`：分析天数（默认90天）

**示例**：
```bash
etf analyze 512880            # 分析最近90天表现
etf analyze 512880 --days 365 # 分析最近1年表现
```

**显示信息**：
- 总收益率、年化收益率
- 年化波动率
- 最大回撤
- 夏普比率
- 最近交易日数据（收盘价、MA、RSI等）

### `etf holdings <代码>`

查看ETF持仓成分

**选项**：
- `--limit, -l`：显示持仓数量（默认10）

**示例**：
```bash
etf holdings 512880          # 查看前10大持仓
etf holdings 512880 --limit 20 # 查看前20大持仓
```

**显示信息**：
- 持仓统计（总数、前5/10大权重）
- 持仓明细（代码、名称、权重）

### `etf screen` 🎯

筛选流动性好、费率低的优质ETF

**选项**：
- `--top, -t`：返回前N支ETF（默认10）
- `--min-scale, -s`：最小规模（亿份，默认5.0）
- `--max-fee, -f`：最大费率（%，默认0.60）
- `--with-volume, -v`：包含成交量分析（耗时较长）

**示例**：
```bash
etf screen                                # 使用默认参数
etf screen --top 20                      # 返回前20支
etf screen --min-scale 10                # 规模≥10亿的ETF
etf screen --max-fee 0.50                # 费率≤0.50%的ETF
etf screen --with-volume                 # 包含成交量分析
etf screen --top 15 --min-scale 20 --max-fee 0.50  # 组合条件
```

**显示信息**：
- 排名表格（代码、名称、交易所、规模、流动性评分）
- 统计信息（总规模、平均评分、平均成交额）
- 流动性前三名详情

**流动性评分说明**：
- ≥80分：优秀，适合大额交易
- 60-80分：良好，适合中等规模交易
- <60分：一般，建议小额交易

**使用场景**：
- 构建核心持仓：`etf screen --min-scale 50 --max-fee 0.50`
- 波段交易：`etf screen --min-scale 20 --with-volume`
- 行业轮动：`etf screen --min-scale 10 --max-fee 0.80`

详见：[ETF筛选功能使用指南](ETF_SCREENING_GUIDE.md)

### `etf batch` 🔥

批量生成ETF投资建议报告

从配置的ETF池中批量分析所有ETF，生成包含买入/卖出建议的综合报告。

**选项**：
- `--pool, -p`：ETF池名称（不指定则使用默认池）
- `--days, -d`：分析天数（默认60）
- `--output, -o`：输出文件路径
- `--format, -f`：报告格式（markdown/html，默认markdown）
- `--list-pools`：列出所有可用的ETF池

**示例**：
```bash
etf batch                                # 使用默认池
etf batch --pool 行业主题                # 指定池
etf batch --format html -o report.html  # 生成HTML报告
etf batch --list-pools                  # 查看所有池
etf batch --days 90 --pool 宽基指数     # 自定义天数
```

**配置ETF池**：

编辑 `etf_pool.json` 文件：
```json
{
  "pools": {
    "我的自选": {
      "description": "自定义ETF池",
      "etfs": ["510300", "510500", "159915"]
    }
  },
  "default_pool": "我的自选"
}
```

**报告内容**：
- 📋 执行摘要（买入/卖出/持有统计）
- 🟢 买入建议详情（强烈买入、买入）
- 🟡 持有建议列表
- 🔴 卖出建议详情（强烈卖出、卖出）
- 📊 综合排名（按评分排序）
- ⚠️ 风险提示

**综合评分说明**：
- 基于信号类型(40%)、置信度(20%)、年化收益(20%)、夏普比率(20%)
- 评分范围: 0-100分
- ≥70分: 良好标的
- <50分: 弱势标的

**使用场景**：
- 每周投资复盘：`etf batch --pool 我的持仓`
- 行业轮动决策：`etf batch --pool 行业主题`
- 构建新组合：从多个池选择最佳标的
- 定期调仓：根据买卖建议调整持仓

详见：[批量报告功能使用指南](BATCH_GUIDE.md)

## 技术栈

- **数据源**：[AKShare](https://akshare.akfamily.xyz/) - 免费开源的A股数据接口
- **数据处理**：pandas、numpy
- **CLI框架**：Click
- **终端美化**：Rich
- **Python版本**：3.9+

## 开发

### 安装开发依赖

```bash
pip install -e ".[dev]"
```

### 运行测试

```bash
pytest
pytest --cov=src/etf_challenger
```

### 代码格式化

```bash
black src/ tests/
ruff check src/ tests/
```

## 常见ETF代码

### 宽基指数ETF
- 510300 - 沪深300ETF（华泰柏瑞）
- 512880 - 中证红利ETF（证券ETF）
- 510500 - 中证500ETF
- 159915 - 创业板ETF
- 159919 - 沪深300ETF（嘉实）
- 588000 - 科创50ETF

### 行业主题ETF
- 512690 - 白酒ETF
- 159928 - 消费ETF
- 512480 - 半导体ETF
- 515880 - 通信ETF
- 512980 - 传媒ETF

## 注意事项

1. **数据延迟**：实时行情数据可能有1-2分钟延迟
2. **使用限制**：akshare为免费数据源，请勿频繁请求
3. **投资建议**：本工具仅供数据分析，不构成投资建议
4. **风险提示**：投资有风险，决策需谨慎

## 许可证

MIT License

## 贡献

欢迎提交Issue和Pull Request！

## 联系方式

如有问题或建议，请提交Issue。

### `etf suggest <代码>` ⭐

**获取智能交易建议（综合技术分析）**

基于多项技术指标的综合分析，提供买入/卖出/持有建议。

**选项**：
- `--days, -d`：分析天数（默认60天，建议30-90天）

**示例**：
```bash
etf suggest 510300           # 获取沪深300ETF的交易建议
etf suggest 515880 --days 90 # 基于90天数据分析
```

**分析指标**：
- ✓ **均线交叉**（MA5/MA20）- 金叉/死叉信号
- ✓ **RSI相对强弱**- 超买/超卖判断
- ✓ **MACD动能**- 趋势强度分析
- ✓ **布林带**- 价格波动范围
- ✓ **趋势分析**- 上升/下降趋势识别
- ✓ **成交量分析**- 量价配合情况
- ✓ **溢价率**- 估值高低判断

**输出信息**：
- 交易建议：强烈买入/买入/持有/卖出/强烈卖出
- 置信度：0-100%
- 风险等级：低/中/高
- 分析依据：具体的看涨/看跌理由
- 技术指标状态：各指标的当前状态
- 价格参考：目标价位和止损价位

**风险提示**：
- 建议仅供参考，不构成投资建议
- 技术分析存在滞后性
- 需结合基本面分析和自身风险承受能力


### `etf report <代码>` 📄

**生成ETF综合分析报告**

将所有分析结果整合为一份完整的报告，支持多种格式导出。

**选项**：
- `--output, -o`：输出文件路径（默认自动命名）
- `--format, -f`：报告格式（markdown/html/json，默认markdown）
- `--days, -d`：历史数据分析天数（默认60天）
- `--year, -y`：持仓数据年份（默认2024）

**示例**：
```bash
# 生成Markdown报告（默认）
etf report 510300

# 生成HTML报告（可在浏览器查看）
etf report 510300 --format html --output 510300.html

# 生成JSON报告（结构化数据）
etf report 510300 --format json --output 510300.json

# 自定义分析参数
etf report 510300 --days 90 --year 2024 --format html
```

**报告内容**：
- 📊 实时行情数据
- 🎯 智能交易建议（综合7项技术指标）
- 📈 历史表现分析（收益率、波动率、夏普比率等）
- 🔧 技术指标详情（MA、RSI、MACD、布林带等）
- 💎 溢价/折价分析
- 📊 持仓成分分析（前10大持仓）
- 📅 近期价格走势

**报告格式**：

1. **Markdown (.md)**
   - 纯文本格式，易于阅读和版本控制
   - 可在GitHub、编辑器中直接查看
   - 推荐用于记录和分享

2. **HTML (.html)**
   - 网页格式，美观的可视化展示
   - 可在浏览器中打开查看
   - 自带样式，适合打印或演示

3. **JSON (.json)**
   - 结构化数据格式
   - 方便程序处理和数据分析
   - 可导入Excel、数据库等

**使用场景**：
- 📝 每日/每周投资复盘
- 📊 投资决策依据存档
- 👥 与他人分享分析结果
- 💾 建立投资数据库
- 📈 跟踪ETF长期表现

