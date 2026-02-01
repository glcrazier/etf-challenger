#!/bin/bash

# ETF配置备份脚本

BACKUP_DIR="$HOME/backups"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# 备份配置
tar -czf $BACKUP_DIR/etf_config_$DATE.tar.gz \
    ~/.etf_challenger/config/ \
    ~/etf-challenger/etf_pool.json

# 保留最近30天的备份
find $BACKUP_DIR -name "etf_config_*.tar.gz" -mtime +30 -delete

echo "配置备份完成: $BACKUP_DIR/etf_config_$DATE.tar.gz"
