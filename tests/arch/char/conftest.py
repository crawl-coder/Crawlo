#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Characterization tests 局部 collection 配置
===========================================

本目录下的测试文件命名为 ``char_*.py``（非默认 ``test_*.py``），
通过 ``pytest_collect_file`` 钩子让 pytest 识别这些文件为可收集模块。
文件内仍使用标准 ``Test*`` 类与 ``test_*`` 方法命名。
"""
import pytest


def pytest_collect_file(parent, file_path):
    if file_path.suffix == ".py" and file_path.name.startswith("char_"):
        return pytest.Module.from_parent(parent, path=file_path)
