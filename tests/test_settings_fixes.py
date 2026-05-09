#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试 Settings 模块修复

验证 P1 和 P2 问题是否已正确修复。
"""
import pytest
from unittest.mock import Mock, patch, mock_open
from crawlo.settings.setting_manager import (
    SettingManager,
    EnvConfigManager,
    normalize_component_config,
    merge_component_configs,
)


class TestDedupPipelinePriority:
    """测试去重管道优先级修复"""
    
    def test_dedup_pipeline_default_priority(self):
        """测试默认情况下优先级计算"""
        settings = SettingManager({
            'DEFAULT_DEDUP_PIPELINE': 'crawlo.pipelines.memory_dedup_pipeline.MemoryDedupPipeline',
            'PIPELINES': {
                'crawlo.pipelines.console_pipeline.ConsolePipeline': 300,
            }
        })
        
        pipelines = settings.attributes['PIPELINES']
        dedup_priority = pipelines['crawlo.pipelines.memory_dedup_pipeline.MemoryDedupPipeline']
        
        # 验证去重管道优先级为 200 (300 - 100)
        assert dedup_priority == 200
    
    def test_dedup_pipeline_with_empty_pipelines(self):
        """测试空管道列表时的默认优先级"""
        settings = SettingManager({
            'DEFAULT_DEDUP_PIPELINE': 'crawlo.pipelines.memory_dedup_pipeline.MemoryDedupPipeline',
            'PIPELINES': {}  # 会被默认配置覆盖
        })
        
        pipelines = settings.attributes['PIPELINES']
        dedup_priority = pipelines['crawlo.pipelines.memory_dedup_pipeline.MemoryDedupPipeline']
        
        # 默认 PIPELINES 有 ConsolePipeline: 100
        # 去重管道优先级 = 100 - 100 = 0，但 max(1, 0) = 1
        assert dedup_priority == 1
    
    def test_dedup_pipeline_with_low_priority(self):
        """测试低优先级管道时的计算"""
        settings = SettingManager({
            'DEFAULT_DEDUP_PIPELINE': 'crawlo.pipelines.memory_dedup_pipeline.MemoryDedupPipeline',
            'PIPELINES': {
                'crawlo.pipelines.console_pipeline.ConsolePipeline': 50,
            }
        })
        
        pipelines = settings.attributes['PIPELINES']
        dedup_priority = pipelines['crawlo.pipelines.memory_dedup_pipeline.MemoryDedupPipeline']
        
        # 验证使用 max(1, 50 - 100) = 1
        assert dedup_priority == 1


class TestGetDefaultValue:
    """测试 get() 默认值语义改进"""
    
    def test_get_without_default_raises_keyerror(self):
        """测试不提供 default 时抛出 KeyError"""
        settings = SettingManager()
        
        with pytest.raises(KeyError, match="Configuration key 'NONEXISTENT' not found"):
            settings.get('NONEXISTENT')
    
    def test_get_with_default_returns_default(self):
        """测试提供 default 时返回默认值"""
        settings = SettingManager()
        
        result = settings.get('NONEXISTENT', 'default_value')
        assert result == 'default_value'
    
    def test_get_with_none_returns_none(self):
        """测试键存在但值为 None 时返回 None"""
        settings = SettingManager({'KEY': None})
        
        result = settings.get('KEY', 'default')
        assert result is None
    
    def test_get_existing_key_returns_value(self):
        """测试键存在时返回值"""
        settings = SettingManager({'KEY': 'value'})
        
        result = settings.get('KEY', 'default')
        assert result == 'value'
    
    def test_get_int_with_default(self):
        """测试 get_int 使用默认值"""
        settings = SettingManager()
        
        result = settings.get_int('NONEXISTENT', 42)
        assert result == 42
    
    def test_get_bool_with_default(self):
        """测试 get_bool 使用默认值"""
        settings = SettingManager()
        
        result = settings.get_bool('NONEXISTENT', True)
        assert result is True
    
    def test_get_list_with_default(self):
        """测试 get_list 使用默认值"""
        settings = SettingManager()
        
        result = settings.get_list('NONEXISTENT', ['a', 'b'])
        assert result == ['a', 'b']
    
    def test_get_dict_with_default(self):
        """测试 get_dict 使用默认值"""
        settings = SettingManager()
        
        result = settings.get_dict('NONEXISTENT', {'key': 'value'})
        assert result == {'key': 'value'}


class TestNormalizeComponentConfig:
    """测试 normalize_component_config 注释清理"""
    
    def test_dict_config_with_comment_in_value(self):
        """测试字典配置中值的注释清理"""
        config = {
            'middleware1': 100,
            'middleware2': 'value with # comment',
        }
        
        result = normalize_component_config(config)
        
        assert result['middleware1'] == 100
        assert result['middleware2'] == 'value with'
    
    def test_dict_config_with_comment_key(self):
        """测试字典配置中注释键的过滤"""
        config = {
            '# This is a comment': 100,
            'middleware1': 200,
        }
        
        result = normalize_component_config(config)
        
        assert '# This is a comment' not in result
        assert result['middleware1'] == 200
    
    def test_list_config_with_comment_items(self):
        """测试列表配置中注释项的过滤"""
        config = [
            'middleware1',
            '# This is a comment',
            'middleware2',
        ]
        
        result = normalize_component_config(config)
        
        assert 'middleware1' in result
        assert '# This is a comment' not in result
        assert 'middleware2' in result


class TestProcessDynamicConfig:
    """测试 _process_dynamic_config 硬编码路径修复"""
    
    def test_log_file_with_custom_log_dir(self):
        """测试自定义 LOG_DIR"""
        # 先创建 SettingManager，然后修改配置
        settings = SettingManager()
        
        # 删除 LOG_FILE，使其为 None
        if 'LOG_FILE' in settings.attributes:
            del settings.attributes['LOG_FILE']
        
        # 修改 LOG_DIR 和 PROJECT_NAME
        settings.set('LOG_DIR', 'custom_logs')
        settings.set('PROJECT_NAME', 'test_project')
        
        # 重新处理动态配置
        settings._process_dynamic_config()
        
        # _process_dynamic_config 会使用 LOG_DIR 和 PROJECT_NAME
        assert settings.get('LOG_FILE') == 'custom_logs/test_project.log'
    
    def test_log_file_with_default_log_dir(self):
        """测试默认 LOG_DIR"""
        settings = SettingManager()
        
        # 删除 LOG_FILE
        if 'LOG_FILE' in settings.attributes:
            del settings.attributes['LOG_FILE']
        
        # 修改 PROJECT_NAME
        settings.set('PROJECT_NAME', 'test_project')
        settings._process_dynamic_config()
        
        assert settings.get('LOG_FILE') == 'logs/test_project.log'
    
    def test_log_file_not_overridden_if_set(self):
        """测试如果已设置 LOG_FILE 则不覆盖"""
        settings = SettingManager({
            'LOG_FILE': 'custom/path.log',
        })
        
        assert settings.get('LOG_FILE') == 'custom/path.log'


class TestVersionCache:
    """测试 get_version() 缓存"""
    
    def test_version_is_cached(self):
        """测试版本号被缓存"""
        # 清除缓存
        EnvConfigManager._version_cache = None
        
        # 第一次调用
        version1 = EnvConfigManager.get_version()
        
        # 第二次调用
        version2 = EnvConfigManager.get_version()
        
        # 验证两次返回相同值
        assert version1 == version2
        # 验证缓存被设置
        assert EnvConfigManager._version_cache == version1
    
    def test_version_cache_persists(self):
        """测试缓存在多次调用中保持"""
        EnvConfigManager._version_cache = None
        
        # 调用 10 次
        for _ in range(10):
            version = EnvConfigManager.get_version()
            assert EnvConfigManager._version_cache == version


class TestComponentDisable:
    """测试组件禁用机制"""
    
    def test_disable_component_with_none(self):
        """测试使用 None 禁用组件"""
        default = {
            'middleware1': 100,
            'middleware2': 200,
        }
        user = {
            'middleware1': None,
        }
        
        result = merge_component_configs(default, user)
        
        assert 'middleware1' not in result
        assert 'middleware2' in result
    
    def test_disable_component_with_zero(self):
        """测试使用 0 禁用组件"""
        default = {
            'middleware1': 100,
            'middleware2': 200,
        }
        user = {
            'middleware1': 0,
        }
        
        result = merge_component_configs(default, user)
        
        assert 'middleware1' not in result
        assert 'middleware2' in result
    
    def test_override_component_priority(self):
        """测试覆盖组件优先级"""
        default = {
            'middleware1': 100,
            'middleware2': 200,
        }
        user = {
            'middleware1': 500,
        }
        
        result = merge_component_configs(default, user)
        
        assert result['middleware1'] == 500
        assert result['middleware2'] == 200
    
    def test_add_new_component(self):
        """测试添加新组件"""
        default = {
            'middleware1': 100,
        }
        user = {
            'middleware2': 200,
        }
        
        result = merge_component_configs(default, user)
        
        assert result['middleware1'] == 100
        assert result['middleware2'] == 200
    
    def test_disable_via_setting_manager(self):
        """测试通过 SettingManager 禁用组件"""
        settings = SettingManager({
            'MIDDLEWARES': {
                'crawlo.middleware.retry.RetryMiddleware': 600,
            }
        })
        
        # 用户配置禁用某个中间件
        settings.update({
            'MIDDLEWARES': {
                'crawlo.middleware.retry.RetryMiddleware': None,
            }
        })
        
        middlewares = settings.attributes['MIDDLEWARES']
        assert 'crawlo.middleware.retry.RetryMiddleware' not in middlewares


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
