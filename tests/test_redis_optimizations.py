#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Tests for crawlo/utils/redis module optimizations
- Async context manager for RedisConnectionPool
- GlobalRedisManager initialization
- Thread safety in RedisConfig singleton
- Connection pool stats
"""
import pytest
import asyncio
import threading
from unittest.mock import AsyncMock, patch, MagicMock


class TestRedisConnectionPoolAsyncContext:
    """Test async context manager for CrawloRedisManager"""

    @pytest.mark.asyncio
    async def test_async_context_manager_exists(self):
        """Test that CrawloRedisManager has async context manager methods"""
        from crawlo.utils.redis.pool import CrawloRedisManager
        
        # Check methods exist
        assert hasattr(CrawloRedisManager, '__aenter__')
        assert hasattr(CrawloRedisManager, '__aexit__')

    @pytest.mark.asyncio
    async def test_context_manager_protocol(self):
        """Test context manager protocol methods are coroutines"""
        import inspect
        from crawlo.utils.redis.pool import CrawloRedisManager
        
        # Should be async methods
        assert inspect.iscoroutinefunction(CrawloRedisManager.__aenter__)
        assert inspect.iscoroutinefunction(CrawloRedisManager.__aexit__)


class TestGlobalRedisManager:
    """Test GlobalRedisManager improvements"""

    @pytest.mark.asyncio
    async def test_initialize_method(self):
        """Test GlobalRedisManager.initialize method"""
        from crawlo.utils.redis.pool import GlobalRedisManager
        
        manager = GlobalRedisManager()
        
        with patch('crawlo.utils.redis.pool.get_redis_pool') as mock_get_pool:
            mock_pool = MagicMock()
            mock_get_pool.return_value = mock_pool
            
            await manager.initialize('redis://localhost:6379/0')
            
            assert manager._is_initialized is True
            assert manager._default_pool is mock_pool
            mock_get_pool.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_pool_before_init_raises(self):
        """Test that get_pool raises error before initialization"""
        from crawlo.utils.redis.pool import GlobalRedisManager
        
        manager = GlobalRedisManager()
        
        with pytest.raises(RuntimeError, match="Redis管理器未初始化"):
            await manager.get_pool()

    @pytest.mark.asyncio
    async def test_get_pool_after_init(self):
        """Test that get_pool returns pool after initialization"""
        from crawlo.utils.redis.pool import GlobalRedisManager
        
        manager = GlobalRedisManager()
        
        with patch('crawlo.utils.redis.pool.get_redis_pool') as mock_get_pool:
            mock_pool = MagicMock()
            mock_get_pool.return_value = mock_pool
            
            await manager.initialize('redis://localhost:6379/0')
            pool = await manager.get_pool()
            
            assert pool is mock_pool

    @pytest.mark.asyncio
    async def test_close_method(self):
        """Test GlobalRedisManager.close method"""
        from crawlo.utils.redis.pool import GlobalRedisManager
        
        manager = GlobalRedisManager()
        
        with patch('crawlo.utils.redis.pool.get_redis_pool') as mock_get_pool:
            mock_pool = AsyncMock()
            mock_get_pool.return_value = mock_pool
            
            await manager.initialize('redis://localhost:6379/0')
            await manager.close()
            
            assert manager._default_pool is None
            assert manager._is_initialized is False
            mock_pool.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize_idempotent(self):
        """Test that initialize is idempotent (safe to call multiple times)"""
        from crawlo.utils.redis.pool import GlobalRedisManager
        
        manager = GlobalRedisManager()
        
        with patch('crawlo.utils.redis.pool.get_redis_pool') as mock_get_pool:
            mock_pool = MagicMock()
            mock_get_pool.return_value = mock_pool
            
            await manager.initialize('redis://localhost:6379/0')
            await manager.initialize('redis://localhost:6379/1')  # Should be ignored
            
            mock_get_pool.assert_called_once()


class TestRedisConfigThreadSafety:
    """Test thread safety of RedisConfig singleton"""

    def test_singleton_thread_safety(self):
        """Test that RedisConfig singleton is thread-safe"""
        from crawlo.utils.redis.config import RedisConfig
        
        # Clear existing instances
        RedisConfig._instances.clear()
        RedisConfig._default_instance = None
        
        instances = []
        lock = threading.Lock()
        
        def create_config():
            config = RedisConfig.get_instance(host='localhost', port=6379)
            with lock:
                instances.append(config)
        
        # Create 10 threads
        threads = [threading.Thread(target=create_config) for _ in range(10)]
        
        for t in threads:
            t.start()
        
        for t in threads:
            t.join()
        
        # All should be same instance
        assert len(instances) == 10
        assert all(inst is instances[0] for inst in instances)

    def test_singleton_different_configs(self):
        """Test that different configs create different instances"""
        from crawlo.utils.redis.config import RedisConfig
        
        RedisConfig._instances.clear()
        
        config1 = RedisConfig.get_instance(host='localhost', port=6379, db=0)
        config2 = RedisConfig.get_instance(host='localhost', port=6379, db=1)
        
        assert config1 is not config2
        assert config1.db == 0
        assert config2.db == 1


class TestConnectionPoolStats:
    """Test connection pool stats improvements"""

    def test_get_stats_structure(self):
        """Test that get_stats returns expected structure"""
        from crawlo.utils.redis.pool import RedisConnectionPool
        
        # Create pool (won't actually connect due to mock)
        with patch('crawlo.utils.redis.pool.aioredis.ConnectionPool') as mock_pool_cls:
            mock_instance = MagicMock()
            mock_instance.max_connections = 10
            mock_instance._available_connections = []
            mock_instance._in_use_connections = []
            mock_pool_cls.from_url.return_value = mock_instance
            
            pool = RedisConnectionPool(redis_url='redis://localhost:6379/0')
            stats = pool.get_stats()
            
            # Should return dict with expected keys
            assert isinstance(stats, dict)
            assert 'max_connections' in stats
            assert 'available_connections' in stats
            assert 'in_use_connections' in stats


class TestRedisKeyManagerHelper:
    """Test RedisKeyManager._get_setting helper"""

    def test_get_setting_with_dict(self):
        """Test _get_setting with dict-like settings"""
        from crawlo.utils.redis.keys import RedisKeyManager
        
        settings = {'PROJECT_NAME': 'test_project'}
        result = RedisKeyManager._get_setting(settings, 'PROJECT_NAME', 'default')
        
        assert result == 'test_project'

    def test_get_setting_with_object(self):
        """Test _get_setting with object-like settings"""
        from crawlo.utils.redis.keys import RedisKeyManager
        
        class Settings:
            PROJECT_NAME = 'test_project'
        
        settings = Settings()
        result = RedisKeyManager._get_setting(settings, 'PROJECT_NAME', 'default')
        
        assert result == 'test_project'

    def test_get_setting_with_default(self):
        """Test _get_setting returns default when key not found"""
        from crawlo.utils.redis.keys import RedisKeyManager
        
        settings = {}
        result = RedisKeyManager._get_setting(settings, 'MISSING_KEY', 'default_value')
        
        assert result == 'default_value'


class TestIntegration:
    """Integration tests for redis module optimizations"""

    @pytest.mark.asyncio
    async def test_full_lifecycle(self):
        """Test full lifecycle: init -> use -> close"""
        from crawlo.utils.redis.pool import GlobalRedisManager
        
        manager = GlobalRedisManager()
        
        with patch('crawlo.utils.redis.pool.get_redis_pool') as mock_get_pool:
            mock_pool = AsyncMock()
            mock_get_pool.return_value = mock_pool
            
            # Initialize
            await manager.initialize('redis://localhost:6379/0')
            assert manager._is_initialized is True
            
            # Get pool
            pool = await manager.get_pool()
            assert pool is mock_pool
            
            # Close
            await manager.close()
            assert manager._is_initialized is False
            assert manager._default_pool is None
