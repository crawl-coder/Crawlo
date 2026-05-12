import sys, re
from datetime import datetime
sys.stdout.reconfigure(encoding='utf-8')

# 查找所有可能的日志文件位置
import os, glob

# 搜索日志文件
log_dirs = [
    r'D:\dowell\others\Crawlo\examples\ofweek_standalone\logs',
    r'D:\dowell\others\Crawlo\examples\ofweek_standalone',
    r'D:\dowell\others\Crawlo\logs',
]

found_logs = []
for d in log_dirs:
    if os.path.exists(d):
        for f in os.listdir(d):
            if f.endswith('.log'):
                found_logs.append(os.path.join(d, f))

# 也递归搜索
for root, dirs, files in os.walk(r'D:\dowell\others\Crawlo\examples\ofweek_standalone'):
    for f in files:
        if f.endswith('.log'):
            path = os.path.join(root, f)
            if path not in found_logs:
                found_logs.append(path)

print(f"找到日志文件: {len(found_logs)}")
for f in found_logs:
    size = os.path.getsize(f)
    print(f"  {f} ({size} bytes)")
