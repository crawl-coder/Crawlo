#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
P1-B2 插件示例一致性守护
======================

防止 examples/plugin_hello_world 与框架插件机制脱节：
1. 示例包可导入、可注册（register_plugins 幂等）；
2. 短名称 / 类型前缀 / 完整路径三种解析方式对示例类全部生效；
3. 文档承诺的插件契约（create_instance / from_crawler）真实存在。
"""

import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_DIR = ROOT / "examples"


def _ensure_examples_on_path():
    if str(EXAMPLES_DIR) not in sys.path:
        sys.path.insert(0, str(EXAMPLES_DIR))


def test_plugin_example_importable_and_registrable():
    _ensure_examples_on_path()
    plugin = importlib.import_module("plugin_hello_world")
    assert callable(plugin.register_plugins)

    # 幂等注册
    plugin.register_plugins()
    plugin.register_plugins()


def test_plugin_example_resolution_channels():
    _ensure_examples_on_path()
    from plugin_hello_world import register_plugins
    from plugin_hello_world.hello_plugin.extension import HelloExtension
    from plugin_hello_world.hello_plugin.middleware import HelloMiddleware
    from plugin_hello_world.hello_plugin.pipeline import HelloPipeline
    from crawlo.utils.misc import load_object

    register_plugins()
    assert load_object("hello_mw") is HelloMiddleware
    assert load_object("pipeline:hello_pipe") is HelloPipeline
    assert load_object(
        "plugin_hello_world.hello_plugin.extension.HelloExtension"
    ) is HelloExtension


def test_plugin_contracts():
    """插件类必须实现文档承诺的框架契约。"""
    _ensure_examples_on_path()
    from plugin_hello_world.hello_plugin.extension import HelloExtension
    from plugin_hello_world.hello_plugin.middleware import HelloMiddleware
    from plugin_hello_world.hello_plugin.pipeline import HelloPipeline

    assert hasattr(HelloMiddleware, "create_instance")
    assert hasattr(HelloPipeline, "from_crawler")
    assert hasattr(HelloExtension, "create_instance")
