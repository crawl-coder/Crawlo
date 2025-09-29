#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试配置加载问题
"""

import os
import sys

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

print(f"当前工作目录: {os.getcwd()}")
print(f"项目根目录: {project_root}")

# 检查配置文件
cfg_file = os.path.join(project_root, "crawlo.cfg")
print(f"配置文件路径: {cfg_file}")
print(f"配置文件存在: {os.path.exists(cfg_file)}")

if os.path.exists(cfg_file):
    with open(cfg_file, 'r', encoding='utf-8') as f:
        print("配置文件内容:")
        print(f.read())

# 导入配置模块
try:
    import ofweek_standalone.settings as settings_module
    print("\n成功导入 settings 模块")
    print(f"QUEUE_TYPE in settings module: {getattr(settings_module, 'QUEUE_TYPE', 'NOT FOUND')}")
    print(f"FILTER_CLASS in settings module: {getattr(settings_module, 'FILTER_CLASS', 'NOT FOUND')}")
except Exception as e:
    print(f"导入 settings 模块失败: {e}")

# 使用框架方式加载配置
try:
    from crawlo.project import _load_project_settings
    settings = _load_project_settings()
    print(f"\n通过 _load_project_settings 加载的 QUEUE_TYPE: {settings.get('QUEUE_TYPE', 'NOT FOUND')}")
    print(f"通过 _load_project_settings 加载的 FILTER_CLASS: {settings.get('FILTER_CLASS', 'NOT FOUND')}")
except Exception as e:
    print(f"通过 _load_project_settings 加载配置失败: {e}")

# 使用初始化器加载配置
try:
    from crawlo.initialization import initialize_framework
    settings = initialize_framework()
    print(f"\n通过 initialize_framework 加载的 QUEUE_TYPE: {settings.get('QUEUE_TYPE', 'NOT FOUND')}")
    print(f"通过 initialize_framework 加载的 FILTER_CLASS: {settings.get('FILTER_CLASS', 'NOT FOUND')}")
except Exception as e:
    print(f"通过 initialize_framework 加载配置失败: {e}")