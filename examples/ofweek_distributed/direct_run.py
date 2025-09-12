#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import sys
import os

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# 切换到项目根目录
os.chdir(project_root)

from crawlo.commands.run import main

if __name__ == '__main__':
    # 模拟命令行参数
    args = ['of_week_distributed']
    main(args)