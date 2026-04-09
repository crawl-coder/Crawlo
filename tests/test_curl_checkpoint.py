#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
测试 curl_parser 和 checkpoint 模块
"""
import asyncio
import json
import os
import sys
import shutil
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_curl_parser_basic():
    """测试 curl 基本解析"""
    from crawlo.utils.curl_parser import CurlParser
    
    result = CurlParser.parse('curl https://example.com')
    assert result['url'] == 'https://example.com'
    assert result['method'] == 'GET'
    print("✅ curl 基本解析测试通过")


def test_curl_parser_post_json():
    """测试 POST JSON 请求解析"""
    from crawlo.utils.curl_parser import CurlParser
    
    cmd = 'curl https://api.example.com -X POST -H "Content-Type: application/json" -d \'{"key":"val"}\''
    result = CurlParser.parse(cmd)
    assert result['url'] == 'https://api.example.com'
    assert result['method'] == 'POST'
    assert result['json_body'] == {"key": "val"}
    print("✅ curl POST JSON 解析测试通过")


def test_curl_parser_headers():
    """测试 headers 解析"""
    from crawlo.utils.curl_parser import CurlParser
    
    cmd = 'curl https://example.com -H "Authorization: Bearer xyz" -H "Accept: text/html"'
    result = CurlParser.parse(cmd)
    assert result['headers']['Authorization'] == 'Bearer xyz'
    assert result['headers']['Accept'] == 'text/html'
    print("✅ curl headers 解析测试通过")


def test_curl_parser_cookies():
    """测试 cookies 解析"""
    from crawlo.utils.curl_parser import CurlParser
    
    cmd = 'curl https://example.com -b "session=abc123; user=john"'
    result = CurlParser.parse(cmd)
    assert result['cookies']['session'] == 'abc123'
    assert result['cookies']['user'] == 'john'
    print("✅ curl cookies 解析测试通过")


def test_curl_parser_auth():
    """测试认证解析"""
    from crawlo.utils.curl_parser import CurlParser
    
    cmd = 'curl https://example.com -u admin:secret'
    result = CurlParser.parse(cmd)
    assert result['auth'] == ('admin', 'secret')
    print("✅ curl 认证解析测试通过")


def test_curl_parser_flags():
    """测试布尔标志解析"""
    from crawlo.utils.curl_parser import CurlParser
    
    cmd = 'curl https://example.com -k --compressed'
    result = CurlParser.parse(cmd)
    assert result['verify'] == False
    # --compressed 应被忽略
    print("✅ curl 布尔标志解析测试通过")


def test_curl_parser_timeout():
    """测试超时解析"""
    from crawlo.utils.curl_parser import CurlParser
    
    cmd = 'curl https://example.com --connect-timeout 15'
    result = CurlParser.parse(cmd)
    assert result['timeout'] == 15.0
    print("✅ curl 超时解析测试通过")


def test_curl_parser_proxy():
    """测试代理解析"""
    from crawlo.utils.curl_parser import CurlParser
    
    cmd = 'curl https://example.com --proxy http://127.0.0.1:8080'
    result = CurlParser.parse(cmd)
    assert result['proxy'] == 'http://127.0.0.1:8080'
    print("✅ curl 代理解析测试通过")


def test_curl_parser_head():
    """测试 HEAD 请求"""
    from crawlo.utils.curl_parser import CurlParser
    
    cmd = 'curl -I https://example.com'
    result = CurlParser.parse(cmd)
    assert result['method'] == 'HEAD'
    print("✅ curl HEAD 请求解析测试通过")


def test_curl_parser_data_auto_post():
    """测试 -d 自动设为 POST"""
    from crawlo.utils.curl_parser import CurlParser
    
    cmd = 'curl https://example.com -d "key=val"'
    result = CurlParser.parse(cmd)
    assert result['method'] == 'POST'
    assert result['body'] == 'key=val'
    print("✅ curl -d 自动 POST 解析测试通过")


def test_curl_parser_form_data():
    """测试表单数据解析"""
    from crawlo.utils.curl_parser import CurlParser
    
    cmd = 'curl https://example.com -H "Content-Type: application/x-www-form-urlencoded" -d "name=John&age=30"'
    result = CurlParser.parse(cmd)
    assert result['form_data']['name'] == 'John'
    assert result['form_data']['age'] == '30'
    print("✅ curl 表单数据解析测试通过")


def test_curl_parser_multiline():
    """测试多行 curl 命令"""
    from crawlo.utils.curl_parser import CurlParser
    
    cmd = '''curl https://example.com \\
  -H "Authorization: Bearer xyz" \\
  -d '{"key":"val"}' \\
  --compressed'''
    result = CurlParser.parse(cmd)
    assert result['url'] == 'https://example.com'
    assert result['headers']['Authorization'] == 'Bearer xyz'
    print("✅ curl 多行命令解析测试通过")


def test_curl_parser_no_url():
    """测试缺少 URL 的情况"""
    from crawlo.utils.curl_parser import CurlParser
    
    try:
        CurlParser.parse('curl -H "Key: val"')
        assert False, "Should raise ValueError"
    except ValueError as e:
        assert "No URL" in str(e)
    print("✅ curl 缺少 URL 错误测试通过")


def test_curl_parser_empty():
    """测试空命令"""
    from crawlo.utils.curl_parser import CurlParser
    
    try:
        CurlParser.parse('')
        assert False, "Should raise ValueError"
    except ValueError:
        pass
    print("✅ curl 空命令错误测试通过")


def test_curl_parser_to_request():
    """测试 to_request 直接生成 Request"""
    from crawlo.utils.curl_parser import CurlParser
    from crawlo.network.request import Request
    
    req = CurlParser.to_request('curl https://example.com -H "Accept: text/html"')
    assert isinstance(req, Request)
    assert req.url == 'https://example.com'
    assert req.headers.get('Accept') == 'text/html'
    print("✅ curl to_request 测试通过")


def test_curl_parser_to_request_with_overrides():
    """测试 to_request 覆盖参数"""
    from crawlo.utils.curl_parser import CurlParser
    
    req = CurlParser.to_request('curl https://example.com', meta={'key': 'val'})
    assert req.meta.get('key') == 'val'
    print("✅ curl to_request 覆盖参数测试通过")


# ==================== Checkpoint 测试 ====================


def test_json_storage_save_load():
    """测试 JSON 存储后端的保存和加载"""
    from crawlo.checkpoint.storage import JsonStorage
    
    tmpdir = tempfile.mkdtemp(prefix='crawlo_test_')
    try:
        storage = JsonStorage('test_spider', 'test_project', checkpoint_dir=tmpdir)
        
        data = {
            'project_name': 'test_project',
            'spider_name': 'test_spider',
            'pending_count': 3,
            'requests': [{'url': 'https://a.com'}, {'url': 'https://b.com'}],
            'fingerprints': {'fp1', 'fp2', 'fp3'},
            'stats': {'downloaded': 100},
        }
        
        # 保存
        assert storage.save(data) == True
        assert storage.exists() == True
        
        # 加载
        loaded = storage.load()
        assert loaded is not None
        assert loaded['spider_name'] == 'test_spider'
        assert loaded['pending_count'] == 3
        assert len(loaded['requests']) == 2
        assert loaded['fingerprints'] == {'fp1', 'fp2', 'fp3'}
        assert loaded['stats']['downloaded'] == 100
        
        # 清除
        assert storage.clear() == True
        assert storage.exists() == False
        
        print("✅ JSON 存储保存/加载/清除测试通过")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_sqlite_storage_save_load():
    """测试 SQLite 存储后端的保存和加载"""
    from crawlo.checkpoint.storage import SqliteStorage
    
    tmpdir = tempfile.mkdtemp(prefix='crawlo_test_')
    try:
        storage = SqliteStorage('test_spider', 'test_project', checkpoint_dir=tmpdir)
        
        data = {
            'project_name': 'test_project',
            'spider_name': 'test_spider',
            'pending_count': 2,
            'requests': [{'url': 'https://a.com'}, {'url': 'https://b.com'}],
            'fingerprints': {'fp1', 'fp2'},
            'stats': {'downloaded': 50},
        }
        
        # 保存
        assert storage.save(data) == True
        assert storage.exists() == True
        
        # 加载
        loaded = storage.load()
        assert loaded is not None
        assert loaded['spider_name'] == 'test_spider'
        assert len(loaded['requests']) == 2
        assert loaded['fingerprints'] == {'fp1', 'fp2'}
        
        # 清除
        assert storage.clear() == True
        assert storage.exists() == False
        
        print("✅ SQLite 存储保存/加载/清除测试通过")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_checkpoint_manager_basic():
    """测试 CheckpointManager 基本功能"""
    from crawlo.checkpoint.manager import CheckpointManager
    
    tmpdir = tempfile.mkdtemp(prefix='crawlo_test_')
    try:
        # 创建配置
        try:
            from crawlo.settings.setting_manager import SettingManager
            settings = SettingManager()
            settings.attributes['CHECKPOINT_DIR'] = tmpdir
            settings.attributes['CHECKPOINT_ENABLED'] = True
            settings.attributes['CHECKPOINT_STORAGE'] = 'json'
        except ImportError:
            settings = {'CHECKPOINT_DIR': tmpdir, 'CHECKPOINT_ENABLED': True, 'CHECKPOINT_STORAGE': 'json'}
        
        mgr = CheckpointManager('test_spider', settings)
        assert mgr.enabled == True
        
        # 无检查点
        assert asyncio.run(mgr.has_checkpoint()) == False
        assert asyncio.run(mgr.load()) is None
        
        # 保存
        result = asyncio.run(mgr.save())
        # 无 scheduler，应该保存空数据
        assert result == True
        assert asyncio.run(mgr.has_checkpoint()) == True
        
        # 加载
        data = asyncio.run(mgr.load())
        assert data is not None
        assert data['spider_name'] == 'test_spider'
        assert data['pending_count'] == 0
        
        # 清除
        assert asyncio.run(mgr.clear()) == True
        assert asyncio.run(mgr.has_checkpoint()) == False
        
        print("✅ CheckpointManager 基本功能测试通过")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_checkpoint_manager_disabled():
    """测试 CheckpointManager 禁用时"""
    from crawlo.checkpoint.manager import CheckpointManager
    
    try:
        from crawlo.settings.setting_manager import SettingManager
        settings = SettingManager()
        settings.attributes['CHECKPOINT_ENABLED'] = False
    except ImportError:
        settings = {'CHECKPOINT_ENABLED': False}
    
    mgr = CheckpointManager('test_spider', settings)
    assert mgr.enabled == False
    assert asyncio.run(mgr.has_checkpoint()) == False
    assert asyncio.run(mgr.save()) == False
    print("✅ CheckpointManager 禁用测试通过")


def test_checkpoint_manager_restore_request():
    """测试 CheckpointManager 恢复请求"""
    from crawlo.checkpoint.manager import CheckpointManager
    
    try:
        from crawlo.settings.setting_manager import SettingManager
        settings = SettingManager()
    except ImportError:
        settings = {}
    
    mgr = CheckpointManager('test_spider', settings)
    
    # 简单请求恢复
    req_data = {'url': 'https://example.com', 'method': 'GET'}
    request = mgr.restore_request(req_data)
    assert request is not None
    assert request.url == 'https://example.com'
    
    # 带参数请求恢复
    req_data = {
        'url': 'https://api.example.com',
        'method': 'POST',
        'headers': {'Content-Type': 'application/json'},
        'meta': {'key': 'val'},
        'priority': 5,
    }
    request = mgr.restore_request(req_data)
    assert request is not None
    assert request.method == 'POST'
    assert request.meta.get('key') == 'val'
    
    print("✅ CheckpointManager 请求恢复测试通过")


def test_checkpoint_manager_restore_fingerprints():
    """测试 CheckpointManager 恢复指纹"""
    from crawlo.checkpoint.manager import CheckpointManager
    
    try:
        from crawlo.settings.setting_manager import SettingManager
        settings = SettingManager()
    except ImportError:
        settings = {}
    
    mgr = CheckpointManager('test_spider', settings)
    
    # 创建模拟调度器
    class MockFilter:
        def __init__(self):
            self.fingerprints = set()
    
    class MockScheduler:
        def __init__(self):
            self.dupe_filter = MockFilter()
    
    scheduler = MockScheduler()
    fps = {'fp1', 'fp2', 'fp3'}
    
    result = mgr.restore_fingerprints(fps, scheduler)
    assert result == True
    assert scheduler.dupe_filter.fingerprints == {'fp1', 'fp2', 'fp3'}
    
    print("✅ CheckpointManager 指纹恢复测试通过")


def test_checkpoint_manager_sqlite_backend():
    """测试 CheckpointManager 使用 SQLite 后端"""
    from crawlo.checkpoint.manager import CheckpointManager
    
    tmpdir = tempfile.mkdtemp(prefix='crawlo_test_')
    try:
        try:
            from crawlo.settings.setting_manager import SettingManager
            settings = SettingManager()
            settings.attributes['CHECKPOINT_DIR'] = tmpdir
            settings.attributes['CHECKPOINT_STORAGE'] = 'sqlite'
        except ImportError:
            settings = {'CHECKPOINT_DIR': tmpdir, 'CHECKPOINT_STORAGE': 'sqlite'}
        
        mgr = CheckpointManager('test_spider', settings)
        
        # 保存
        asyncio.run(mgr.save())
        assert asyncio.run(mgr.has_checkpoint()) == True
        
        # 加载
        data = asyncio.run(mgr.load())
        assert data is not None
        assert data['spider_name'] == 'test_spider'
        
        # 清除
        asyncio.run(mgr.clear())
        assert asyncio.run(mgr.has_checkpoint()) == False
        
        print("✅ CheckpointManager SQLite 后端测试通过")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_shell_from_curl():
    """测试 Shell 的 from_curl 方法"""
    from crawlo.shell.core import CrawloShell
    
    shell = CrawloShell()
    
    # 测试 from_curl 解析
    try:
        result = asyncio.run(shell.from_curl('curl https://example.com'))
        # 网络可能不可用，只测试不崩溃
        print("✅ Shell from_curl 网络测试完成" + (" (成功)" if result else " (网络不可达)"))
    except Exception as e:
        print(f"⚠️ Shell from_curl 测试跳过: {e}")


def test_shell_namespace_has_from_curl():
    """测试 Shell 命名空间包含 from_curl"""
    from crawlo.shell.core import CrawloShell
    
    shell = CrawloShell()
    ns = shell.get_namespace()
    assert 'from_curl' in ns
    assert callable(ns['from_curl'])
    print("✅ Shell 命名空间 from_curl 测试通过")


# ==================== 主测试运行 ====================

if __name__ == '__main__':
    tests = [
        # curl_parser
        test_curl_parser_basic,
        test_curl_parser_post_json,
        test_curl_parser_headers,
        test_curl_parser_cookies,
        test_curl_parser_auth,
        test_curl_parser_flags,
        test_curl_parser_timeout,
        test_curl_parser_proxy,
        test_curl_parser_head,
        test_curl_parser_data_auto_post,
        test_curl_parser_form_data,
        test_curl_parser_multiline,
        test_curl_parser_no_url,
        test_curl_parser_empty,
        test_curl_parser_to_request,
        test_curl_parser_to_request_with_overrides,
        # checkpoint storage
        test_json_storage_save_load,
        test_sqlite_storage_save_load,
        # checkpoint manager
        test_checkpoint_manager_basic,
        test_checkpoint_manager_disabled,
        test_checkpoint_manager_restore_request,
        test_checkpoint_manager_restore_fingerprints,
        test_checkpoint_manager_sqlite_backend,
        # shell integration
        test_shell_namespace_has_from_curl,
        test_shell_from_curl,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"❌ {test.__name__} 失败: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print(f"\n{'='*60}")
    print(f"  测试结果: {passed} 通过, {failed} 失败, 共 {passed + failed} 个")
    print(f"{'='*60}")
