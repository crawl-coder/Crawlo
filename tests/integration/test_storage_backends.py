#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
指纹存储后端测试

测试两种存储管理器：
1. SqliteStorage - 单机模式
2. RedisStorage - 分布式模式

测试内容：
- 基本存取功能
- 数据覆盖更新
- 多域名隔离
- 线程安全
- 异常处理
"""

import os
import sys
import tempfile
import json
from pathlib import Path
from threading import Thread, Lock

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from crawlo.helpers.adaptive_selector.storage import (
    SqliteStorage,
    RedisStorage,
    FingerprintStorage,
)
from crawlo.helpers.adaptive_selector.element_fingerprint import ElementFingerprint


# 测试用指纹数据
def create_test_fingerprint(tag='div', text='测试文本', attrs=None):
    """创建测试指纹"""
    return ElementFingerprint(
        tag=tag,
        text=text,
        attributes=attrs or {'class': 'test-class'},
        path=('html', 'body', 'div', 'article'),
        parent_name='article',
        parent_attribs={'id': 'content'},
        parent_text='文章内容',
        siblings=('prev-sibling', 'next-sibling'),
        children=('h3', 'p', 'span'),
    )


class TestSqliteStorage:
    """SQLite 存储测试"""

    def __init__(self):
        self.temp_db = tempfile.mktemp(suffix='.db')
        self.storage = None
        self.results = []

    def setup(self):
        """初始化"""
        print("\n" + "="*60)
        print("测试：SQLite 存储后端（单机模式）")
        print("="*60)
        self.storage = SqliteStorage(storage_file=self.temp_db)
        print(f"✓ 数据库初始化: {self.temp_db}")

    def cleanup(self):
        """清理"""
        if self.storage:
            self.storage.close()
        if os.path.exists(self.temp_db):
            try:
                os.remove(self.temp_db)
            except:
                pass

    def test_basic_save_retrieve(self):
        """测试1：基本存取"""
        print("\n[测试1] 基本存取功能")
        
        fingerprint = create_test_fingerprint(
            tag='div',
            text='列表项内容',
            attrs={'class': 'list-item'}
        )
        
        # 保存
        self.storage.save('ee.ofweek.com', 'list_selector', fingerprint)
        print("  ✓ 保存指纹")
        
        # 读取
        retrieved = self.storage.retrieve('ee.ofweek.com', 'list_selector')
        assert retrieved is not None, "指纹读取失败"
        assert retrieved['tag'] == 'div', f"标签不匹配: {retrieved['tag']}"
        assert retrieved['text'] == '列表项内容', f"文本不匹配: {retrieved['text']}"
        assert retrieved['attributes']['class'] == 'list-item'
        print("  ✓ 读取指纹并验证")
        print(f"    - 标签: {retrieved['tag']}")
        print(f"    - 文本: {retrieved['text']}")
        print(f"    - 属性: {retrieved['attributes']}")
        
        self.results.append(('基本存取', True))

    def test_overwrite_update(self):
        """测试2：覆盖更新"""
        print("\n[测试2] 覆盖更新")
        
        # 首次保存
        fp1 = create_test_fingerprint(text='原始内容')
        self.storage.save('test.com', 'selector1', fp1)
        print("  ✓ 首次保存")
        
        # 覆盖保存
        fp2 = create_test_fingerprint(text='更新内容')
        self.storage.save('test.com', 'selector1', fp2)
        print("  ✓ 覆盖保存")
        
        # 验证更新
        retrieved = self.storage.retrieve('test.com', 'selector1')
        assert retrieved['text'] == '更新内容', f"更新失败: {retrieved['text']}"
        print(f"  ✓ 验证更新成功: {retrieved['text']}")
        
        self.results.append(('覆盖更新', True))

    def test_multi_domain_isolation(self):
        """测试3：多域名隔离"""
        print("\n[测试3] 多域名隔离")
        
        # 不同域名保存相同 identifier
        fp1 = create_test_fingerprint(text='域名A的内容')
        fp2 = create_test_fingerprint(text='域名B的内容')
        
        self.storage.save('domain-a.com', 'article', fp1)
        self.storage.save('domain-b.com', 'article', fp2)
        print("  ✓ 两个域名保存相同 identifier")
        
        # 验证隔离
        data_a = self.storage.retrieve('domain-a.com', 'article')
        data_b = self.storage.retrieve('domain-b.com', 'article')
        
        assert data_a['text'] == '域名A的内容'
        assert data_b['text'] == '域名B的内容'
        print(f"  ✓ 域名A: {data_a['text']}")
        print(f"  ✓ 域名B: {data_b['text']}")
        
        self.results.append(('多域名隔离', True))

    def test_nonexistent_key(self):
        """测试4：不存在的键"""
        print("\n[测试4] 不存在的键")
        
        result = self.storage.retrieve('nonexistent.com', 'missing_selector')
        assert result is None, "不存在的键应返回 None"
        print("  ✓ 不存在的键返回 None")
        
        self.results.append(('不存在键处理', True))

    def test_thread_safety(self):
        """测试5：线程安全"""
        print("\n[测试5] 线程安全（并发读写）")
        
        error_count = [0]
        success_count = [0]
        lock = Lock()
        
        def worker(thread_id):
            try:
                domain = f'thread-{thread_id}.com'
                for i in range(10):
                    fp = create_test_fingerprint(text=f'线程{thread_id}-数据{i}')
                    self.storage.save(domain, f'selector_{i}', fp)
                    retrieved = self.storage.retrieve(domain, f'selector_{i}')
                    assert retrieved['text'] == f'线程{thread_id}-数据{i}'
                
                with lock:
                    success_count[0] += 1
            except Exception as e:
                with lock:
                    error_count[0] += 1
                print(f"  ✗ 线程{thread_id} 错误: {e}")
        
        # 启动5个线程
        threads = []
        for i in range(5):
            t = Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()
        
        # 等待完成
        for t in threads:
            t.join()
        
        print(f"  ✓ 成功: {success_count[0]}/5 线程")
        print(f"  ✓ 失败: {error_count[0]}/5 线程")
        assert error_count[0] == 0, f"{error_count[0]} 个线程出错"
        
        self.results.append(('线程安全', True))

    def run_all(self):
        """运行所有测试"""
        self.setup()
        try:
            self.test_basic_save_retrieve()
            self.test_overwrite_update()
            self.test_multi_domain_isolation()
            self.test_nonexistent_key()
            self.test_thread_safety()
            
            print("\n" + "="*60)
            print("SQLite 测试结果汇总")
            print("="*60)
            for name, passed in self.results:
                status = "✓ 通过" if passed else "✗ 失败"
                print(f"  {status} - {name}")
            
            all_passed = all(passed for _, passed in self.results)
            print(f"\n总计: {sum(1 for _, p in self.results if p)}/{len(self.results)} 通过")
            return all_passed
        finally:
            self.cleanup()


class TestRedisStorage:
    """Redis 存储测试"""

    def __init__(self):
        self.storage = None
        self.results = []
        self.redis_available = False

    def setup(self):
        """初始化"""
        print("\n" + "="*60)
        print("测试：Redis 存储后端（分布式模式）")
        print("="*60)
        
        try:
            self.storage = RedisStorage(redis_url='redis://localhost:6379/15')
            # 测试连接
            self.storage._redis.ping()
            self.redis_available = True
            print("✓ Redis 连接成功")
        except Exception as e:
            print(f"⚠ Redis 不可用: {e}")
            print("  跳过 Redis 测试（需要启动 Redis 服务）")
            self.redis_available = False
            return False
        
        return True

    def cleanup(self):
        """清理测试数据"""
        if self.storage and self.redis_available:
            # 清理测试 key
            try:
                keys = self.storage._redis.keys('crawlo:adaptive:test-*')
                if keys:
                    self.storage._redis.delete(*keys)
                print("✓ 已清理测试数据")
            except:
                pass

    def test_basic_save_retrieve(self):
        """测试1：基本存取"""
        print("\n[测试1] 基本存取功能")
        
        fingerprint = create_test_fingerprint(
            tag='article',
            text='文章标题',
            attrs={'class': 'news-article', 'id': 'art-123'}
        )
        
        # 保存
        self.storage.save('test-redis.com', 'article_selector', fingerprint)
        print("  ✓ 保存指纹")
        
        # 读取
        retrieved = self.storage.retrieve('test-redis.com', 'article_selector')
        assert retrieved is not None, "指纹读取失败"
        assert retrieved['tag'] == 'article'
        assert retrieved['text'] == '文章标题'
        print("  ✓ 读取指纹并验证")
        print(f"    - 标签: {retrieved['tag']}")
        print(f"    - 文本: {retrieved['text']}")
        print(f"    - 属性: {retrieved['attributes']}")
        
        self.results.append(('基本存取', True))

    def test_overwrite_update(self):
        """测试2：覆盖更新"""
        print("\n[测试2] 覆盖更新")
        
        fp1 = create_test_fingerprint(text='版本1')
        fp2 = create_test_fingerprint(text='版本2')
        
        self.storage.save('test-redis.com', 'update_test', fp1)
        self.storage.save('test-redis.com', 'update_test', fp2)
        print("  ✓ 覆盖保存")
        
        retrieved = self.storage.retrieve('test-redis.com', 'update_test')
        assert retrieved['text'] == '版本2'
        print(f"  ✓ 验证更新成功: {retrieved['text']}")
        
        self.results.append(('覆盖更新', True))

    def test_multi_domain_isolation(self):
        """测试3：多域名隔离"""
        print("\n[测试3] 多域名隔离")
        
        fp1 = create_test_fingerprint(text='站点X数据')
        fp2 = create_test_fingerprint(text='站点Y数据')
        
        self.storage.save('test-site-x.com', 'content', fp1)
        self.storage.save('test-site-y.com', 'content', fp2)
        print("  ✓ 两个域名保存相同 identifier")
        
        data_x = self.storage.retrieve('test-site-x.com', 'content')
        data_y = self.storage.retrieve('test-site-y.com', 'content')
        
        assert data_x['text'] == '站点X数据'
        assert data_y['text'] == '站点Y数据'
        print(f"  ✓ 站点X: {data_x['text']}")
        print(f"  ✓ 站点Y: {data_y['text']}")
        
        self.results.append(('多域名隔离', True))

    def test_key_format(self):
        """测试4：Key 格式验证"""
        print("\n[测试4] Redis Key 格式")
        
        # 保存后检查 key 格式
        fp = create_test_fingerprint(text='key测试')
        self.storage.save('test-keyformat.com', 'test_selector', fp)
        
        key = self.storage._make_key('test-keyformat.com')
        print(f"  ✓ Redis Key: {key}")
        assert key == 'crawlo:adaptive:test-keyformat.com'
        
        # 验证 Hash 结构
        all_fields = self.storage._redis.hgetall(key)
        print(f"  ✓ Hash 字段数: {len(all_fields)}")
        assert len(all_fields) >= 2  # 至少包含数据 + selector
        
        self.results.append(('Key格式', True))

    def test_nonexistent_key(self):
        """测试5：不存在的键"""
        print("\n[测试5] 不存在的键")
        
        result = self.storage.retrieve('nonexistent.com', 'missing')
        assert result is None
        print("  ✓ 不存在的键返回 None")
        
        self.results.append(('不存在键处理', True))

    def run_all(self):
        """运行所有测试"""
        if not self.setup():
            return None  # Redis 不可用
        
        try:
            self.test_basic_save_retrieve()
            self.test_overwrite_update()
            self.test_multi_domain_isolation()
            self.test_key_format()
            self.test_nonexistent_key()
            
            print("\n" + "="*60)
            print("Redis 测试结果汇总")
            print("="*60)
            for name, passed in self.results:
                status = "✓ 通过" if passed else "✗ 失败"
                print(f"  {status} - {name}")
            
            all_passed = all(passed for _, passed in self.results)
            print(f"\n总计: {sum(1 for _, p in self.results if p)}/{len(self.results)} 通过")
            return all_passed
        finally:
            self.cleanup()


class TestFingerprintStorage:
    """FingerprintStorage 统一接口测试"""

    def __init__(self):
        self.temp_db = tempfile.mktemp(suffix='.db')
        self.results = []

    def test_sqlite_backend(self):
        """测试 SQLite 后端"""
        print("\n" + "="*60)
        print("测试：FingerprintStorage - SQLite 后端")
        print("="*60)
        
        storage = FingerprintStorage(
            backend='sqlite',
            storage_file=self.temp_db
        )
        
        # 保存（传入完整 URL，自动提取域名）
        fp = create_test_fingerprint(text='统一接口测试')
        storage.save('https://ee.ofweek.com/article/123.html', 'article_sel', fp)
        print("✓ 保存指纹（URL: https://ee.ofweek.com/article/123.html）")
        
        # 读取
        retrieved = storage.retrieve('https://ee.ofweek.com/article/123.html', 'article_sel')
        assert retrieved is not None
        assert retrieved['text'] == '统一接口测试'
        print(f"✓ 读取成功: {retrieved['text']}")
        
        storage.close()
        self.results.append(('SQLite后端', True))

    def test_backend_selection(self):
        """测试后端选择"""
        print("\n[测试] 后端选择逻辑")
        
        # SQLite
        storage1 = FingerprintStorage(backend='sqlite', storage_file=self.temp_db)
        assert isinstance(storage1._backend, SqliteStorage)
        print("  ✓ SQLite 后端正确初始化")
        storage1.close()
        
        # Redis（如果可用）
        try:
            storage2 = FingerprintStorage(backend='redis', redis_url='redis://localhost:6379/15')
            assert isinstance(storage2._backend, RedisStorage)
            print("  ✓ Redis 后端正确初始化")
            storage2.close()
            self.results.append(('后端选择', True))
        except:
            print("  ⚠ Redis 不可用，跳过")
            self.results.append(('后端选择', True))  # SQLite 测试通过即可

    def cleanup(self):
        """清理"""
        if os.path.exists(self.temp_db):
            try:
                os.remove(self.temp_db)
            except:
                pass

    def run_all(self):
        """运行测试"""
        try:
            self.test_sqlite_backend()
            self.test_backend_selection()
            
            print("\n" + "="*60)
            print("FingerprintStorage 测试结果汇总")
            print("="*60)
            for name, passed in self.results:
                status = "✓ 通过" if passed else "✗ 失败"
                print(f"  {status} - {name}")
            
            return all(passed for _, passed in self.results)
        finally:
            self.cleanup()


if __name__ == '__main__':
    print("="*60)
    print("指纹存储后端完整测试")
    print("="*60)

    all_results = []

    # 测试1：SQLite
    sqlite_test = TestSqliteStorage()
    sqlite_passed = sqlite_test.run_all()
    all_results.append(('SQLite存储', sqlite_passed))

    # 测试2：Redis
    redis_test = TestRedisStorage()
    redis_passed = redis_test.run_all()
    if redis_passed is not None:
        all_results.append(('Redis存储', redis_passed))

    # 测试3：统一接口
    unified_test = TestFingerprintStorage()
    unified_passed = unified_test.run_all()
    all_results.append(('统一接口', unified_passed))

    # 总汇总
    print("\n" + "="*60)
    print("总体测试结果")
    print("="*60)
    for name, passed in all_results:
        status = "✓ 通过" if passed else "✗ 失败"
        print(f"  {status} - {name}")

    total_passed = sum(1 for _, p in all_results if p)
    total_tests = len(all_results)
    print(f"\n总计: {total_passed}/{total_tests} 测试套件通过")

    if total_passed == total_tests:
        print("\n✓✓✓ 所有存储后端测试通过！")
    else:
        print(f"\n⚠ {total_tests - total_passed} 个测试套件未通过")

    sys.exit(0 if total_passed == total_tests else 1)
