#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Deep validation tests for RUN_MODE logic
"""
import pytest
from unittest.mock import patch, MagicMock
from crawlo.config import CrawloConfig, BASE_CONFIG, MODE_CONFIG_MAP
from crawlo.settings.setting_manager import SettingManager


class TestModeConfigConsistency:
    """Test mode configuration consistency"""

    def test_standalone_mode_config(self):
        """Verify standalone mode configuration is correct"""
        config = CrawloConfig.standalone(project_name='test')
        settings = config.to_dict()
        
        assert settings['RUN_MODE'] == 'standalone'
        assert settings['QUEUE_TYPE'] == 'memory'
        assert 'MemoryFilter' in settings['FILTER_CLASS']
        assert 'MemoryDedupPipeline' in settings['DEFAULT_DEDUP_PIPELINE']
        assert settings['CONCURRENCY'] == 8  # From BASE_CONFIG

    def test_distributed_mode_config(self):
        """Verify distributed mode configuration is correct"""
        config = CrawloConfig.distributed(
            redis_host='127.0.0.1',
            redis_port=6379,
            project_name='test'
        )
        settings = config.to_dict()
        
        assert settings['RUN_MODE'] == 'distributed'
        assert settings['QUEUE_TYPE'] == 'redis'
        assert 'AioRedisFilter' in settings['FILTER_CLASS']
        assert 'RedisDedupPipeline' in settings['DEFAULT_DEDUP_PIPELINE']
        assert settings['CONCURRENCY'] == 16  # Overridden in distributed mode
        assert settings['REDIS_HOST'] == '127.0.0.1'
        assert settings['REDIS_PORT'] == 6379

    def test_auto_mode_config(self):
        """Verify auto mode configuration is correct"""
        config = CrawloConfig.auto(project_name='test')
        settings = config.to_dict()
        
        assert settings['RUN_MODE'] == 'auto'
        assert settings['QUEUE_TYPE'] == 'auto'
        # Auto mode should use standalone as base (will detect at runtime)
        assert settings['CONCURRENCY'] == 8


class TestModeSettingsLogic:
    """Test _get_mode_settings function logic"""

    def test_standalone_mode_returns_correct_config(self):
        """Test standalone mode returns correct settings"""
        from crawlo.project import _get_mode_settings
        
        settings = SettingManager()
        settings.set('PROJECT_NAME', 'test_project')
        
        mode_settings = _get_mode_settings(settings, 'standalone')
        
        assert mode_settings['RUN_MODE'] == 'standalone'
        assert mode_settings['QUEUE_TYPE'] == 'memory'

    def test_distributed_mode_returns_correct_config(self):
        """Test distributed mode returns correct settings"""
        from crawlo.project import _get_mode_settings
        
        settings = SettingManager()
        settings.set('PROJECT_NAME', 'test_project')
        
        mode_settings = _get_mode_settings(settings, 'distributed')
        
        assert mode_settings['RUN_MODE'] == 'distributed'
        assert mode_settings['QUEUE_TYPE'] == 'redis'

    def test_auto_mode_returns_correct_config(self):
        """Test auto mode returns correct settings"""
        from crawlo.project import _get_mode_settings
        
        settings = SettingManager()
        settings.set('PROJECT_NAME', 'test_project')
        
        mode_settings = _get_mode_settings(settings, 'auto')
        
        assert mode_settings['RUN_MODE'] == 'auto'
        assert mode_settings['QUEUE_TYPE'] == 'auto'

    def test_unknown_mode_defaults_to_standalone(self):
        """Test unknown mode defaults to standalone"""
        from crawlo.project import _get_mode_settings
        
        settings = SettingManager()
        settings.set('PROJECT_NAME', 'test_project')
        
        mode_settings = _get_mode_settings(settings, 'unknown_mode')
        
        # Should default to standalone
        assert mode_settings['RUN_MODE'] == 'standalone'
        assert mode_settings['QUEUE_TYPE'] == 'memory'


class TestUserQueueTypePreservation:
    """Test user QUEUE_TYPE preservation logic in standalone mode"""

    def test_standalone_ignores_user_queue_type(self):
        """Test standalone mode ignores user's QUEUE_TYPE (uses mode default)"""
        from crawlo.project import _get_mode_settings
        
        settings = SettingManager()
        settings.set('PROJECT_NAME', 'test')
        settings.set('QUEUE_TYPE', 'redis')  # User wants redis
        
        mode_settings = _get_mode_settings(settings, 'standalone')
        
        # Should use standalone default (memory), not user's setting
        assert mode_settings['QUEUE_TYPE'] == 'memory'
        assert 'MemoryFilter' in mode_settings['FILTER_CLASS']

    def test_standalone_ignores_user_memory_queue(self):
        """Test standalone mode uses memory (same as mode default)"""
        from crawlo.project import _get_mode_settings
        
        settings = SettingManager()
        settings.set('PROJECT_NAME', 'test')
        settings.set('QUEUE_TYPE', 'memory')  # Same as standalone default
        
        mode_settings = _get_mode_settings(settings, 'standalone')
        
        # Should use default memory
        assert mode_settings['QUEUE_TYPE'] == 'memory'
        assert 'MemoryFilter' in mode_settings['FILTER_CLASS']

    def test_distributed_overrides_user_queue_type(self):
        """Test distributed mode overrides user's QUEUE_TYPE"""
        from crawlo.project import _get_mode_settings
        
        settings = SettingManager()
        settings.set('PROJECT_NAME', 'test')
        settings.set('QUEUE_TYPE', 'memory')  # User wants memory
        
        mode_settings = _get_mode_settings(settings, 'distributed')
        
        # Distributed mode should force redis
        assert mode_settings['QUEUE_TYPE'] == 'redis'
        assert 'AioRedisFilter' in mode_settings['FILTER_CLASS']

    def test_auto_mode_ignores_user_queue_type(self):
        """Test auto mode ignores user's QUEUE_TYPE"""
        from crawlo.project import _get_mode_settings
        
        settings = SettingManager()
        settings.set('PROJECT_NAME', 'test')
        settings.set('QUEUE_TYPE', 'redis')  # User wants redis
        
        mode_settings = _get_mode_settings(settings, 'auto')
        
        # Auto mode should use 'auto'
        assert mode_settings['QUEUE_TYPE'] == 'auto'


class TestQueueRelatedSettingsUpdate:
    """Test _update_queue_related_settings logic"""

    def test_redis_queue_updates_filter_and_pipeline(self):
        """Test redis queue updates related settings correctly"""
        from crawlo.project import _update_queue_related_settings

        mode_settings = {}
        settings = SettingManager()

        _update_queue_related_settings(mode_settings, 'redis', settings)

        assert mode_settings['FILTER_CLASS'] == 'crawlo.filters.AioRedisFilter'
        assert mode_settings['DEFAULT_DEDUP_PIPELINE'] == 'crawlo.pipelines.RedisDedupPipeline'

    def test_auto_queue_preserves_user_settings(self):
        """Test auto queue preserves user's settings"""
        from crawlo.project import _update_queue_related_settings

        mode_settings = {}
        settings = SettingManager()
        settings.set('FILTER_CLASS', 'custom.Filter')
        settings.set('DEFAULT_DEDUP_PIPELINE', 'custom.Pipeline')

        _update_queue_related_settings(mode_settings, 'auto', settings)

        # Should preserve user's custom settings
        assert mode_settings['FILTER_CLASS'] == 'custom.Filter'
        assert mode_settings['DEFAULT_DEDUP_PIPELINE'] == 'custom.Pipeline'

    def test_unknown_queue_type_no_update(self):
        """Test unknown queue type doesn't update settings"""
        from crawlo.project import _update_queue_related_settings
        
        mode_settings = {'EXISTING': 'value'}
        settings = SettingManager()
        
        _update_queue_related_settings(mode_settings, 'unknown', settings)
        
        # Should not add new keys
        assert mode_settings == {'EXISTING': 'value'}


class TestConfigurationPriority:
    """Test configuration priority logic in _load_project_settings"""

    def test_custom_settings_highest_priority(self):
        """Test custom_settings has highest priority"""
        # This is validated in the actual _load_project_settings function
        # We verify the logic exists
        from crawlo.project import _load_project_settings
        import inspect
        
        source = inspect.getsource(_load_project_settings)
        
        # Should apply custom_settings last
        assert 'if custom_settings:' in source
        assert 'settings.update_attributes(custom_settings)' in source

    def test_run_mode_priority_keys_override(self):
        """Test RUN_MODE priority keys override user settings"""
        from crawlo.project import _load_project_settings
        import inspect
        
        source = inspect.getsource(_load_project_settings)
        
        # Should have priority_keys logic
        assert "priority_keys = ['QUEUE_TYPE', 'FILTER_CLASS', 'DEFAULT_DEDUP_PIPELINE']" in source
        assert 'if key in priority_keys or key not in settings.attributes:' in source

    def test_mode_applied_after_settings_loaded(self):
        """Test RUN_MODE config is applied after settings.py is loaded"""
        # Verify the order in _load_project_settings
        from crawlo.project import _load_project_settings
        import inspect
        
        source = inspect.getsource(_load_project_settings)
        
        # Order should be:
        # 1. settings.set_settings() - load settings.py
        # 2. _get_mode_settings() - apply RUN_MODE
        # 3. custom_settings update - highest priority
        
        set_settings_pos = source.find('settings.set_settings')
        get_mode_settings_pos = source.find('_get_mode_settings')
        custom_settings_pos = source.find('if custom_settings:')
        
        assert set_settings_pos < get_mode_settings_pos < custom_settings_pos


class TestModeTransitionLogic:
    """Test mode transition and switching logic"""

    def test_standalone_to_distributed_transition(self):
        """Test transitioning from standalone to distributed"""
        # User changes RUN_MODE from standalone to distributed
        settings = SettingManager()
        settings.set('PROJECT_NAME', 'test')
        settings.set('RUN_MODE', 'standalone')
        settings.set('QUEUE_TYPE', 'memory')
        
        # Change to distributed
        from crawlo.project import _get_mode_settings
        mode_settings = _get_mode_settings(settings, 'distributed')
        
        # Should use distributed config
        assert mode_settings['QUEUE_TYPE'] == 'redis'
        assert mode_settings['CONCURRENCY'] == 16

    def test_distributed_to_standalone_uses_mode_default(self):
        """Test transitioning from distributed to standalone uses mode default"""
        settings = SettingManager()
        settings.set('PROJECT_NAME', 'test')
        settings.set('RUN_MODE', 'distributed')
        settings.set('QUEUE_TYPE', 'redis')  # Was using redis
        
        # Change to standalone
        from crawlo.project import _get_mode_settings
        mode_settings = _get_mode_settings(settings, 'standalone')
        
        # Should use standalone default (memory)
        assert mode_settings['QUEUE_TYPE'] == 'memory'

    def test_auto_mode_runtime_detection(self):
        """Test auto mode sets up for runtime detection"""
        config = CrawloConfig.auto(project_name='test')
        settings = config.to_dict()
        
        # Auto mode should set QUEUE_TYPE to 'auto'
        assert settings['QUEUE_TYPE'] == 'auto'
        assert settings['RUN_MODE'] == 'auto'
        
        # Runtime detection will happen later in the framework
        # The config just needs to signal "auto" mode


class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_empty_project_name_rejected(self):
        """Test that empty project name is rejected by validator"""
        # This is expected behavior - validator should reject empty names
        with pytest.raises(ValueError, match="PROJECT_NAME 必须是非空字符串"):
            CrawloConfig.standalone(project_name='')

    def test_special_characters_in_project_name(self):
        """Test with special characters in project name"""
        config = CrawloConfig.standalone(project_name='test-project_123')
        settings = config.to_dict()
        
        assert settings['PROJECT_NAME'] == 'test-project_123'

    def test_mode_config_map_consistency(self):
        """Test MODE_CONFIG_MAP is consistent"""
        # All modes should have required keys
        required_keys = ['RUN_MODE', 'QUEUE_TYPE', 'FILTER_CLASS', 'DEFAULT_DEDUP_PIPELINE']
        
        for mode_name, mode_config in MODE_CONFIG_MAP.items():
            for key in required_keys:
                assert key in mode_config, f"{mode_name} missing {key}"

    def test_base_config_not_modified(self):
        """Test BASE_CONFIG is not modified by mode creation"""
        original_concurrency = BASE_CONFIG['CONCURRENCY']
        
        # Create distributed config (which has different CONCURRENCY)
        config = CrawloConfig.distributed(project_name='test')
        
        # BASE_CONFIG should not be modified
        assert BASE_CONFIG['CONCURRENCY'] == original_concurrency

    def test_kwargs_override_in_modes(self):
        """Test kwargs can override mode settings"""
        config = CrawloConfig.standalone(
            project_name='test',
            concurrency=20,  # Override default
            log_level='DEBUG'
        )
        settings = config.to_dict()
        
        assert settings['CONCURRENCY'] == 20
        assert settings['LOG_LEVEL'] == 'DEBUG'


class TestIntegrationWithSettingsManager:
    """Test integration with SettingManager"""

    def test_mode_settings_merge_with_existing(self):
        """Test mode settings merge correctly with existing settings"""
        from crawlo.project import _get_mode_settings
        
        settings = SettingManager()
        settings.set('PROJECT_NAME', 'test')
        settings.set('EXISTING_KEY', 'existing_value')
        
        mode_settings = _get_mode_settings(settings, 'standalone')
        
        # Mode settings should not affect existing settings
        assert settings.get('EXISTING_KEY') == 'existing_value'
        # But mode_settings should have correct values
        assert mode_settings['RUN_MODE'] == 'standalone'

    def test_settings_manager_default_queue_type(self):
        """Test SettingManager.get with QUEUE_TYPE default from default_settings"""
        # Note: default_settings.py sets QUEUE_TYPE = 'auto'
        # This is the framework default, not the mode default
        settings = SettingManager()
        
        # Should return 'auto' from default_settings.py
        assert settings.get('QUEUE_TYPE', 'memory') == 'auto'


class TestLogicalCorrectness:
    """Test overall logical correctness"""

    def test_standalone_mode_is_truly_standalone(self):
        """Verify standalone mode requires no external dependencies"""
        config = CrawloConfig.standalone(project_name='test')
        settings = config.to_dict()
        
        # Should use memory-based components
        assert 'memory' in settings['QUEUE_TYPE']
        assert 'memory' in settings['FILTER_CLASS'].lower()
        assert 'memory' in settings['DEFAULT_DEDUP_PIPELINE'].lower()
        
        # Should not require Redis
        assert 'REDIS_HOST' not in settings or settings.get('REDIS_HOST') is None

    def test_distributed_mode_requires_redis(self):
        """Verify distributed mode configures Redis"""
        config = CrawloConfig.distributed(project_name='test')
        settings = config.to_dict()
        
        # Should use Redis-based components
        assert settings['QUEUE_TYPE'] == 'redis'
        assert 'redis' in settings['FILTER_CLASS'].lower() or 'aioredis' in settings['FILTER_CLASS'].lower()
        assert 'redis' in settings['DEFAULT_DEDUP_PIPELINE'].lower()
        
        # Should have Redis configuration
        assert 'REDIS_HOST' in settings
        assert 'REDIS_URL' in settings

    def test_auto_mode_is_flexible(self):
        """Verify auto mode is flexible for runtime detection"""
        config = CrawloConfig.auto(project_name='test')
        settings = config.to_dict()
        
        # Should signal "auto" for runtime detection
        assert settings['QUEUE_TYPE'] == 'auto'
        assert settings['RUN_MODE'] == 'auto'
        
        # Should use standalone as base (safe default)
        assert settings['CONCURRENCY'] == 8

    def test_mode_switching_is_consistent(self):
        """Test that mode switching produces consistent results"""
        from crawlo.project import _get_mode_settings
        
        settings = SettingManager()
        settings.set('PROJECT_NAME', 'test')
        
        # Get config for each mode
        standalone = _get_mode_settings(settings, 'standalone')
        distributed = _get_mode_settings(settings, 'distributed')
        auto = _get_mode_settings(settings, 'auto')
        
        # Each mode should have distinct QUEUE_TYPE
        assert standalone['QUEUE_TYPE'] == 'memory'
        assert distributed['QUEUE_TYPE'] == 'redis'
        assert auto['QUEUE_TYPE'] == 'auto'
        
        # Each mode should set correct RUN_MODE
        assert standalone['RUN_MODE'] == 'standalone'
        assert distributed['RUN_MODE'] == 'distributed'
        assert auto['RUN_MODE'] == 'auto'


class TestPotentialIssues:
    """Test for potential logical issues"""

    def test_user_queue_type_logic_removed(self):
        """Verify user QUEUE_TYPE preservation logic has been removed"""
        from crawlo.project import _get_mode_settings
        import inspect
        
        source = inspect.getsource(_get_mode_settings)
        
        # Should NOT check run_mode == 'standalone' for preserving QUEUE_TYPE
        assert "run_mode == 'standalone'" not in source
        assert "user_queue_type" not in source

    def test_priority_keys_are_comprehensive(self):
        """Test priority_keys include all necessary configuration keys"""
        from crawlo.project import _load_project_settings
        import inspect
        
        source = inspect.getsource(_load_project_settings)
        
        # Should include queue-related keys
        assert 'QUEUE_TYPE' in source
        assert 'FILTER_CLASS' in source
        assert 'DEFAULT_DEDUP_PIPELINE' in source
        
        # These are the keys that must be consistent across mode switching

    def test_no_circular_dependency_in_mode_settings(self):
        """Test no circular dependency in mode settings logic"""
        # _get_mode_settings imports CrawloConfig
        # CrawloConfig should not import from project
        from crawlo.config import CrawloConfig
        import inspect
        
        config_source = inspect.getsource(CrawloConfig)
        
        # Should not import from crawlo.project
        assert 'from crawlo.project' not in config_source
        assert 'import crawlo.project' not in config_source
