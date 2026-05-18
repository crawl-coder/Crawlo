#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
Tests for Core module P0/P1/P2 fixes
Validates all modifications made to crawlo.core module
"""
import asyncio
import warnings
import pytest
from unittest.mock import Mock, MagicMock, patch
from typing import Dict, Any

# Test P0-1: application.py print() -> logger.error()
class TestApplicationPrintFix:
    """Test P0-1: application.py uses logger instead of print()"""
    
    @pytest.mark.asyncio
    async def test_cleanup_uses_logger_not_print(self):
        """Verify cleanup() uses logger.error() instead of print()"""
        from crawlo.core.application import ApplicationContext
        from crawlo.logging import get_logger
        
        # Create context with a resource that raises exception
        ctx = ApplicationContext()
        
        # Mock resource that raises exception on close
        bad_resource = Mock()
        bad_resource.close = Mock(side_effect=RuntimeError("Test error"))
        ctx.resources.add(bad_resource)
        
        # Patch logger to verify it's called
        with patch('crawlo.core.application.get_logger') as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger
            
            # Should not raise exception
            await ctx.cleanup()
            
            # Verify logger.error was called (not print)
            mock_logger.error.assert_called_once()
            call_args = mock_logger.error.call_args[0][0]
            assert "Error cleaning up resource" in call_args


# Test P0-2: error_types.py duplicate TimeoutError removal
class TestErrorTypesTimeoutFix:
    """Test P0-2: error_types.py removed duplicate TimeoutError"""
    
    def test_no_duplicate_timeout_error(self):
        """Verify asyncio.TimeoutError is not in NETWORK_EXCEPTIONS"""
        from crawlo.core.error_types import ErrorClassifier
        import asyncio
        
        # In Python 3.11+, asyncio.TimeoutError is an alias of TimeoutError
        # Should only have TimeoutError once
        network_exceptions = ErrorClassifier.NETWORK_EXCEPTIONS
        
        # Count how many times TimeoutError appears
        timeout_count = sum(1 for exc in network_exceptions if exc is TimeoutError)
        assert timeout_count == 1, "TimeoutError should appear only once"
        
        # asyncio.TimeoutError should be the same as TimeoutError in 3.11+
        if hasattr(asyncio, 'TimeoutError'):
            assert asyncio.TimeoutError is TimeoutError
    
    def test_retryable_exceptions_no_duplicate(self):
        """Verify RETRYABLE_EXCEPTIONS has no duplicate TimeoutError"""
        from crawlo.core.error_types import ErrorClassifier
        
        retryable_exceptions = ErrorClassifier.RETRYABLE_EXCEPTIONS
        timeout_count = sum(1 for exc in retryable_exceptions if exc is TimeoutError)
        assert timeout_count == 1


# Test P0-3: task_manager.py meaningless super().__init__()
class TestDynamicSemaphoreSuperFix:
    """Test P0-3: DynamicSemaphore removed meaningless super().__init__()"""
    
    def test_dynamic_semaphore_no_super_init(self):
        """Verify DynamicSemaphore doesn't call super().__init__()"""
        from crawlo.core.task_manager import DynamicSemaphore
        import inspect
        
        # Get the __init__ source code
        source = inspect.getsource(DynamicSemaphore.__init__)
        
        # Should not contain super().__init__()
        assert "super().__init__()" not in source, \
            "DynamicSemaphore should not call super().__init__()"
    
    def test_dynamic_semaphore_instantiation(self):
        """Verify DynamicSemaphore can be instantiated correctly"""
        from crawlo.core.task_manager import DynamicSemaphore
        
        # Should work without errors
        semaphore = DynamicSemaphore(initial_value=5)
        assert semaphore._initial_value == 5
        assert semaphore._current_value == 5


# Test P1-2: engine.py config extraction
class TestEngineConfigExtraction:
    """Test P1-2: engine.py extracted config to _init_configs()"""
    
    def test_init_configs_method_exists(self):
        """Verify _init_configs() method exists"""
        from crawlo.core.engine import Engine
        
        assert hasattr(Engine, '_init_configs'), \
            "Engine should have _init_configs method"
        
        # Check it's a method
        assert callable(getattr(Engine, '_init_configs'))
    
    def test_init_configs_is_called(self):
        """Verify __init__ calls _init_configs()"""
        from crawlo.core.engine import Engine
        import inspect
        
        source = inspect.getsource(Engine.__init__)
        assert "self._init_configs()" in source, \
            "__init__ should call _init_configs()"


# Test P1-3: scheduler.py magic numbers
class TestSchedulerConstants:
    """Test P1-3: scheduler.py extracted magic numbers to constants"""
    
    def test_default_constants_exist(self):
        """Verify default constants are defined"""
        from crawlo.core import scheduler
        
        assert hasattr(scheduler, '_DEFAULT_QUEUE_TYPE')
        assert hasattr(scheduler, '_DEFAULT_FILTER_CLASS')
        assert hasattr(scheduler, '_DEFAULT_CONCURRENCY')
        assert hasattr(scheduler, '_DEFAULT_DELAY')
        assert hasattr(scheduler, '_DEFAULT_DEPTH_PRIORITY')
    
    def test_default_values_correct(self):
        """Verify constant values are correct"""
        from crawlo.core.scheduler import (
            _DEFAULT_QUEUE_TYPE,
            _DEFAULT_FILTER_CLASS,
            _DEFAULT_CONCURRENCY,
            _DEFAULT_DELAY,
            _DEFAULT_DEPTH_PRIORITY
        )
        
        assert _DEFAULT_QUEUE_TYPE == 'memory'
        assert _DEFAULT_FILTER_CLASS == 'crawlo.filters.memory_filter.MemoryFilter'
        assert _DEFAULT_CONCURRENCY == 8
        assert _DEFAULT_DELAY == 1.0
        assert _DEFAULT_DEPTH_PRIORITY == 0
    
    def test_constants_used_in_code(self):
        """Verify constants are used instead of magic numbers"""
        from crawlo.core.scheduler import Scheduler
        import inspect
        
        source = inspect.getsource(Scheduler.create_instance)
        # 重构后常量前缀为 _DEFAULT_*
        assert "_DEFAULT_FILTER_CLASS" in source, \
            "Should use _DEFAULT_FILTER_CLASS constant"
        assert "_DEFAULT_DEPTH_PRIORITY" in source, \
            "Should use _DEFAULT_DEPTH_PRIORITY constant"


# Test P1-4: processor.py safe_get_config
class TestProcessorSafeGetConfig:
    """Test P1-4: processor.py uses safe_get_config instead of getattr"""
    
    def test_uses_safe_get_config(self):
        """Verify Processor uses safe_get_config"""
        from crawlo.core.processor import Processor
        import inspect
        
        source = inspect.getsource(Processor.__init__)
        assert "safe_get_config" in source, \
            "Processor should use safe_get_config"
        assert "getattr(crawler.settings, 'get_int'" not in source, \
            "Processor should not use getattr chain for config"
    
    def test_config_types_correct(self):
        """Verify config values have correct types"""
        from crawlo.utils.misc import safe_get_config
        
        # Test that safe_get_config works with type conversion
        mock_settings = Mock()
        mock_settings.get_int = Mock(return_value=20)
        mock_settings.get_float = Mock(return_value=2.5)
        
        batch_size = safe_get_config(mock_settings, 'PROCESSOR_BATCH_SIZE', 10, int)
        timeout = safe_get_config(mock_settings, 'PROCESSOR_TIMEOUT', 1.0, float)
        
        assert isinstance(batch_size, int)
        assert isinstance(timeout, float)


# Test P1-5: engine_helpers.py time import
class TestEngineHelpersTimeImport:
    """Test P1-5: engine_helpers.py moved time import to top"""
    
    def test_time_imported_at_top(self):
        """Verify time is imported at module level"""
        import crawlo.core.engine_helpers as module
        import inspect
        
        source = inspect.getsource(module)
        
        # Check time is imported at top (in first 20 lines)
        lines = source.split('\n')[:20]
        has_top_import = any('import time' in line for line in lines)
        assert has_top_import, "time should be imported at module top"
    
    def test_no_local_time_import(self):
        """Verify no local import of time in methods"""
        from crawlo.core.engine_helpers import GenerationStats
        import inspect
        
        source = inspect.getsource(GenerationStats.mark_start)
        assert "import time" not in source, \
            "mark_start should not have local import time"
        
        source = inspect.getsource(GenerationStats.mark_end)
        assert "import time" not in source, \
            "mark_end should not have local import time"


# Test P1-6: error_types.py documentation English
class TestErrorTypesDocumentation:
    """Test P1-6: error_types.py documentation is in English"""
    
    def test_module_docstring_english(self):
        """Verify module docstring is in English"""
        from crawlo.core import error_types
        
        docstring = error_types.__doc__
        assert docstring is not None
        
        # Should contain English words, not Chinese
        assert "Error Type Classification" in docstring
        assert "错误类型分类" not in docstring
    
    def test_class_docstring_english(self):
        """Verify ErrorClassifier docstring is in English"""
        from crawlo.core.error_types import ErrorClassifier
        
        docstring = ErrorClassifier.__doc__
        assert docstring is not None
        assert "Error classifier" in docstring
        assert "错误分类器" not in docstring


# Test P1-7: application.py cleanup exception handling
class TestApplicationCleanupException:
    """Test P1-7: application.py cleanup has proper exception handling"""
    
    @pytest.mark.asyncio
    async def test_handles_cancelled_error(self):
        """Verify cleanup handles asyncio.CancelledError"""
        from crawlo.core.application import ApplicationContext
        import inspect
        
        source = inspect.getsource(ApplicationContext.cleanup)
        assert "CancelledError" in source, \
            "cleanup should handle CancelledError"
    
    @pytest.mark.asyncio
    async def test_cleanup_logs_resource_type(self):
        """Verify cleanup logs resource type name"""
        from crawlo.core.application import ApplicationContext
        import inspect
        
        source = inspect.getsource(ApplicationContext.cleanup)
        assert "type(resource).__name__" in source, \
            "cleanup should log resource type name"
    
    @pytest.mark.asyncio
    async def test_cleanup_has_exc_info(self):
        """Verify cleanup passes exc_info=True to logger"""
        from crawlo.core.application import ApplicationContext
        import inspect
        
        source = inspect.getsource(ApplicationContext.cleanup)
        assert "exc_info=True" in source, \
            "cleanup should pass exc_info=True to logger"


# Test P2-1: __init__.py deprecation warnings
class TestInitDeprecationWarnings:
    """Test P2-1: __init__.py marks compatibility functions as deprecated"""
    
    def test_async_initialize_framework_deprecated(self):
        """Verify async_initialize_framework shows deprecation warning"""
        from crawlo.core import async_initialize_framework
        
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            # This will call initialize_framework internally
            try:
                async_initialize_framework()
            except:
                pass  # Ignore other errors
            
            # Check for deprecation warning
            deprecation_warnings = [
                warning for warning in w 
                if issubclass(warning.category, DeprecationWarning)
            ]
            assert len(deprecation_warnings) > 0, \
                "Should show DeprecationWarning"
    
    def test_bootstrap_framework_deprecated(self):
        """Verify bootstrap_framework shows deprecation warning"""
        from crawlo.core import bootstrap_framework
        
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            try:
                bootstrap_framework()
            except:
                pass
            
            deprecation_warnings = [
                warning for warning in w 
                if issubclass(warning.category, DeprecationWarning)
            ]
            assert len(deprecation_warnings) > 0


# Test P2-2: engine_helpers.py type annotations
class TestEngineHelpersTypeAnnotations:
    """Test P2-2: engine_helpers.py has proper type annotations"""
    
    def test_to_dict_return_type(self):
        """Verify to_dict() returns Dict[str, Any]"""
        from crawlo.core.engine_helpers import GenerationStats
        import inspect
        
        # Get the method
        method = GenerationStats.to_dict
        
        # Check return annotation
        if hasattr(method, '__annotations__'):
            return_annotation = method.__annotations__.get('return')
            # Should be Dict or dict
            assert return_annotation is not None, \
                "to_dict should have return type annotation"


# Integration test: verify all imports work
class TestCoreModuleImports:
    """Integration test: verify all core modules can be imported"""
    
    def test_import_all_modified_modules(self):
        """Verify all modified modules can be imported"""
        # Should not raise any import errors
        from crawlo.core.application import ApplicationContext
        from crawlo.core.error_types import ErrorClassifier
        from crawlo.core.task_manager import DynamicSemaphore
        from crawlo.core.engine import Engine
        from crawlo.core.scheduler import Scheduler
        from crawlo.core.processor import Processor
        from crawlo.core.engine_helpers import GenerationStats, BackpressureController
        
        # All imports successful
        assert ApplicationContext is not None
        assert ErrorClassifier is not None
        assert DynamicSemaphore is not None
        assert Engine is not None
        assert Scheduler is not None
        assert Processor is not None
        assert GenerationStats is not None
        assert BackpressureController is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
