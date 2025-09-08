#!/bin/bash

# 停止分布式爬虫集群

echo "正在停止分布式爬虫集群..."

# 通过PID文件停止进程
for pid_file in *.pid; do
    if [ -f "$pid_file" ]; then
        pid=$(cat "$pid_file")
        node_name=$(basename "$pid_file" .pid)
        
        echo "停止节点 $node_name (PID: $pid)..."
        
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid"
            sleep 2
            
            # 强制停止
            if kill -0 "$pid" 2>/dev/null; then
                echo "强制停止节点 $node_name..."
                kill -9 "$pid"
            fi
        fi
        
        rm -f "$pid_file"
    fi
done

# 清理残留进程
echo "清理残留进程..."
pkill -f "run.py"

echo ""
echo "=== 集群已停止 ==="

# 显示剩余进程
remaining=$(ps aux | grep "run.py" | grep -v grep | wc -l)
if [ $remaining -gt 0 ]; then
    echo "警告: 仍有 $remaining 个相关进程在运行"
    ps aux | grep "run.py" | grep -v grep
else
    echo "所有爬虫进程已停止"
fi