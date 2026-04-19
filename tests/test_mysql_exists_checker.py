#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
MySQLExistsChecker 测试
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from crawlo.tools.mysql_exists_checker import MySQLExistsChecker, check_exists


class TestMySQLExistsChecker:
    """MySQLExistsChecker 测试"""
    
    def test_init_with_settings(self):
        """测试初始化配置提取"""
        settings = Mock()
        settings.get = Mock(side_effect=lambda k, d=None: {
            'MYSQL_HOST': '192.168.1.100',
            'MYSQL_PORT': 3307,
            'MYSQL_USER': 'test_user',
            'MYSQL_PASSWORD': 'test_pass',
            'MYSQL_DB': 'test_db',
        }.get(k, d))
        settings.get_int = Mock(side_effect=lambda k, d=None: {
            'MYSQL_PORT': 3307,
            'MYSQL_POOL_MIN': 3,
            'MYSQL_POOL_MAX': 15,
        }.get(k, d))
        
        checker = MySQLExistsChecker(settings)
        
        assert checker._db_config['host'] == '192.168.1.100'
        assert checker._db_config['port'] == 3307
        assert checker._db_config['user'] == 'test_user'
        assert checker._db_config['password'] == 'test_pass'
        assert checker._db_config['db'] == 'test_db'
        assert checker._db_config['minsize'] == 3
        assert checker._db_config['maxsize'] == 15
        assert checker.is_closed() is False
    
    def test_init_with_dict(self):
        """测试使用字典初始化"""
        config = {
            'MYSQL_HOST': 'localhost',
            'MYSQL_PORT': 3306,
            'MYSQL_USER': 'root',
            'MYSQL_PASSWORD': '',
            'MYSQL_DB': 'crawlo',
        }
        
        checker = MySQLExistsChecker(config)
        
        assert checker._db_config['host'] == 'localhost'
        assert checker._db_config['port'] == 3306
        assert checker._db_config['user'] == 'root'
    
    def test_init_with_none(self):
        """测试无配置时使用默认值"""
        checker = MySQLExistsChecker(None)
        
        assert checker._db_config['host'] == 'localhost'
        assert checker._db_config['port'] == 3306
        assert checker._db_config['user'] == 'root'
        assert checker._db_config['db'] == 'crawlo'
    
    def test_is_closed(self):
        """测试关闭状态检查"""
        checker = MySQLExistsChecker()
        assert checker.is_closed() is False
        
        checker._closed = True
        assert checker.is_closed() is True
    
    @pytest.mark.asyncio
    async def test_exists_raises_when_closed(self):
        """测试关闭后调用抛出异常"""
        checker = MySQLExistsChecker()
        checker._closed = True
        
        with pytest.raises(RuntimeError, match="已关闭"):
            await checker.exists("SELECT 1 FROM articles LIMIT 1")
    
    @pytest.mark.asyncio
    async def test_context_manager(self):
        """测试异步上下文管理器"""
        async with MySQLExistsChecker() as checker:
            assert checker.is_closed() is False
        
        # 退出后应该关闭
        assert checker.is_closed() is True
    
    @pytest.mark.asyncio
    async def test_context_manager_with_real_usage(self):
        """测试上下文管理器的真实用法"""
        # 创建一个简单的测试
        async with MySQLExistsChecker(None) as checker:
            # 检查初始状态
            assert checker._closed is False
            assert checker._pool is None
            
            # 尝试获取配置（应该成功）
            config = checker._db_config
            assert config['host'] == 'localhost'
    
    @pytest.mark.asyncio
    async def test_batch_exists_raises_when_closed(self):
        """测试批量检查关闭后抛出异常"""
        checker = MySQLExistsChecker()
        checker._closed = True
        
        with pytest.raises(RuntimeError, match="已关闭"):
            await checker.batch_exists("SELECT 1 FROM articles", [("url",)])
    
    @pytest.mark.asyncio
    async def test_count_raises_when_closed(self):
        """测试统计查询关闭后抛出异常"""
        checker = MySQLExistsChecker()
        checker._closed = True
        
        with pytest.raises(RuntimeError, match="已关闭"):
            await checker.count("SELECT COUNT(*) FROM articles")
    
    @pytest.mark.asyncio
    async def test_close(self):
        """测试关闭功能"""
        checker = MySQLExistsChecker()
        mock_pool = Mock()
        checker._pool = mock_pool
        
        await checker.close()
        
        assert checker._closed is True
        assert checker._pool is None
    
    @pytest.mark.asyncio
    async def test_close_idempotent(self):
        """测试关闭的幂等性"""
        checker = MySQLExistsChecker()
        checker._closed = True
        
        # 多次关闭不应该出错
        await checker.close()
        await checker.close()
        
        assert checker._closed is True
    
    @pytest.mark.asyncio
    async def test_close_already_closed(self):
        """测试重复关闭"""
        checker = MySQLExistsChecker()
        checker._closed = True
        
        # 不应该抛出异常
        await checker.close()
        assert checker.is_closed() is True


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


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
