#!/bin/bash
# Redis 去重监控脚本
# 实时查看分布式去重的 Redis 操作

echo "========================================"
echo "Redis 去重实时监控"
echo "========================================"
echo ""
echo "按 Ctrl+C 停止监控"
echo ""

# Redis 配置
REDIS_HOST="127.0.0.1"
REDIS_PORT="6379"
REDIS_DB="15"

# 项目名称
PROJECT_NAME="dedup_test"

# 清屏并显示标题
clear

while true; do
    # 移动光标到顶部
    tput cup 0 0
    
    echo "========================================"
    echo "Redis 去重实时监控 (DB: $REDIS_DB)"
    echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "========================================"
    echo ""
    
    # 获取过滤器指纹数量
    FILTER_COUNT=$(redis-cli -h $REDIS_HOST -p $REDIS_PORT -n $REDIS_DB \
        SCARD "crawlo:${PROJECT_NAME}:filter:fingerprint" 2>/dev/null || echo "0")
    
    # 获取数据项指纹数量
    ITEM_COUNT=$(redis-cli -h $REDIS_HOST -p $REDIS_PORT -n $REDIS_DB \
        SCARD "crawlo:${PROJECT_NAME}:item:fingerprint" 2>/dev/null || echo "0")
    
    # 获取队列长度
    QUEUE_LEN=$(redis-cli -h $REDIS_HOST -p $REDIS_PORT -n $REDIS_DB \
        ZCARD "crawlo:${PROJECT_NAME}:queue:requests" 2>/dev/null || echo "0")
    
    echo "📊 实时统计:"
    echo "  - URL 指纹数 (过滤器): $FILTER_COUNT"
    echo "  - 数据项指纹数: $ITEM_COUNT"
    echo "  - 待处理队列长度: $QUEUE_LEN"
    echo ""
    
    # 显示最近的 URL 指纹（前 5 个）
    echo "🔍 最近的 URL 指纹:"
    redis-cli -h $REDIS_HOST -p $REDIS_PORT -n $REDIS_DB \
        SRANDMEMBER "crawlo:${PROJECT_NAME}:filter:fingerprint" 5 2>/dev/null | \
        head -5 | sed 's/^/  - /'
    echo ""
    
    # 显示所有相关的 key
    echo "🔑 Redis Keys:"
    redis-cli -h $REDIS_HOST -p $REDIS_PORT -n $REDIS_DB \
        KEYS "crawlo:${PROJECT_NAME}:*" 2>/dev/null | \
        sed 's/^/  - /'
    echo ""
    
    echo "========================================"
    echo "提示: 在另一个终端运行测试脚本"
    echo "  python tests/distributed_dedup_test.py"
    echo "========================================"
    
    # 每秒更新一次
    sleep 1
done
