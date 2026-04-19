#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
MySQLExistsChecker 测试
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from crawlo.tools.mysql_exists_checker import MySQLExistsChecker, check_exists


class TestMySQLExistsChecker:
    """MySQLExistsChecker 测试"""
    
    def test_init_with_config(self):
        """测试配置初始化"""
        config = {
            'host': 'localhost',
            'port': 3306,
            'user': 'root',
            'password': '',
            'db': 'crawlo',
        }
        checker = MySQLExistsChecker(config)
        assert checker._config['host'] == 'localhost'
        assert checker._closed is False
    
    def test_init_with_dict(self):
        """测试字典配置"""
        config = {
            'MYSQL_HOST': '192.168.1.100',
            'MYSQL_PORT': 3307,
            'MYSQL_USER': 'test',
            'MYSQL_DB': 'test_db',
        }
        checker = MySQLExistsChecker.from_settings(config)
        assert checker._config['host'] == '192.168.1.100'
        assert checker._config['port'] == 3307
    
    def test_init_with_none(self):
        """测试默认配置"""
        checker = MySQLExistsChecker.from_settings(None)
        assert checker._config['host'] == 'localhost'
        assert checker._config['port'] == 3306
    
    def test_is_closed(self):
        """测试关闭状态"""
        checker = MySQLExistsChecker({'host': 'localhost'})
        assert checker.is_closed() is False
        checker._closed = True
        assert checker.is_closed() is True
    
    @pytest.mark.asyncio
    async def test_exists_raises_when_closed(self):
        """测试关闭后抛出异常"""
        checker = MySQLExistsChecker({'host': 'localhost'})
        checker._closed = True
        
        with pytest.raises(RuntimeError, match="已关闭"):
            await checker.exists("SELECT 1 FROM t")
    
    @pytest.mark.asyncio
    async def test_batch_exists_raises_when_closed(self):
        """测试批量检查关闭后抛出异常"""
        checker = MySQLExistsChecker({'host': 'localhost'})
        checker._closed = True
        
        with pytest.raises(RuntimeError, match="已关闭"):
            await checker.batch_exists("SELECT 1 FROM t", [("a",)])
    
    @pytest.mark.asyncio
    async def test_count_raises_when_closed(self):
        """测试统计关闭后抛出异常"""
        checker = MySQLExistsChecker({'host': 'localhost'})
        checker._closed = True
        
        with pytest.raises(RuntimeError, match="已关闭"):
            await checker.count("SELECT COUNT(*) FROM t")
    
    @pytest.mark.asyncio
    async def test_close(self):
        """测试关闭"""
        checker = MySQLExistsChecker({'host': 'localhost'})
        await checker.close()
        assert checker.is_closed() is True


class TestCheckExists:
    """便捷函数测试"""
    
    def test_import(self):
        """测试导入"""
        from crawlo.tools import MySQLExistsChecker, check_exists
        assert MySQLExistsChecker is not None
        assert check_exists is not None
    
    def test_check_exists_is_coroutine(self):
        """测试是协程函数"""
        assert asyncio.iscoroutinefunction(check_exists) is True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
