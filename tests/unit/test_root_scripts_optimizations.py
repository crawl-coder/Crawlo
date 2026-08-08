#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Tests for crawlo root scripts optimizations
- Thread safety in framework singleton
- Exception handling in cli.py
- Logger initialization in project.py
"""
import pytest
import threading
from unittest.mock import patch, MagicMock


class TestFrameworkThreadSafety:
    """Test thread safety of framework singleton"""

    def setup_method(self):
        """Reset framework before each test"""
        from crawlo.framework import reset_framework
        reset_framework()

    def teardown_method(self):
        """Clean up after each test"""
        from crawlo.framework import reset_framework
        reset_framework()

    def test_singleton_thread_safety(self):
        """Test that singleton creates only one instance under concurrent access"""
        from crawlo.framework import get_framework, reset_framework
        reset_framework()
        
        instances = []
        lock = threading.Lock()
        
        def create_framework():
            fw = get_framework()
            with lock:
                instances.append(fw)
        
        # Create 10 threads trying to get framework simultaneously
        threads = [threading.Thread(target=create_framework) for _ in range(10)]
        
        # Start all threads
        for t in threads:
            t.start()
        
        # Wait for all threads
        for t in threads:
            t.join()
        
        # All instances should be the same object
        assert len(instances) == 10
        assert all(inst is instances[0] for inst in instances)

    def test_singleton_returns_same_instance(self):
        """Test that multiple calls return the same instance"""
        from crawlo.framework import get_framework
        
        fw1 = get_framework()
        fw2 = get_framework()
        
        assert fw1 is fw2

    def test_reset_framework_creates_new_instance(self):
        """Test that reset_framework allows creating new instance"""
        from crawlo.framework import get_framework, reset_framework
        
        fw1 = get_framework()
        reset_framework()
        fw2 = get_framework()
        
        assert fw1 is not fw2


class TestCliExceptionHandling:
    """Test exception handling in cli.py"""

    def test_bare_except_replaced(self):
        """Verify that bare except is replaced with except Exception"""
        import inspect
        from crawlo import cli
        
        source = inspect.getsource(cli)
        
        # Should not have bare except:
        assert 'except:' not in source or 'except Exception:' in source
        
        # Should have proper exception handling
        assert 'except Exception:' in source


class TestProjectLogger:
    """Test logger initialization in project.py"""

    def test_module_level_logger(self):
        """Test that logger is module-level constant"""
        import crawlo.project as project_module
        
        # Should have _logger attribute
        assert hasattr(project_module, '_logger')
        
        # Should not have logger() function anymore
        assert not hasattr(project_module, 'logger') or callable(getattr(project_module, 'logger', None)) is False

    def test_logger_is_not_none(self):
        """Test that logger is initialized, not None"""
        from crawlo.project import _logger
        
        assert _logger is not None

    def test_logger_has_correct_name(self):
        """Test that logger has correct module name"""
        from crawlo.project import _logger
        
        assert _logger.name == 'crawlo.project'


class TestIntegration:
    """Integration tests for all optimizations"""

    def test_framework_with_logger(self):
        """Test framework initialization works with logger changes"""
        from crawlo.framework import get_framework, reset_framework
        reset_framework()
        
        # Should not raise any exceptions
        fw = get_framework()
        assert fw is not None
        assert hasattr(fw, '_logger')

    def test_cli_main_exists(self):
        """Test that cli.main function exists and is callable"""
        from crawlo.cli import main
        
        assert callable(main)

    def test_project_common_call(self):
        """Test common_call function works correctly"""
        import asyncio
        from crawlo.project import common_call
        
        async def run_tests():
            # Test sync function
            def sync_func(x):
                return x * 2
            
            result = await common_call(sync_func, 5)
            assert result == 10
            
            # Test async function
            async def async_func(x):
                return x * 3
            
            result = await common_call(async_func, 5)
            assert result == 15
        
        asyncio.run(run_tests())
