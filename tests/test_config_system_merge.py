#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置系统三重冗余合并 — 全方位测试
=================================
覆盖：
1. 导入正确性 — ConfigUtils/EnvConfigManager 在新旧路径可访问
2. ConfigUtils 功能 — get_config_value / has_config_prefix / merge_config_sources
3. EnvConfigManager 功能 — get_env_var / get_redis_config / get_runtime_config / get_version
4. 向后兼容性 — config_manager.py 重导出对象与原位置对象一致
5. SettingManager 集成 — 默认配置加载 / 组件合并
6. Registry — register() 不再发出 DeprecationWarning
"""

import os
import sys
import types
import unittest
import warnings
import asyncio
from typing import Any, Dict, List

# 添加项目根目录
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


# ============================================================================
# 测试组 1：导入正确性
# ============================================================================
class TestImportCorrectness(unittest.TestCase):
    """验证 ConfigUtils 和 EnvConfigManager 在所有目标路径可访问"""

    def test_configutils_from_misc(self):
        """ConfigUtils 可从 crawlo.utils.misc 导入"""
        from crawlo.utils.misc import ConfigUtils
        self.assertTrue(isinstance(ConfigUtils, type))
        self.assertEqual(ConfigUtils.__name__, 'ConfigUtils')
        self.assertTrue(hasattr(ConfigUtils, 'get_config_value'))
        self.assertTrue(hasattr(ConfigUtils, 'has_config_prefix'))
        self.assertTrue(hasattr(ConfigUtils, 'merge_config_sources'))

    def test_envconfigmanager_from_setting_manager(self):
        """EnvConfigManager 可从 crawlo.settings.setting_manager 导入"""
        from crawlo.settings.setting_manager import EnvConfigManager
        self.assertTrue(isinstance(EnvConfigManager, type))
        self.assertEqual(EnvConfigManager.__name__, 'EnvConfigManager')
        self.assertTrue(hasattr(EnvConfigManager, 'get_env_var'))
        self.assertTrue(hasattr(EnvConfigManager, 'get_redis_config'))
        self.assertTrue(hasattr(EnvConfigManager, 'get_runtime_config'))
        self.assertTrue(hasattr(EnvConfigManager, 'get_version'))

    def test_configutils_from_config_manager_emits_deprecation(self):
        """ConfigUtils 可从旧路径导入并触发 DeprecationWarning"""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            from crawlo.utils.config_manager import ConfigUtils  # noqa: F811
            self.assertTrue(isinstance(ConfigUtils, type))
            deprecations = [x for x in w if issubclass(x.category, DeprecationWarning)]
            self.assertEqual(len(deprecations), 1, "应触发 1 个 DeprecationWarning")
            self.assertIn("deprecated", str(deprecations[0].message))
            self.assertIn("crawlo.utils.misc", str(deprecations[0].message))

    def test_envconfigmanager_from_config_manager_backward_compat(self):
        """EnvConfigManager 可从旧路径导入（向后兼容，无额外警告——模块已缓存）"""
        from crawlo.utils.config_manager import EnvConfigManager
        self.assertTrue(isinstance(EnvConfigManager, type))

    def test_no_largescaleconfig_in_config_manager(self):
        """LargeScaleConfig 已从 config_manager.py 移除（死代码清理）"""
        import crawlo.utils.config_manager
        self.assertFalse(hasattr(crawlo.utils.config_manager, 'LargeScaleConfig'))
        self.assertFalse(hasattr(crawlo.utils.config_manager, 'apply_large_scale_config'))


# ============================================================================
# 测试组 2：ConfigUtils 功能
# ============================================================================
class TestConfigUtilsFunctionality(unittest.TestCase):
    """测试 ConfigUtils 三类静态方法的功能正确性"""

    @classmethod
    def setUpClass(cls):
        from crawlo.utils.misc import ConfigUtils
        cls.ConfigUtils = ConfigUtils

    # ---- get_config_value ----

    def test_get_config_value_from_dict(self):
        """从字典源获取配置值"""
        sources = [{'LOG_LEVEL': 'DEBUG'}]
        result = self.ConfigUtils.get_config_value(sources, 'LOG_LEVEL')
        self.assertEqual(result, 'DEBUG')

    def test_get_config_value_from_object(self):
        """从对象源获取配置值"""
        class MockConfig:
            LOG_LEVEL = 'WARNING'
        sources = [MockConfig()]
        result = self.ConfigUtils.get_config_value(sources, 'LOG_LEVEL')
        self.assertEqual(result, 'WARNING')

    def test_get_config_value_default_fallback(self):
        """键不存在时返回默认值"""
        sources = [{}]
        result = self.ConfigUtils.get_config_value(sources, 'MISSING_KEY', default='FALLBACK')
        self.assertEqual(result, 'FALLBACK')

    def test_get_config_value_type_int(self):
        """类型转换 — int"""
        sources = [{'CONCURRENCY': '16'}]
        result = self.ConfigUtils.get_config_value(sources, 'CONCURRENCY', value_type=int)
        self.assertIsInstance(result, int)
        self.assertEqual(result, 16)

    def test_get_config_value_type_float(self):
        """类型转换 — float"""
        sources = [{'DELAY': '0.5'}]
        result = self.ConfigUtils.get_config_value(sources, 'DELAY', value_type=float)
        self.assertIsInstance(result, float)
        self.assertEqual(result, 0.5)

    def test_get_config_value_type_bool_true(self):
        """类型转换 — bool（真值）"""
        for val in ['1', 'true', 'True', 'yes', 'YES', 'on', 'ON']:
            sources = [{'ENABLED': val}]
            result = self.ConfigUtils.get_config_value(sources, 'ENABLED', value_type=bool)
            self.assertTrue(result, f"'{val}' should be True")

    def test_get_config_value_type_bool_false(self):
        """类型转换 — bool（假值）"""
        sources = [{'ENABLED': 'false'}]
        result = self.ConfigUtils.get_config_value(sources, 'ENABLED', value_type=bool)
        self.assertFalse(result)

    def test_get_config_value_type_bool_from_int(self):
        """类型转换 — bool from int（非零为 True）"""
        sources = [{'ENABLED': 1}]
        result = self.ConfigUtils.get_config_value(sources, 'ENABLED', value_type=bool)
        self.assertTrue(result)

        sources = [{'ENABLED': 0}]
        result = self.ConfigUtils.get_config_value(sources, 'ENABLED', value_type=bool)
        self.assertFalse(result)

    def test_get_config_value_priority_order(self):
        """优先级顺序：前面的源优先于后面的源"""
        sources = [{'KEY': 'first'}, {'KEY': 'second'}]
        result = self.ConfigUtils.get_config_value(sources, 'KEY')
        self.assertEqual(result, 'first')

    def test_get_config_value_skip_none_source(self):
        """跳过 None 配置源"""
        sources = [None, {'KEY': 'valid'}]
        result = self.ConfigUtils.get_config_value(sources, 'KEY')
        self.assertEqual(result, 'valid')

    def test_get_config_value_skip_empty_source(self):
        """跳过空配置源"""
        sources = [{}, {'KEY': 'valid'}]
        result = self.ConfigUtils.get_config_value(sources, 'KEY')
        self.assertEqual(result, 'valid')

    # ---- has_config_prefix ----

    def test_has_config_prefix_from_dict(self):
        """从字典检查前缀"""
        source = {'LOG_LEVEL': 'INFO', 'LOG_FILE': 'app.log', 'OTHER': 'val'}
        self.assertTrue(self.ConfigUtils.has_config_prefix(source, 'LOG_'))
        self.assertFalse(self.ConfigUtils.has_config_prefix(source, 'NOT_EXIST_'))

    def test_has_config_prefix_from_object(self):
        """从对象检查前缀（实例属性位于 __dict__ 中）"""
        class MockConfig:
            def __init__(self):
                self.LOG_LEVEL = 'INFO'
                self.NOT_LOG = 'val'
        source = MockConfig()
        self.assertTrue(self.ConfigUtils.has_config_prefix(source, 'LOG_'))

    def test_has_config_prefix_from_class_attrs(self):
        """从对象检查前缀（类属性通过 dir() 检测——修复后可达）"""
        class MockConfig:
            LOG_LEVEL = 'INFO'
            NOT_LOG = 'val'
        source = MockConfig()
        self.assertTrue(self.ConfigUtils.has_config_prefix(source, 'LOG_'))

    def test_has_config_prefix_none_source(self):
        """None 源返回 False"""
        self.assertFalse(self.ConfigUtils.has_config_prefix(None, 'LOG_'))

    # ---- merge_config_sources ----

    def test_merge_config_sources_basic(self):
        """基本合并"""
        sources = [{'A': 1, 'B': 2}, {'C': 3}]
        result = self.ConfigUtils.merge_config_sources(sources)
        self.assertEqual(result, {'A': 1, 'B': 2, 'C': 3})

    def test_merge_config_sources_later_wins(self):
        """后面的源覆盖前面的（仅大写键）"""
        sources = [{'A': 1}, {'A': 2}]
        result = self.ConfigUtils.merge_config_sources(sources)
        self.assertEqual(result['A'], 2)

    def test_merge_config_sources_filters_lowercase(self):
        """只合并大写的配置项"""
        sources = [{'UPPER': 1, 'lower': 2}]
        result = self.ConfigUtils.merge_config_sources(sources)
        self.assertIn('UPPER', result)
        self.assertNotIn('lower', result)

    def test_merge_config_sources_skip_none(self):
        """跳过 None 源"""
        sources = [None, {'A': 1}]
        result = self.ConfigUtils.merge_config_sources(sources)
        self.assertEqual(result, {'A': 1})

    def test_merge_config_sources_object(self):
        """合并对象类型源"""
        class MockConfig:
            A = 1
            B = 2
            lower = 3
        result = self.ConfigUtils.merge_config_sources([MockConfig])
        self.assertIn('A', result)
        self.assertNotIn('lower', result)


# ============================================================================
# 测试组 3：EnvConfigManager 功能
# ============================================================================
class TestEnvConfigManagerFunctionality(unittest.TestCase):
    """测试 EnvConfigManager 四类静态方法的功能正确性"""

    @classmethod
    def setUpClass(cls):
        from crawlo.settings.setting_manager import EnvConfigManager
        cls.EnvConfigManager = EnvConfigManager

    # ---- get_env_var ----

    def test_get_env_var_existing(self):
        """获取已存在的环境变量"""
        os.environ['_CRAWLO_TEST_VAR'] = 'hello'
        try:
            result = self.EnvConfigManager.get_env_var('_CRAWLO_TEST_VAR')
            self.assertEqual(result, 'hello')
        finally:
            del os.environ['_CRAWLO_TEST_VAR']

    def test_get_env_var_default_for_missing(self):
        """不存在的环境变量返回默认值"""
        result = self.EnvConfigManager.get_env_var('_CRAWLO_NONEXISTENT_VAR', default='default_val')
        self.assertEqual(result, 'default_val')

    def test_get_env_var_type_int(self):
        """类型转换 — int"""
        os.environ['_CRAWLO_TEST_INT'] = '42'
        try:
            result = self.EnvConfigManager.get_env_var('_CRAWLO_TEST_INT', var_type=int)
            self.assertIsInstance(result, int)
            self.assertEqual(result, 42)
        finally:
            del os.environ['_CRAWLO_TEST_INT']

    def test_get_env_var_type_float(self):
        """类型转换 — float"""
        os.environ['_CRAWLO_TEST_FLOAT'] = '3.14'
        try:
            result = self.EnvConfigManager.get_env_var('_CRAWLO_TEST_FLOAT', var_type=float)
            self.assertIsInstance(result, float)
            self.assertEqual(result, 3.14)
        finally:
            del os.environ['_CRAWLO_TEST_FLOAT']

    def test_get_env_var_type_bool(self):
        """类型转换 — bool"""
        os.environ['_CRAWLO_TEST_BOOL'] = 'true'
        try:
            result = self.EnvConfigManager.get_env_var('_CRAWLO_TEST_BOOL', var_type=bool)
            self.assertTrue(result)
        finally:
            del os.environ['_CRAWLO_TEST_BOOL']

        os.environ['_CRAWLO_TEST_BOOL'] = '0'
        try:
            result = self.EnvConfigManager.get_env_var('_CRAWLO_TEST_BOOL', var_type=bool)
            self.assertFalse(result)
        finally:
            del os.environ['_CRAWLO_TEST_BOOL']

    def test_get_env_var_returns_default_on_type_error(self):
        """类型转换失败时返回默认值"""
        os.environ['_CRAWLO_TEST_BAD'] = 'not_a_number'
        try:
            result = self.EnvConfigManager.get_env_var('_CRAWLO_TEST_BAD', default=999, var_type=int)
            self.assertEqual(result, 999)
        finally:
            del os.environ['_CRAWLO_TEST_BAD']

    # ---- get_redis_config ----

    def test_get_redis_config_structure(self):
        """get_redis_config 返回正确的键结构"""
        config = self.EnvConfigManager.get_redis_config()
        self.assertIsInstance(config, dict)
        self.assertIn('REDIS_HOST', config)
        self.assertIn('REDIS_PORT', config)
        self.assertIn('REDIS_PASSWORD', config)
        self.assertIn('REDIS_DB', config)

    def test_get_redis_config_with_env_override(self):
        """get_redis_config 使用环境变量覆盖"""
        os.environ['CRAWLO_REDIS_HOST'] = '10.0.0.1'
        os.environ['CRAWLO_REDIS_PORT'] = '6380'
        try:
            config = self.EnvConfigManager.get_redis_config()
            self.assertEqual(config['REDIS_HOST'], '10.0.0.1')
            self.assertEqual(config['REDIS_PORT'], 6380)
        finally:
            del os.environ['CRAWLO_REDIS_HOST']
            del os.environ['CRAWLO_REDIS_PORT']

    # ---- get_runtime_config ----

    def test_get_runtime_config_structure(self):
        """get_runtime_config 返回正确的键结构"""
        config = self.EnvConfigManager.get_runtime_config()
        self.assertIsInstance(config, dict)
        self.assertIn('CRAWLO_MODE', config)
        self.assertIn('PROJECT_NAME', config)
        self.assertIn('CONCURRENCY', config)

    def test_get_runtime_config_defaults(self):
        """get_runtime_config 返回正确的默认值"""
        config = self.EnvConfigManager.get_runtime_config()
        self.assertEqual(config['CRAWLO_MODE'], 'standalone')
        self.assertEqual(config['PROJECT_NAME'], 'crawlo')
        self.assertEqual(config['CONCURRENCY'], 8)

    # ---- get_version ----

    def test_get_version_returns_string(self):
        """get_version 返回非空字符串"""
        version = self.EnvConfigManager.get_version()
        self.assertIsInstance(version, str)
        self.assertTrue(len(version) > 0)
        # 应该匹配语义化版本格式
        import re
        self.assertTrue(re.match(r'\d+\.\d+\.\d+', version), f"版本格式不符: {version}")


# ============================================================================
# 测试组 4：向后兼容性
# ============================================================================
class TestBackwardCompatibility(unittest.TestCase):
    """验证旧路径导入的对象与新路径相同（对象标识等价）"""

    def test_configutils_identity(self):
        """config_manager 重导出的 ConfigUtils 与 misc 中的同一个类"""
        from crawlo.utils.misc import ConfigUtils as CU_New
        from crawlo.utils.config_manager import ConfigUtils as CU_Old
        self.assertIs(CU_New, CU_Old, "旧路径和新路径必须返回同一个类对象")

    def test_envconfigmanager_identity(self):
        """config_manager 重导出的 EnvConfigManager 与 setting_manager 中的同一个类"""
        from crawlo.settings.setting_manager import EnvConfigManager as ECM_New
        from crawlo.utils.config_manager import EnvConfigManager as ECM_Old
        self.assertIs(ECM_New, ECM_Old, "旧路径和新路径必须返回同一个类对象")

    def test_configutils_methods_accessible_from_old_path(self):
        """旧路径的 ConfigUtils 方法可调用"""
        from crawlo.utils.config_manager import ConfigUtils
        result = ConfigUtils.get_config_value([{'A': 'hello'}], 'A')
        self.assertEqual(result, 'hello')

    def test_envconfigmanager_methods_accessible_from_old_path(self):
        """旧路径的 EnvConfigManager 方法可调用"""
        from crawlo.utils.config_manager import EnvConfigManager
        version = EnvConfigManager.get_version()
        self.assertIsInstance(version, str)


# ============================================================================
# 测试组 5：SettingManager 集成
# ============================================================================
class TestSettingManagerIntegration(unittest.TestCase):
    """验证 SettingManager 正确加载默认配置并融合 EnvConfigManager 值"""

    def test_default_settings_loaded(self):
        """SettingManager 加载默认配置"""
        from crawlo.settings.setting_manager import SettingManager
        settings = SettingManager()
        # 核心配置项存在
        self.assertIsNotNone(settings.get('PROJECT_NAME'))
        self.assertIsNotNone(settings.get('CONCURRENCY'))
        self.assertIsNotNone(settings.get('MIDDLEWARES'))

    def test_project_name_from_env(self):
        """PROJECT_NAME 来源于 EnvConfigManager 环境变量"""
        from crawlo.settings.setting_manager import EnvConfigManager
        # default_settings 模块顶层已执行 get_runtime_config()，不再 reload
        from crawlo.settings import default_settings
        expected = EnvConfigManager.get_env_var('CRAWLO_PROJECT_NAME', 'crawlo', str)
        self.assertEqual(default_settings.PROJECT_NAME, expected)

    def test_middleware_merge_with_user_config(self):
        """中间件合并：用户配置追加到默认配置"""
        from crawlo.settings.setting_manager import SettingManager
        user_config = {
            'MIDDLEWARES': ['myproject.middlewares.CustomMiddleware']
        }
        settings = SettingManager(user_config)
        middlewares = settings.get('MIDDLEWARES')
        self.assertIn('crawlo.middleware.request_ignore.RequestIgnoreMiddleware', middlewares)
        self.assertIn('myproject.middlewares.CustomMiddleware', middlewares)

    def test_pipeline_merge_with_dedup_first(self):
        """管道合并：去重管道存在并有序"""
        from crawlo.settings.setting_manager import SettingManager
        settings = SettingManager()
        pipelines = settings.get('PIPELINES')
        # 去重管道必须存在
        dedup = settings.get('DEFAULT_DEDUP_PIPELINE', 'crawlo.pipelines.dedup.memory.MemoryDedupPipeline')
        self.assertIn(dedup, pipelines, "去重管道必须存在于 PIPELINES 中")

    def test_setting_manager_get_int_bool_float(self):
        """SettingManager 类型化获取方法正常"""
        from crawlo.settings.setting_manager import SettingManager
        settings = SettingManager({'TEST_INT': '42', 'TEST_BOOL': 'true', 'TEST_FLOAT': '3.14'})
        self.assertEqual(settings.get_int('TEST_INT'), 42)
        self.assertTrue(settings.get_bool('TEST_BOOL'))
        self.assertAlmostEqual(settings.get_float('TEST_FLOAT'), 3.14)

    def test_setting_manager_sentinel_none(self):
        """显式设置 None 与未设置的区别（哨兵值）"""
        from crawlo.settings.setting_manager import SettingManager
        settings = SettingManager({'EXPLICIT_NONE': None})
        self.assertIsNone(settings.get('EXPLICIT_NONE'))
        self.assertEqual(settings.get('UNSET_KEY', 'default'), 'default')


# ============================================================================
# 测试组 6：Registry 无 DeprecationWarning
# ============================================================================
class TestRegistryNoDeprecationWarning(unittest.TestCase):
    """验证 register() 不再发出 DeprecationWarning"""

    def test_register_no_warning(self):
        """register() 不发出任何警告"""
        from crawlo.factories import ComponentRegistry, ComponentSpec

        def factory(**kwargs):
            return object()

        spec = ComponentSpec(name="test_item", component_type=object, factory_func=factory)
        registry = ComponentRegistry()

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")  # 捕获所有警告
            registry.register(spec)
            deprecation_warnings = [x for x in w if issubclass(x.category, DeprecationWarning)]
            self.assertEqual(len(deprecation_warnings), 0,
                             "register() 不应发出 DeprecationWarning")

    def test_register_async_still_works(self):
        """register_async() 仍然可用"""
        from crawlo.factories import ComponentRegistry, ComponentSpec

        def factory(**kwargs):
            return object()

        spec = ComponentSpec(name="async_item", component_type=object, factory_func=factory)
        registry = ComponentRegistry()

        async def do_register():
            await registry.register_async(spec)
            return "async_item" in registry.list_components()

        result = asyncio.run(do_register())
        self.assertTrue(result)

    def test_register_stores_spec_correctly(self):
        """register() 正确存储规范"""
        from crawlo.factories import ComponentRegistry, ComponentSpec

        def factory(**kwargs):
            return object()

        spec = ComponentSpec(name="stored_item", component_type=object, factory_func=factory)
        registry = ComponentRegistry()
        registry.register(spec)

        self.assertIn("stored_item", registry.list_components())
        retrieved = registry.get_spec("stored_item")
        self.assertEqual(retrieved.name, "stored_item")
        self.assertIs(retrieved.factory_func, factory)


# ============================================================================
# 测试组 7：跨模块 import 验证（集成）
# ============================================================================
class TestCrossModuleImportVerification(unittest.TestCase):
    """验证各消费模块的 import 路径已正确迁移"""

    def test_built_in_imports_configutils_from_misc(self):
        """built_in.py 从 crawlo.utils.misc 导入 ConfigUtils"""
        import crawlo.initialization.built_in as bu
        # 检查模块源码中的 import 语句（不实际运行，避免上下文依赖）
        source = open(bu.__file__, encoding='utf-8').read()
        self.assertNotIn('from crawlo.utils.config_manager import ConfigUtils', source)
        self.assertIn('from crawlo.utils.misc import ConfigUtils', source)

    def test_help_imports_envconfigmanager_from_setting_manager(self):
        """help.py 从 crawlo.settings.setting_manager 导入 EnvConfigManager"""
        import crawlo.commands.help as hp
        source = open(hp.__file__, encoding='utf-8').read()
        self.assertNotIn('from crawlo.utils.config_manager import EnvConfigManager', source)
        self.assertIn('from crawlo.settings.setting_manager import EnvConfigManager', source)

    def test_default_settings_imports_from_setting_manager(self):
        """default_settings.py 从 crawlo.settings.setting_manager 导入 EnvConfigManager"""
        import crawlo.settings.default_settings as ds
        source = open(ds.__file__, encoding='utf-8').read()
        self.assertNotIn('from crawlo.utils.config_manager import EnvConfigManager', source)
        self.assertIn('from crawlo.settings.setting_manager import EnvConfigManager', source)

    def test_cli_imports_from_setting_manager(self):
        """cli.py 从 crawlo.settings.setting_manager 导入 EnvConfigManager"""
        import crawlo.cli as cli
        source = open(cli.__file__, encoding='utf-8').read()
        self.assertNotIn('from crawlo.utils.config_manager import EnvConfigManager', source)
        self.assertIn('from crawlo.settings.setting_manager import EnvConfigManager', source)


# ============================================================================
# 运行入口
# ============================================================================
if __name__ == '__main__':
    unittest.main(verbosity=2)
