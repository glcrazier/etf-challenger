# ETF监控系统 - Linux服务器部署手册

## 📋 目录

1. [服务器要求](#服务器要求)
2. [安装部署](#安装部署)
3. [配置设置](#配置设置)
4. [系统服务配置](#系统服务配置)
5. [测试验证](#测试验证)
6. [监控维护](#监控维护)
7. [故障排查](#故障排查)
8. [备份恢复](#备份恢复)

---

## 服务器要求

### 最低配置
- **操作系统**: Ubuntu 20.04+ / CentOS 8+ / Debian 11+
- **CPU**: 1核心
- **内存**: 1GB RAM
- **磁盘**: 10GB可用空间（报告存储）
- **Python**: 3.9+
- **网络**: 稳定的互联网连接（访问A股数据源和SMTP服务器）

### 推荐配置
- **CPU**: 2核心
- **内存**: 2GB RAM
- **磁盘**: 20GB SSD
- **带宽**: 10Mbps+

---

## 安装部署

### 步骤1: 连接到服务器

```bash
# 使用SSH连接到远程服务器
ssh username@your-server-ip

# 示例
ssh ubuntu@192.168.1.100
```

### 步骤2: 更新系统并安装依赖

```bash
# Ubuntu/Debian
sudo apt update
sudo apt upgrade -y
sudo apt install -y python3 python3-pip python3-venv git

# CentOS/RHEL
sudo yum update -y
sudo yum install -y python3 python3-pip git
```

### 步骤3: 创建专用用户（可选但推荐）

```bash
# 创建etf用户
sudo useradd -m -s /bin/bash etf

# 设置密码
sudo passwd etf

# 切换到etf用户
sudo su - etf
```

### 步骤4: 克隆项目代码

```bash
# 使用etf用户或你的用户
cd ~

# 从Git仓库克隆（替换为实际仓库地址）
git clone https://github.com/your-repo/etf-challenger.git

# 或者从本地上传（在本地执行）
# scp -r /path/to/etf-challenger username@server-ip:/home/username/

cd etf-challenger
```

### 步骤5: 创建虚拟环境

```bash
# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate

# 验证Python版本
python --version  # 应显示 Python 3.9+
```

### 步骤6: 安装Python依赖

```bash
# 升级pip
pip install --upgrade pip

# 安装项目依赖
pip install -e .

# 验证安装
etf --version
```

**预期输出**:
```
etf, version 0.1.0
```

### 步骤7: 创建必要的目录

```bash
# 创建配置和日志目录
mkdir -p ~/.etf_challenger/{config,logs,reports}

# 验证目录结构
tree -L 2 ~/.etf_challenger
```

---

## 配置设置

### 步骤1: 配置邮件服务

```bash
# 使用交互式配置向导
etf monitor config
```

**交互式配置示例**:
```
发件邮箱: your_email@163.com
授权码: ****************
收件人（逗号分隔）: recipient1@example.com,recipient2@example.com

✓ 配置已保存到: /home/etf/.etf_challenger/config/scheduler_config.toml
```

### 步骤2: 获取163邮箱授权码

1. 登录 [mail.163.com](https://mail.163.com)
2. 点击 **设置** → **POP3/SMTP/IMAP**
3. 开启 **SMTP服务**
4. 点击 **获取授权码**
5. 根据提示发送短信验证
6. 复制授权码（16位字符串）

### 步骤3: 编辑高级配置（可选）

```bash
# 编辑配置文件
nano ~/.etf_challenger/config/scheduler_config.toml
```

**关键配置项**:

```toml
[watchlists]
# 监控的ETF池（可根据需要调整）
pools = [
    "宽基指数",
    "医疗医药",
    "科技创新",
    "金融券商",
    "港股海外",
    "消费能源",
    "精选组合"
]

[report]
# 报告格式
formats = ["html", "markdown", "json"]
# 分析天数
analysis_days = 60
# 是否包含持仓分析（耗时较长，建议false）
include_holdings = false

[storage]
# 报告存储路径
base_path = "~/.etf_challenger/reports"
# 归档天数
archive_after_days = 90

[email]
# 是否启用邮件
enabled = true
# 是否发送每日汇总
send_daily_summary = true

[market]
# 早盘报告时间（开盘后30分钟）
morning_report_time = "10:00"
# 尾盘报告时间（收盘前30分钟）
afternoon_report_time = "14:30"

[logging]
# 日志级别: DEBUG, INFO, WARNING, ERROR
level = "INFO"
```

保存并退出：`Ctrl+X` → `Y` → `Enter`

### 步骤4: 验证配置

```bash
# 查看配置文件
cat ~/.etf_challenger/config/scheduler_config.toml

# 测试邮件发送
etf monitor test-email
```

**预期输出**:
```
✓ 测试邮件已发送，请检查收件箱
```

检查邮箱应收到测试邮件。

---

## 系统服务配置

### 方法1: 使用systemd服务（推荐）

#### 1.1 创建systemd服务文件

```bash
# 切换到root或使用sudo
sudo nano /etc/systemd/system/etf-monitor.service
```

**服务文件内容**:

```ini
[Unit]
Description=ETF Monitoring and Report Generation Service
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=etf
Group=etf
WorkingDirectory=/home/etf/etf-challenger
Environment="PATH=/home/etf/etf-challenger/venv/bin:/usr/local/bin:/usr/bin:/bin"

# 启动命令（前台运行）
ExecStart=/home/etf/etf-challenger/venv/bin/python -m etf_challenger.cli.main monitor start

# 重启策略
Restart=on-failure
RestartSec=10s

# 日志输出
StandardOutput=append:/home/etf/.etf_challenger/logs/stdout.log
StandardError=append:/home/etf/.etf_challenger/logs/stderr.log

# 资源限制
MemoryLimit=1G
CPUQuota=100%

[Install]
WantedBy=multi-user.target
```

**注意**:
- 替换 `/home/etf` 为实际用户主目录
- 替换 `etf` 为实际用户名

#### 1.2 重载systemd配置

```bash
# 重载systemd配置
sudo systemctl daemon-reload

# 启用开机自启动
sudo systemctl enable etf-monitor.service
```

#### 1.3 启动服务

```bash
# 启动服务
sudo systemctl start etf-monitor.service

# 查看状态
sudo systemctl status etf-monitor.service
```

**预期输出**:
```
● etf-monitor.service - ETF Monitoring and Report Generation Service
     Loaded: loaded (/etc/systemd/system/etf-monitor.service; enabled)
     Active: active (running) since Sat 2026-02-01 09:00:00 CST; 5s ago
   Main PID: 12345 (python)
      Tasks: 3
     Memory: 150M
        CPU: 2s
     CGroup: /system.slice/etf-monitor.service
             └─12345 /home/etf/etf-challenger/venv/bin/python...
```

#### 1.4 常用systemd命令

```bash
# 启动服务
sudo systemctl start etf-monitor

# 停止服务
sudo systemctl stop etf-monitor

# 重启服务
sudo systemctl restart etf-monitor

# 查看状态
sudo systemctl status etf-monitor

# 查看日志
sudo journalctl -u etf-monitor -f

# 查看最近50行日志
sudo journalctl -u etf-monitor -n 50

# 禁用开机自启动
sudo systemctl disable etf-monitor
```

---

### 方法2: 使用内置守护进程（备选）

```bash
# 启动守护进程
etf monitor start --daemon

# 查看状态
etf monitor status

# 停止守护进程
etf monitor stop
```

**注意**: 内置守护进程不会自动开机启动，推荐使用systemd。

---

## 测试验证

### 1. 手动触发报告生成

```bash
# 激活虚拟环境（如果未激活）
cd ~/etf-challenger
source venv/bin/activate

# 手动生成早盘报告
etf monitor trigger --session morning
```

**预期输出**:
```
✓ 成功生成21个报告
处理池: 7个
汇总文件: /home/etf/.etf_challenger/reports/daily/2026/02/01/morning/summary_morning.json
```

### 2. 检查生成的报告

```bash
# 查看报告列表
etf monitor reports --date 2026-02-01

# 查看报告文件
ls -lh ~/.etf_challenger/reports/daily/2026/02/01/morning/
```

**预期输出**:
```
total 10M
-rw-r--r-- 1 etf etf 512K Feb  1 10:05 宽基指数_20260201_1000.html
-rw-r--r-- 1 etf etf 256K Feb  1 10:05 宽基指数_20260201_1000.md
-rw-r--r-- 1 etf etf 128K Feb  1 10:05 宽基指数_20260201_1000.json
...
-rw-r--r-- 1 etf etf  64K Feb  1 10:05 summary_morning.json
```

### 3. 检查邮件发送

检查收件箱是否收到汇总邮件，邮件主题格式为：
```
[ETF监控] 2026-02-01 早盘报告
```

### 4. 查看日志

```bash
# 查看调度器日志
tail -f ~/.etf_challenger/logs/scheduler.log

# 查看systemd日志
sudo journalctl -u etf-monitor -f
```

### 5. 验证定时任务

```bash
# 修改配置文件，设置测试时间（例如5分钟后）
nano ~/.etf_challenger/config/scheduler_config.toml

# 将 morning_report_time 改为当前时间+5分钟
# 例如现在是 14:30，改为 14:35

# 重启服务
sudo systemctl restart etf-monitor

# 观察日志
tail -f ~/.etf_challenger/logs/scheduler.log
```

等待5分钟，应看到日志输出报告生成信息。

---

## 监控维护

### 1. 设置日志轮转

创建logrotate配置：

```bash
sudo nano /etc/logrotate.d/etf-monitor
```

**配置内容**:
```
/home/etf/.etf_challenger/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 0644 etf etf
    sharedscripts
    postrotate
        systemctl reload etf-monitor > /dev/null 2>&1 || true
    endscript
}
```

### 2. 定期清理旧报告

配置cron任务自动归档：

```bash
# 编辑crontab
crontab -e
```

添加以下行：
```cron
# 每周日凌晨2点清理90天前的报告
0 2 * * 0 /home/etf/etf-challenger/venv/bin/python -c "from etf_challenger.storage.report_storage import ReportStorage; ReportStorage().archive_old_reports(90)"
```

### 3. 监控脚本

创建健康检查脚本：

```bash
nano ~/check_etf_monitor.sh
```

**脚本内容**:
```bash
#!/bin/bash

# ETF监控服务健康检查脚本

SERVICE_NAME="etf-monitor"
LOG_FILE="/home/etf/.etf_challenger/logs/health_check.log"
ALERT_EMAIL="admin@example.com"

# 检查服务状态
if ! systemctl is-active --quiet $SERVICE_NAME; then
    echo "$(date): ETF监控服务已停止，正在重启..." >> $LOG_FILE

    # 重启服务
    sudo systemctl restart $SERVICE_NAME

    # 发送告警邮件（需配置）
    echo "ETF监控服务异常，已自动重启" | mail -s "[告警] ETF监控服务异常" $ALERT_EMAIL

    exit 1
fi

# 检查进程CPU/内存使用
PID=$(systemctl show -p MainPID $SERVICE_NAME | cut -d= -f2)
if [ "$PID" != "0" ]; then
    CPU=$(ps -p $PID -o %cpu --no-headers)
    MEM=$(ps -p $PID -o %mem --no-headers)

    echo "$(date): 服务运行正常 - PID: $PID, CPU: $CPU%, MEM: $MEM%" >> $LOG_FILE
fi

# 检查磁盘空间
DISK_USAGE=$(df -h /home/etf/.etf_challenger/reports | awk 'NR==2 {print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -gt 80 ]; then
    echo "$(date): 警告 - 报告存储空间使用率超过80%: ${DISK_USAGE}%" >> $LOG_FILE
fi

exit 0
```

设置定时执行：
```bash
chmod +x ~/check_etf_monitor.sh

# 每5分钟检查一次
crontab -e
# 添加：
*/5 * * * * /home/etf/check_etf_monitor.sh
```

### 4. 监控命令

```bash
# 查看服务状态
sudo systemctl status etf-monitor

# 查看实时日志
tail -f ~/.etf_challenger/logs/scheduler.log

# 查看邮件发送日志
tail -f ~/.etf_challenger/logs/email.log

# 查看今日生成的报告
etf monitor reports --date $(date +%Y-%m-%d)

# 查看存储使用情况
du -sh ~/.etf_challenger/reports/

# 查看进程资源占用
ps aux | grep etf-challenger
top -p $(pgrep -f etf-challenger)
```

---

## 故障排查

### 问题1: 服务无法启动

**症状**:
```bash
sudo systemctl status etf-monitor
# 显示 failed 或 inactive
```

**排查步骤**:

1. 查看详细错误日志
```bash
sudo journalctl -u etf-monitor -n 100
```

2. 检查Python环境
```bash
/home/etf/etf-challenger/venv/bin/python --version
/home/etf/etf-challenger/venv/bin/etf --version
```

3. 检查权限
```bash
ls -l /home/etf/etf-challenger/
ls -l ~/.etf_challenger/
```

4. 手动启动测试
```bash
cd ~/etf-challenger
source venv/bin/activate
etf monitor start  # 前台运行，观察错误
```

### 问题2: 邮件发送失败

**症状**: 日志显示 "邮件发送失败" 或收不到邮件

**排查步骤**:

1. 检查配置
```bash
cat ~/.etf_challenger/config/scheduler_config.toml | grep -A 10 "\[email\]"
```

2. 测试SMTP连接
```bash
python3 -c "
import smtplib
try:
    server = smtplib.SMTP_SSL('smtp.163.com', 465, timeout=10)
    server.login('your_email@163.com', 'your_auth_code')
    print('SMTP连接成功')
    server.quit()
except Exception as e:
    print(f'SMTP连接失败: {e}')
"
```

3. 检查163授权码
- 重新获取授权码
- 确认使用授权码而非登录密码

4. 检查网络
```bash
ping smtp.163.com
telnet smtp.163.com 465
```

5. 查看邮件日志
```bash
tail -f ~/.etf_challenger/logs/email.log
```

### 问题3: 报告生成失败

**症状**: 日志显示 "报告生成失败" 或报告文件缺失

**排查步骤**:

1. 检查网络连接
```bash
# 测试访问A股数据源
ping -c 3 push2.eastmoney.com
```

2. 检查ETF池配置
```bash
ls -l etf_pool.json
cat etf_pool.json
```

3. 手动测试单个ETF
```bash
source ~/etf-challenger/venv/bin/activate
etf quote 510300
etf suggest 510300
```

4. 检查磁盘空间
```bash
df -h ~/.etf_challenger/
```

5. 查看详细日志
```bash
tail -n 200 ~/.etf_challenger/logs/scheduler.log
```

### 问题4: 时区问题

**症状**: 报告生成时间不正确

**解决方案**:

```bash
# 检查系统时区
timedatectl

# 设置时区为上海（中国标准时间）
sudo timedatectl set-timezone Asia/Shanghai

# 验证
date
```

### 问题5: 内存不足

**症状**: 服务频繁重启，日志显示内存错误

**解决方案**:

1. 减少并发数
```bash
# 编辑报告生成任务，减少线程数
# 在 report_job.py 中减少并发ETF池数量
```

2. 调整systemd内存限制
```bash
sudo nano /etc/systemd/system/etf-monitor.service

# 修改
MemoryLimit=2G  # 从1G增加到2G

sudo systemctl daemon-reload
sudo systemctl restart etf-monitor
```

3. 增加swap空间
```bash
# 创建2GB swap文件
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# 永久生效
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

---

## 备份恢复

### 备份策略

#### 1. 备份配置文件

```bash
# 创建备份脚本
cat > ~/backup_etf_config.sh << 'EOF'
#!/bin/bash

BACKUP_DIR="/home/etf/backups"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# 备份配置
tar -czf $BACKUP_DIR/etf_config_$DATE.tar.gz \
    ~/.etf_challenger/config/ \
    ~/etf-challenger/etf_pool.json

# 保留最近30天的备份
find $BACKUP_DIR -name "etf_config_*.tar.gz" -mtime +30 -delete

echo "配置备份完成: $BACKUP_DIR/etf_config_$DATE.tar.gz"
EOF

chmod +x ~/backup_etf_config.sh
```

#### 2. 备份报告数据

```bash
# 创建报告备份脚本
cat > ~/backup_etf_reports.sh << 'EOF'
#!/bin/bash

BACKUP_DIR="/home/etf/backups"
DATE=$(date +%Y%m%d)
REPORTS_DIR=~/.etf_challenger/reports

mkdir -p $BACKUP_DIR

# 只备份最近7天的报告
find $REPORTS_DIR -name "*.html" -mtime -7 | \
    tar -czf $BACKUP_DIR/etf_reports_$DATE.tar.gz -T -

echo "报告备份完成: $BACKUP_DIR/etf_reports_$DATE.tar.gz"
EOF

chmod +x ~/backup_etf_reports.sh
```

#### 3. 定时备份

```bash
crontab -e

# 添加以下行
# 每天凌晨1点备份配置
0 1 * * * /home/etf/backup_etf_config.sh

# 每周日凌晨1点备份报告
0 1 * * 0 /home/etf/backup_etf_reports.sh
```

### 恢复步骤

#### 恢复配置

```bash
# 停止服务
sudo systemctl stop etf-monitor

# 解压备份
tar -xzf /home/etf/backups/etf_config_20260201_010000.tar.gz -C /

# 启动服务
sudo systemctl start etf-monitor
```

#### 恢复报告

```bash
# 解压报告备份
tar -xzf /home/etf/backups/etf_reports_20260201.tar.gz -C ~/.etf_challenger/reports/
```

---

## 远程访问报告（可选）

### 方法1: 使用Nginx提供Web访问

```bash
# 安装Nginx
sudo apt install nginx

# 创建配置
sudo nano /etc/nginx/sites-available/etf-reports
```

**配置内容**:
```nginx
server {
    listen 8080;
    server_name _;

    root /home/etf/.etf_challenger/reports;

    location / {
        autoindex on;
        autoindex_exact_size off;
        autoindex_localtime on;

        # 基础认证
        auth_basic "ETF Reports";
        auth_basic_user_file /etc/nginx/.htpasswd;
    }
}
```

```bash
# 创建密码文件
sudo apt install apache2-utils
sudo htpasswd -c /etc/nginx/.htpasswd admin

# 启用配置
sudo ln -s /etc/nginx/sites-available/etf-reports /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

# 开放防火墙
sudo ufw allow 8080/tcp
```

访问: `http://your-server-ip:8080`

### 方法2: 使用scp下载报告

```bash
# 在本地机器执行
scp -r username@server-ip:/home/etf/.etf_challenger/reports/daily/2026/02/01/ ./
```

---

## 安全建议

1. **使用防火墙**
```bash
# 只开放必要端口
sudo ufw enable
sudo ufw allow 22/tcp  # SSH
sudo ufw allow 8080/tcp  # 如果使用Nginx
```

2. **定期更新**
```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 更新Python依赖
cd ~/etf-challenger
source venv/bin/activate
pip install --upgrade pip
pip list --outdated
```

3. **保护配置文件**
```bash
# 设置适当权限
chmod 600 ~/.etf_challenger/config/scheduler_config.toml
```

4. **使用环境变量存储密码**
```bash
# 编辑 ~/.bashrc 或 ~/.profile
nano ~/.bashrc

# 添加
export ETF_SENDER_EMAIL="your_email@163.com"
export ETF_SENDER_PASSWORD="your_auth_code"

# 重新加载
source ~/.bashrc

# 配置文件中移除明文密码
# scheduler_config.toml 会自动读取环境变量
```

---

## 快速参考卡

### 常用命令

```bash
# 启动服务
sudo systemctl start etf-monitor

# 停止服务
sudo systemctl stop etf-monitor

# 重启服务
sudo systemctl restart etf-monitor

# 查看状态
sudo systemctl status etf-monitor

# 查看日志
tail -f ~/.etf_challenger/logs/scheduler.log

# 手动触发
etf monitor trigger --session morning

# 测试邮件
etf monitor test-email

# 查看报告
etf monitor reports --date 2026-02-01
```

### 重要文件位置

```
配置文件: ~/.etf_challenger/config/scheduler_config.toml
日志文件: ~/.etf_challenger/logs/scheduler.log
报告目录: ~/.etf_challenger/reports/daily/
服务文件: /etc/systemd/system/etf-monitor.service
项目目录: ~/etf-challenger/
虚拟环境: ~/etf-challenger/venv/
```

---

## 联系与支持

- **项目文档**: `/home/etf/etf-challenger/README.md`
- **问题反馈**: GitHub Issues
- **日志查看**: `~/.etf_challenger/logs/`

---

**部署完成！** 🎉

现在系统将在每个交易日的早盘10:00和尾盘14:30自动生成ETF投资建议报告，并发送邮件汇总。
