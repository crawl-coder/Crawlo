#!/bin/bash

# 分布式爬虫启动脚本
# 用法: ./start_cluster.sh [节点数量]

NODE_COUNT=${1:-3}  # 默认3个节点
REDIS_URL="redis://localhost:6379/0"

echo "正在启动 $NODE_COUNT 个分布式爬虫节点..."
echo "Redis连接: $REDIS_URL"

# 检查Redis连接
echo "检查Redis连接..."
if ! redis-cli -u $REDIS_URL ping > /dev/null 2>&1; then
    echo "错误: 无法连接到Redis服务器"
    echo "请确保Redis服务正在运行: redis-server"
    exit 1
fi

echo "Redis连接正常"

# 清理旧的PID文件
rm -f *.pid

# 启动节点
for i in $(seq 1 $NODE_COUNT); do
    NODE_NAME="news-crawler-node-$i"
    CONCURRENT=$((15 + i * 5))  # 递增并发数
    
    echo "启动节点 $NODE_NAME (并发数: $CONCURRENT)..."
    python deploy.py $NODE_NAME --concurrent $CONCURRENT --redis-url $REDIS_URL --daemon
    
    sleep 2  # 间隔启动
done

echo ""
echo "=== 分布式集群启动完成 ==="
echo "节点数量: $NODE_COUNT"
echo "查看运行状态: ps aux | grep python"
echo "停止集群: ./stop_cluster.sh"
echo "查看日志: tail -f logs/*.log"

# 显示运行中的进程
echo ""
echo "运行中的爬虫进程:"
ps aux | grep "run.py" | grep -v grep