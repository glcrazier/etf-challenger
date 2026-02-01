#!/bin/bash

# ETF监控系统 - 一键部署脚本
# 适用于 Ubuntu/Debian 系统

set -e  # 遇到错误立即退出

echo "================================"
echo "ETF监控系统 - 一键部署脚本"
echo "================================"
echo ""

# 检查Python版本
echo "检查Python版本..."
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python版本: $PYTHON_VERSION"

# 创建虚拟环境
echo ""
echo "创建Python虚拟环境..."
python3 -m venv venv

# 激活虚拟环境
echo "激活虚拟环境..."
source venv/bin/activate

# 升级pip
echo ""
echo "升级pip..."
pip install --upgrade pip

# 安装依赖
echo ""
echo "安装项目依赖..."
pip install -e .

# 创建目录
echo ""
echo "创建必要目录..."
mkdir -p ~/.etf_challenger/{config,logs,reports}

# 验证安装
echo ""
echo "验证安装..."
etf --version

echo ""
echo "================================"
echo "部署完成！"
echo "================================"
echo ""
echo "下一步操作："
echo "1. 配置邮件: etf monitor config"
echo "2. 测试邮件: etf monitor test-email"
echo "3. 手动触发: etf monitor trigger --session morning"
echo "4. 查看状态: etf monitor status"
echo ""
echo "systemd服务配置："
echo "sudo cp deploy/etf-monitor.service /etc/systemd/system/"
echo "sudo systemctl daemon-reload"
echo "sudo systemctl enable etf-monitor"
echo "sudo systemctl start etf-monitor"
echo ""
