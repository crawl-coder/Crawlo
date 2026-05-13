#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Test for utils code review fixes
Verifies all P0/P1/P2 fixes work correctly
"""
import asyncio
import pytest
from datetime import datetime

from crawlo.utils.error_handler import ErrorHandler, error_handler, handle_exception
from crawlo.utils.resource_manager import ResourceManager, ResourceType
from crawlo.utils.async_lock import AsyncLock, AsyncCondition
from crawlo.utils.misc import safe_get_config


class TestErrorHandlerFixes:
    """Test error_handler.py fixes"""
    
    def test_datetime_import_works(self):
        """P0: Verify datetime import is present"""
        handler = ErrorHandler()
        # This should not raise NameError
        result = handler.handle_error(
            ValueError("test error"),
            raise_error=False,
            log_error=False
        )
        assert "timestamp" in result
        # Verify timestamp is valid ISO format
        datetime.fromisoformat(result["timestamp"])
    
    def test_no_unused_context_variables(self):
        """P2: Verify unused variables are removed"""
        import inspect
        source = inspect.getsource(ErrorHandler.retry_on_failure)
        # Should not contain unused variable assignments
        assert "retry_context = ErrorContext" not in source
        assert "final_context = ErrorContext" not in source
    
    def test_imports_at_module_level(self):
        """P2: Verify imports are at module level"""
        import crawlo.utils.error_handler as module
        # These should be in module's namespace
        assert hasattr(module, 'asyncio')
        assert hasattr(module, 'inspect')
        assert hasattr(module, 'time')


class TestResourceManagerFixes:
    """Test resource_manager.py dependency calculation fix"""
    
    @pytest.mark.asyncio
    async def test_cleanup_order_with_dependencies(self):
        """P1: Verify correct cleanup order"""
        rm = ResourceManager("test")
        
        cleanup_order = []
        
        # Register pool first (no dependencies)
        rm.register(
            resource="pool_resource",
            cleanup_func=lambda r: cleanup_order.append(r),
            resource_type=ResourceType.REDIS_POOL,
            name="main_pool",
            priority=10,
            depends_on=set()
        )
        
        # Register downloader that depends on pool
        rm.register(
            resource="downloader_resource",
            cleanup_func=lambda r: cleanup_order.append(r),
            resource_type=ResourceType.DOWNLOADER,
            name="main_downloader",
            priority=5,
            depends_on={"main_pool"}
        )
        
        await rm.cleanup_all()
        
        # Downloader should be cleaned BEFORE pool (depends on pool)
        # Pool must stay alive longer since downloader depends on it
        assert len(cleanup_order) == 2
        assert cleanup_order[0] == "downloader_resource"
        assert cleanup_order[1] == "pool_resource"


class TestAsyncLockFixes:
    """Test async_lock.py encapsulation fix"""
    
    def test_underlying_lock_property_exists(self):
        """P1: Verify underlying_lock property exists"""
        lock = AsyncLock()
        assert hasattr(lock, 'underlying_lock')
        # Should return the internal asyncio.Lock
        assert hasattr(lock.underlying_lock, 'acquire')
        assert hasattr(lock.underlying_lock, 'release')
    
    @pytest.mark.asyncio
    async def test_async_condition_uses_property(self):
        """P1: Verify AsyncCondition uses property, not private attribute"""
        import inspect
        from crawlo.utils.async_lock import AsyncCondition
        
        source = inspect.getsource(AsyncCondition.__init__)
        # Should use property, not direct private access
        assert "underlying_lock" in source
        assert "_lock._lock" not in source
        
        # Test it actually works
        async_lock = AsyncLock()
        condition = AsyncCondition(async_lock)
        assert condition is not None


class TestMiscFixes:
    """Test misc.py exception handling fix"""
    
    def test_exception_handling_simplified(self):
        """P2: Verify exception handling is simplified"""
        import inspect
        source = inspect.getsource(safe_get_config)
        # Should have simplified exception clause
        assert "except Exception:" in source
        # Should not have redundant exception types
        assert "except (TypeError, ValueError, AttributeError, Exception)" not in source
    
    def test_safe_get_config_still_works(self):
        """Verify safe_get_config still functions correctly"""
        # Test with dict
        settings = {'TEST_KEY': 'test_value'}
        assert safe_get_config(settings, 'TEST_KEY') == 'test_value'
        assert safe_get_config(settings, 'MISSING_KEY', 'default') == 'default'
        
        # Test with object
        class Obj:
            KEY = 'obj_value'
        
        assert safe_get_config(Obj(), 'KEY') == 'obj_value'
        
        # Test with None
        assert safe_get_config(None, 'KEY', 'default') == 'default'
        
        # Test type conversion
        assert safe_get_config({'NUM': '42'}, 'NUM', value_type=int) == 42
        assert safe_get_config({'FLAG': 'true'}, 'FLAG', value_type=bool) is True


class TestIntegration:
    """Integration tests for all fixes"""
    
    @pytest.mark.asyncio
    async def test_error_handler_with_resource_manager(self):
        """Test error handler works with resource manager"""
        rm = ResourceManager("integration_test")
        
        # Register a resource that will fail during cleanup
        rm.register(
            resource="test_resource",
            cleanup_func=lambda r: (_ for _ in ()).throw(ValueError("cleanup error")),
            resource_type=ResourceType.OTHER,
            name="failing_resource"
        )
        
        # Should handle error gracefully
        result = await rm.cleanup_all()
        assert result['errors'] == 1
        assert result['success'] == 0
    
    def test_all_imports_work(self):
        """Verify all optimized modules can be imported"""
        from crawlo.utils.error_handler import ErrorHandler, handle_exception
        from crawlo.utils.resource_manager import ResourceManager, get_resource_manager
        from crawlo.utils.async_lock import AsyncLock, AsyncRLock, AsyncCondition
        from crawlo.utils.misc import safe_get_config, ConfigUtils
        
        # All imports successful
        assert True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
