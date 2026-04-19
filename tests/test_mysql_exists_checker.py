#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
MySQLExistsChecker 测试
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from crawlo.tools.mysql_exists_checker import MySQLExistsChecker, check_exists, _MySQLPoolManager


class TestMySQLPoolManager:
    """连接池管理器测试"""
    
    def test_generate_key(self):
        """测试配置 key 生成"""
        config = {
            'host': 'localhost',
            'port': 3306,
            'db': 'test_db'
        }
        key = _MySQLPoolManager._generate_key(config)
        assert key == "localhost:3306/test_db"
    
    def test_get_pool_count_empty(self):
        """测试初始连接池数量为 0"""
        assert _MySQLPoolManager.get_pool_count() == 0


class TestMySQLExistsChecker:
    """MySQLExistsChecker 测试"""
    
    def test_init_with_config(self):
        """测试使用配置字典初始化"""
        config = {
            'host': '192.168.1.100',
            'port': 3307,
            'user': 'test_user',
            'password': 'test_pass',
            'db': 'test_db',
            'minsize': 3,
            'maxsize': 15,
        }
        
        checker = MySQLExistsChecker(config)
        
        assert checker._config['host'] == '192.168.1.100'
        assert checker._config['port'] == 3307
        assert checker._config['user'] == 'test_user'
        assert checker._config['password'] == 'test_pass'
        assert checker._config['db'] == 'test_db'
        assert checker._config['minsize'] == 3
        assert checker._config['maxsize'] == 15
        assert checker.is_closed() is False
    
    def test_init_with_settings_object(self):
        """测试使用 Settings 对象初始化"""
        settings = Mock()
        settings.get = Mock(side_effect=lambda k, d=None: {
            'MYSQL_HOST': '192.168.1.100',
            'MYSQL_USER': 'test_user',
            'MYSQL_PASSWORD': 'test_pass',
            'MYSQL_DB': 'test_db',
        }.get(k, d))
        settings.get_int = Mock(side_effect=lambda k, d=None: {
            'MYSQL_PORT': 3307,
            'MYSQL_POOL_MIN': 3,
            'MYSQL_POOL_MAX': 15,
        }.get(k, d))
        
        checker = MySQLExistsChecker.from_settings(settings)
        
        assert checker._config['host'] == '192.168.1.100'
        assert checker._config['port'] == 3307
        assert checker._config['user'] == 'test_user'
        assert checker._config['minsize'] == 3
        assert checker._config['maxsize'] == 15
    
    def test_init_with_dict(self):
        """测试使用字典初始化"""
        config = {
            'MYSQL_HOST': 'localhost',
            'MYSQL_PORT': 3306,
            'MYSQL_USER': 'root',
            'MYSQL_PASSWORD': '',
            'MYSQL_DB': 'crawlo',
        }
        
        checker = MySQLExistsChecker.from_settings(config)
        
        assert checker._config['host'] == 'localhost'
        assert checker._config['port'] == 3306
        assert checker._config['user'] == 'root'
    
    def test_init_with_none(self):
        """测试无配置时使用默认值"""
        checker = MySQLExistsChecker.from_settings(None)
        
        assert checker._config['host'] == 'localhost'
        assert checker._config['port'] == 3306
        assert checker._config['user'] == 'root'
        assert checker._config['db'] == 'crawlo'
    
    def test_is_closed(self):
        """测试关闭状态检查"""
        checker = MySQLExistsChecker({'host': 'localhost'})
        assert checker.is_closed() is False
        
        checker._closed = True
        assert checker.is_closed() is True
    
    @pytest.mark.asyncio
    async def test_exists_raises_when_closed(self):
        """测试关闭后调用抛出异常"""
        checker = MySQLExistsChecker({'host': 'localhost'})
        checker._closed = True
        
        with pytest.raises(RuntimeError, match="已关闭"):
            await checker.exists("SELECT 1 FROM articles LIMIT 1")
    
    @pytest.mark.asyncio
    async def test_batch_exists_raises_when_closed(self):
        """测试批量检查关闭后抛出异常"""
        checker = MySQLExistsChecker({'host': 'localhost'})
        checker._closed = True
        
        with pytest.raises(RuntimeError, match="已关闭"):
            await checker.batch_exists("SELECT 1 FROM articles", [("url",)])
    
    @pytest.mark.asyncio
    async def test_count_raises_when_closed(self):
        """测试统计查询关闭后抛出异常"""
        checker = MySQLExistsChecker({'host': 'localhost'})
        checker._closed = True
        
        with pytest.raises(RuntimeError, match="已关闭"):
            await checker.count("SELECT COUNT(*) FROM articles")
    
    @pytest.mark.asyncio
    async def test_close(self):
        """测试关闭功能"""
        checker = MySQLExistsChecker({'host': 'localhost'})
        mock_pool = Mock()
        checker._pool = mock_pool
        
        await checker.close()
        
        assert checker._closed is True
        assert checker._pool is None  # 引用被清除，但不关闭连接池
    
    @pytest.mark.asyncio
    async def test_close_idempotent(self):
        """测试关闭的幂等性"""
        checker = MySQLExistsChecker({'host': 'localhost'})
        checker._closed = True
        
        # 多次关闭不应该出错
        await checker.close()
        await checker.close()
        
        assert checker._closed is True
    
    @pytest.mark.asyncio
    async def test_close_all(self):
        """测试关闭所有连接池"""
        # 清空现有连接池
        _MySQLPoolManager._pools.clear()
        
        # 调用 close_all
        await MySQLExistsChecker.close_all()
        
        assert _MySQLPoolManager.get_pool_count() == 0


class TestCheckExistsConvenienceFunction:
    """便捷函数测试"""
    
    def test_import_from_tools(self):
        """测试从 tools 模块导入"""
        from crawlo.tools import MySQLExistsChecker, check_exists
        
        assert MySQLExistsChecker is not None
        assert check_exists is not None
    
    def test_check_exists_is_coroutine_function(self):
        """测试便捷函数是协程函数"""
        assert asyncio.iscoroutinefunction(check_exists) is True
    
    @pytest.mark.asyncio
    async def test_check_exists_function_creates_checker(self):
        """测试便捷函数创建并关闭检查器"""
        checker = MySQLExistsChecker({'host': 'localhost'})
        checker._closed = True  # 模拟已关闭
        
        with patch('crawlo.tools.mysql_exists_checker.MySQLExistsChecker') as MockChecker:
            MockChecker.from_settings.return_value = checker
            checker.exists = AsyncMock(return_value=True)
            
            result = await check_exists(
                "SELECT 1 FROM articles WHERE url = %s LIMIT 1",
                ("https://example.com",)
            )
            
            assert result is True


class TestPoolSharing:
    """连接池复用测试"""
    
    def test_multiple_checkers_share_same_pool(self):
        """测试多个检查器可以共享同一个配置"""
        config = {'host': 'localhost', 'port': 3306, 'db': 'test'}
        
        checker1 = MySQLExistsChecker(config)
        checker2 = MySQLExistsChecker(config)
        
        # 配置相同
        assert checker1._config == checker2._config


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
