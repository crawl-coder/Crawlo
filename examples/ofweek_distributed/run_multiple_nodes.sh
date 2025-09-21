#!/bin/bash
# 多节点分布式采集启动脚本

echo "=== Crawlo多节点分布式采集测试 ==="
echo "此脚本将启动5个爬虫节点来测试分布式功能"
echo "请确保Redis服务正在运行"
echo "=================================="

# 检查Redis是否运行
if ! command -v redis-cli &> /dev/null; then
    echo "错误: 未找到redis-cli命令"
    exit 1
fi

if ! redis-cli ping &> /dev/null; then
    echo "错误: Redis服务未运行"
    exit 1
fi

echo "✓ Redis服务运行正常"
echo ""

# 清理之前的Redis数据（可选）
echo "清理之前的分布式采集数据..."
redis-cli -n 2 DEL "crawlo:ofweek_distributed:queue:requests" > /dev/null 2>&1
redis-cli -n 2 DEL "crawlo:ofweek_distributed:filter:fingerprint" > /dev/null 2>&1
redis-cli -n 2 DEL "crawlo:ofweek_distributed:item:fingerprint" > /dev/null 2>&1
echo "✓ Redis数据清理完成"
echo ""

# 启动节点说明
echo "启动5个爬虫节点:"
echo "1. 打开5个新的终端窗口"
echo "2. 在每个终端中执行以下命令:"
echo ""
echo "   cd $(pwd)"
echo "   python run.py"
echo ""
echo "或者使用以下命令在后台启动节点:"
echo ""

# 生成启动命令
for i in {1..5}; do
    echo "节点 $i: "
    echo "  NODE_ID=$i nohup python run.py > node_$i.log 2>&1 &"
    echo ""
done

echo "查看节点运行状态:"
echo "  ps aux | grep python | grep run.py"
echo ""
echo "停止所有节点:"
echo "  pkill -f \"python run.py\""
echo ""
echo "查看Redis队列状态:"
echo "  redis-cli -n 2 zcard \"crawlo:ofweek_distributed:queue:requests\""
echo "  redis-cli -n 2 scard \"crawlo:ofweek_distributed:filter:fingerprint\""
echo "  redis-cli -n 2 scard \"crawlo:ofweek_distributed:item:fingerprint\""