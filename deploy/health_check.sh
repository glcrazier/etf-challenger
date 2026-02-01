#!/bin/bash

# ETF监控服务健康检查脚本

SERVICE_NAME="etf-monitor"
LOG_FILE="$HOME/.etf_challenger/logs/health_check.log"
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
DISK_USAGE=$(df -h $HOME/.etf_challenger/reports | awk 'NR==2 {print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -gt 80 ]; then
    echo "$(date): 警告 - 报告存储空间使用率超过80%: ${DISK_USAGE}%" >> $LOG_FILE
fi

exit 0
