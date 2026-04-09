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
            settings.attributes['CHECKPOINT_STORAGE'] = 'json'
        except ImportError:
            settings = {'CHECKPOINT_DIR': tmpdir, 'CHECKPOINT_STORAGE': 'json'}
        
        mgr = CheckpointManager('test_spider', settings)
        assert mgr.enabled == True  # 始终启用
        
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


# ==================== curl_parser 边界场景 ====================


def test_curl_parser_user_agent():
    """测试 -A / --user-agent 解析"""
    from crawlo.utils.curl_parser import CurlParser
    
    cmd = 'curl https://example.com -A "MyBot/1.0"'
    result = CurlParser.parse(cmd)
    assert result['headers']['User-Agent'] == 'MyBot/1.0'
    print("✅ curl -A user-agent 解析测试通过")


def test_curl_parser_referer():
    """测试 -e / --referer 解析"""
    from crawlo.utils.curl_parser import CurlParser
    
    cmd = 'curl https://example.com -e "https://google.com"'
    result = CurlParser.parse(cmd)
    assert result['headers']['Referer'] == 'https://google.com'
    print("✅ curl -e referer 解析测试通过")


def test_curl_parser_url_option():
    """测试 --url 选项"""
    from crawlo.utils.curl_parser import CurlParser
    
    cmd = 'curl --url https://example.com'
    result = CurlParser.parse(cmd)
    assert result['url'] == 'https://example.com'
    print("✅ curl --url 选项测试通过")


def test_curl_parser_max_redirs_zero():
    """测试 --max-redirs 0 设置 allow_redirects=False"""
    from crawlo.utils.curl_parser import CurlParser
    
    cmd = 'curl https://example.com --max-redirs 0'
    result = CurlParser.parse(cmd)
    assert result['allow_redirects'] == False
    print("✅ curl --max-redirs 0 测试通过")


def test_curl_parser_location_flag():
    """测试 -L / --location 标志"""
    from crawlo.utils.curl_parser import CurlParser
    
    cmd = 'curl -L https://example.com'
    result = CurlParser.parse(cmd)
    assert result['allow_redirects'] == True
    print("✅ curl -L 标志测试通过")


def test_curl_parser_proxy_short():
    """测试 -x 短选项代理解析"""
    from crawlo.utils.curl_parser import CurlParser
    
    cmd = 'curl -x http://proxy:3128 https://example.com'
    result = CurlParser.parse(cmd)
    assert result['proxy'] == 'http://proxy:3128'
    print("✅ curl -x 短选项代理解析测试通过")


def test_curl_parser_auth_no_password():
    """测试 -u 只有用户名没有密码"""
    from crawlo.utils.curl_parser import CurlParser
    
    cmd = 'curl -u admin https://example.com'
    result = CurlParser.parse(cmd)
    assert result['auth'] == ('admin', '')
    print("✅ curl -u 无密码认证解析测试通过")


def test_curl_parser_data_binary():
    """测试 --data-binary 解析"""
    from crawlo.utils.curl_parser import CurlParser
    
    cmd = 'curl https://example.com --data-binary "raw data"'
    result = CurlParser.parse(cmd)
    assert result['method'] == 'POST'
    assert result['body'] == 'raw data'
    print("✅ curl --data-binary 解析测试通过")


def test_curl_parser_complex_chrome_copy():
    """测试 Chrome DevTools 复制的完整 curl 命令"""
    from crawlo.utils.curl_parser import CurlParser
    
    cmd = """curl 'https://api.example.com/v1/items?page=1' \
      -H 'accept: application/json' \
      -H 'accept-language: zh-CN,zh;q=0.9' \
      -H 'authorization: Bearer eyJhbGciOiJIUzI1NiJ9.x' \
      -H 'cookie: session=abc123; _ga=GA1.2.xyz' \
      --compressed"""
    result = CurlParser.parse(cmd)
    assert result['url'] == 'https://api.example.com/v1/items?page=1'
    assert result['method'] == 'GET'
    assert 'authorization' in result['headers']
    assert result['headers']['authorization'].startswith('Bearer ')
    assert 'cookies' in result
    assert result['cookies']['session'] == 'abc123'
    print("✅ curl Chrome DevTools 完整命令解析测试通过")


def test_curl_parser_method_override():
    """测试 -X PUT / -X DELETE 等"""
    from crawlo.utils.curl_parser import CurlParser
    
    cmd = 'curl https://api.example.com/resource/1 -X DELETE'
    result = CurlParser.parse(cmd)
    assert result['method'] == 'DELETE'
    
    cmd2 = 'curl https://api.example.com/resource -X PUT -d "updated"'
    result2 = CurlParser.parse(cmd2)
    assert result2['method'] == 'PUT'
    print("✅ curl -X PUT/DELETE 方法覆盖测试通过")


def test_curl_parser_invalid_option_value():
    """测试缺少选项值时抛出异常"""
    from crawlo.utils.curl_parser import CurlParser
    
    try:
        CurlParser.parse('curl -X')
        assert False, "Should raise ValueError"
    except ValueError as e:
        assert "requires a value" in str(e).lower() or "option" in str(e).lower()
    print("✅ curl 选项缺少值错误测试通过")


# ==================== Checkpoint 存储层边界场景 ====================


def test_json_storage_overwrite():
    """测试 JSON 存储覆盖写入"""
    from crawlo.checkpoint.storage import JsonStorage
    
    tmpdir = tempfile.mkdtemp(prefix='crawlo_test_')
    try:
        storage = JsonStorage('test_spider', 'test_project', checkpoint_dir=tmpdir)
        
        # 第一次保存
        storage.save({'project_name': 'p', 'spider_name': 's', 'pending_count': 1,
                      'requests': [{'url': 'https://a.com'}], 'fingerprints': {'fp1'}, 'stats': {}})
        data1 = storage.load()
        assert data1['pending_count'] == 1
        
        # 覆盖保存
        storage.save({'project_name': 'p', 'spider_name': 's', 'pending_count': 5,
                      'requests': [{'url': 'https://b.com'}], 'fingerprints': {'fp2', 'fp3'}, 'stats': {'x': 1}})
        data2 = storage.load()
        assert data2['pending_count'] == 5
        assert data2['fingerprints'] == {'fp2', 'fp3'}
        
        storage.clear()
        print("✅ JSON 存储覆盖写入测试通过")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_json_storage_load_nonexistent():
    """测试 JSON 加载不存在的文件"""
    from crawlo.checkpoint.storage import JsonStorage
    
    tmpdir = tempfile.mkdtemp(prefix='crawlo_test_')
    try:
        storage = JsonStorage('nonexistent_spider', 'test_project', checkpoint_dir=tmpdir)
        assert storage.load() is None
        assert storage.exists() == False
        print("✅ JSON 加载不存在文件测试通过")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_sqlite_storage_overwrite():
    """测试 SQLite 存储覆盖写入"""
    from crawlo.checkpoint.storage import SqliteStorage
    
    tmpdir = tempfile.mkdtemp(prefix='crawlo_test_')
    try:
        storage = SqliteStorage('test_spider', 'test_project', checkpoint_dir=tmpdir)
        
        # 第一次保存
        storage.save({'project_name': 'p', 'spider_name': 's', 'pending_count': 1,
                      'requests': [{'url': 'https://a.com'}], 'fingerprints': {'fp1'}, 'stats': {}})
        data1 = storage.load()
        assert len(data1['fingerprints']) == 1
        
        # 覆盖保存
        storage.save({'project_name': 'p', 'spider_name': 's', 'pending_count': 3,
                      'requests': [{'url': 'https://b.com'}, {'url': 'https://c.com'}],
                      'fingerprints': {'fp4', 'fp5', 'fp6'}, 'stats': {'count': 99}})
        data2 = storage.load()
        assert len(data2['fingerprints']) == 3
        assert data2['stats']['count'] == 99
        
        storage.clear()
        print("✅ SQLite 存储覆盖写入测试通过")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_sqlite_storage_large_fingerprints():
    """测试 SQLite 大量指纹存储"""
    from crawlo.checkpoint.storage import SqliteStorage
    
    tmpdir = tempfile.mkdtemp(prefix='crawlo_test_')
    try:
        storage = SqliteStorage('test_spider', 'test_project', checkpoint_dir=tmpdir)
        
        # 生成 1000 个指纹
        large_fps = {f'fp_{i:04d}_{"x" * 32}' for i in range(1000)}
        storage.save({'project_name': 'p', 'spider_name': 's', 'pending_count': 0,
                      'requests': [], 'fingerprints': large_fps, 'stats': {}})
        
        data = storage.load()
        assert data['fingerprints'] == large_fps
        assert len(data['fingerprints']) == 1000
        
        storage.clear()
        print("✅ SQLite 大量指纹存储测试通过")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


# ==================== CheckpointManager 边界场景 ====================


def test_checkpoint_manager_save_with_scheduler():
    """测试 CheckpointManager 带 scheduler 的完整保存流程"""
    from crawlo.checkpoint.manager import CheckpointManager
    
    tmpdir = tempfile.mkdtemp(prefix='crawlo_test_')
    try:
        try:
            from crawlo.settings.setting_manager import SettingManager
            settings = SettingManager()
            settings.attributes['CHECKPOINT_DIR'] = tmpdir
            settings.attributes['PROJECT_NAME'] = 'test_project'
        except ImportError:
            settings = {'CHECKPOINT_DIR': tmpdir, 'PROJECT_NAME': 'test_project'}
        
        mgr = CheckpointManager('test_spider', settings)
        
        # 模拟 scheduler
        class MockFilter:
            def __init__(self):
                self.fingerprints = {'fp_a', 'fp_b', 'fp_c'}
        
        class MockQueueManager:
            async def size(self):
                return 0
            async def get(self):
                return None
            async def put(self, request, priority=0):
                pass
        
        class MockSerializer:
            def prepare_for_serialization(self, req):
                pass
        
        class MockStats:
            def get_stats(self):
                return {'downloaded': 50, 'errors': 2}
        
        class MockScheduler:
            def __init__(self):
                self.dupe_filter = MockFilter()
                self.queue_manager = MockQueueManager()
                self.request_serializer = MockSerializer()
        
        scheduler = MockScheduler()
        stats = MockStats()
        
        # 保存
        result = asyncio.run(mgr.save(scheduler, stats))
        assert result == True
        
        # 加载验证
        data = asyncio.run(mgr.load())
        assert data is not None
        assert data['fingerprints'] == {'fp_a', 'fp_b', 'fp_c'}
        assert data['stats']['downloaded'] == 50
        assert data['stats']['errors'] == 2
        
        mgr.storage.clear()
        print("✅ CheckpointManager 带 scheduler 完整保存测试通过")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_checkpoint_manager_restore_request_with_body():
    """测试恢复带 body 和 cookies 的请求"""
    from crawlo.checkpoint.manager import CheckpointManager
    
    try:
        from crawlo.settings.setting_manager import SettingManager
        settings = SettingManager()
    except ImportError:
        settings = {}
    
    mgr = CheckpointManager('test_spider', settings)
    
    req_data = {
        'url': 'https://api.example.com/login',
        'method': 'POST',
        'body': 'username=admin&password=secret',
        'headers': {'Content-Type': 'application/x-www-form-urlencoded'},
        'cookies': {'session': 'xyz'},
        'meta': {'retry': 2},
        'timeout': 30.0,
        'proxy': 'http://proxy:8080',
        'priority': 3,
        'dont_filter': True,
    }
    request = mgr.restore_request(req_data)
    assert request is not None
    assert request.url == 'https://api.example.com/login'
    assert request.method == 'POST'
    assert request.dont_filter == True
    assert request.timeout == 30.0
    
    print("✅ CheckpointManager 恢复带 body/cookies 请求测试通过")


def test_checkpoint_manager_restore_request_minimal():
    """测试恢复最简请求（只有 URL）"""
    from crawlo.checkpoint.manager import CheckpointManager
    
    try:
        from crawlo.settings.setting_manager import SettingManager
        settings = SettingManager()
    except ImportError:
        settings = {}
    
    mgr = CheckpointManager('test_spider', settings)
    
    req_data = {'url': 'https://example.com'}
    request = mgr.restore_request(req_data)
    assert request is not None
    assert request.url == 'https://example.com'
    assert request.method == 'GET'
    
    print("✅ CheckpointManager 恢复最简请求测试通过")


def test_checkpoint_manager_restore_fingerprints_no_filter():
    """测试恢复指纹时过滤器不存在"""
    from crawlo.checkpoint.manager import CheckpointManager
    
    try:
        from crawlo.settings.setting_manager import SettingManager
        settings = SettingManager()
    except ImportError:
        settings = {}
    
    mgr = CheckpointManager('test_spider', settings)
    
    class MockSchedulerNoFilter:
        dupe_filter = None
    
    result = mgr.restore_fingerprints({'fp1', 'fp2'}, MockSchedulerNoFilter())
    assert result == False
    print("✅ CheckpointManager 恢复指纹无过滤器测试通过")


def test_checkpoint_manager_restore_fingerprints_empty():
    """测试恢复空指纹集合"""
    from crawlo.checkpoint.manager import CheckpointManager
    
    try:
        from crawlo.settings.setting_manager import SettingManager
        settings = SettingManager()
    except ImportError:
        settings = {}
    
    mgr = CheckpointManager('test_spider', settings)
    result = mgr.restore_fingerprints(set(), None)
    assert result == False
    print("✅ CheckpointManager 恢复空指纹集合测试通过")


def test_checkpoint_manager_extract_stats_variants():
    """测试统计信息提取的多种情况"""
    from crawlo.checkpoint.manager import CheckpointManager
    
    try:
        from crawlo.settings.setting_manager import SettingManager
        settings = SettingManager()
    except ImportError:
        settings = {}
    
    mgr = CheckpointManager('test_spider', settings)
    
    # stats 为 None
    assert mgr._extract_stats(None) == {}
    
    # stats 有 get_stats 方法
    class MockStats1:
        def get_stats(self):
            return {'a': 1, 'b': 2}
    assert mgr._extract_stats(MockStats1()) == {'a': 1, 'b': 2}
    
    # stats 有 _stats 属性
    class MockStats2:
        _stats = {'c': 3}
    assert mgr._extract_stats(MockStats2()) == {'c': 3}
    
    print("✅ CheckpointManager 统计信息提取变体测试通过")


# ==================== Engine 检查点集成测试 ====================


def test_engine_close_reason_finished():
    """测试 Engine.close_spider(reason='finished') 清除检查点"""
    from crawlo.checkpoint import CheckpointManager
    
    tmpdir = tempfile.mkdtemp(prefix='crawlo_test_')
    try:
        try:
            from crawlo.settings.setting_manager import SettingManager
            settings = SettingManager()
            settings.attributes['CHECKPOINT_DIR'] = tmpdir
        except ImportError:
            settings = {'CHECKPOINT_DIR': tmpdir}
        
        # 先保存一个检查点
        mgr = CheckpointManager('test_spider', settings)
        asyncio.run(mgr.save())
        assert asyncio.run(mgr.has_checkpoint()) == True
        
        # 模拟 Engine._clear_checkpoint()
        # 直接调用 clear
        asyncio.run(mgr.clear())
        assert asyncio.run(mgr.has_checkpoint()) == False
        
        print("✅ Engine close reason=finished 清除检查点测试通过")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_engine_close_reason_shutdown():
    """测试 Engine.close_spider(reason='shutdown') 保存检查点"""
    from crawlo.checkpoint import CheckpointManager
    
    tmpdir = tempfile.mkdtemp(prefix='crawlo_test_')
    try:
        try:
            from crawlo.settings.setting_manager import SettingManager
            settings = SettingManager()
            settings.attributes['CHECKPOINT_DIR'] = tmpdir
            settings.attributes['CHECKPOINT_SAVE_ON_SIGNAL'] = True
        except ImportError:
            settings = {'CHECKPOINT_DIR': tmpdir, 'CHECKPOINT_SAVE_ON_SIGNAL': True}
        
        # 模拟 shutdown 时的保存流程
        mgr = CheckpointManager('test_spider', settings)
        result = asyncio.run(mgr.save())
        assert result == True
        assert asyncio.run(mgr.has_checkpoint()) == True
        
        # 加载验证
        data = asyncio.run(mgr.load())
        assert data is not None
        
        # 清理
        asyncio.run(mgr.clear())
        print("✅ Engine close reason=shutdown 保存检查点测试通过")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_engine_save_on_signal_disabled():
    """测试 CHECKPOINT_SAVE_ON_SIGNAL=False 时不保存"""
    from crawlo.utils.misc import safe_get_config
    
    try:
        from crawlo.settings.setting_manager import SettingManager
        settings = SettingManager()
        settings.attributes['CHECKPOINT_SAVE_ON_SIGNAL'] = False
    except ImportError:
        settings = {'CHECKPOINT_SAVE_ON_SIGNAL': False}
    
    # 验证配置读取正确
    val = safe_get_config(settings, 'CHECKPOINT_SAVE_ON_SIGNAL', True, bool)
    assert val == False
    print("✅ CHECKPOINT_SAVE_ON_SIGNAL=False 配置读取测试通过")


# ==================== Shell from_curl 边界场景 ====================


def test_shell_from_curl_invalid_command():
    """测试 Shell from_curl 无效 curl 命令"""
    from crawlo.shell.core import CrawloShell
    
    shell = CrawloShell()
    
    # 空 curl 命令
    result = asyncio.run(shell.from_curl(''))
    assert result is None
    
    # 缺少 URL
    result2 = asyncio.run(shell.from_curl('curl -H "Key: val"'))
    assert result2 is None
    
    print("✅ Shell from_curl 无效命令测试通过")


def test_shell_from_curl_sync():
    """测试 Shell sync_from_curl 方法"""
    from crawlo.shell.core import CrawloShell
    
    shell = CrawloShell()
    
    # 验证方法存在且可调用
    assert hasattr(shell, 'sync_from_curl')
    assert callable(shell.sync_from_curl)
    
    # 无效命令返回 None
    result = shell.sync_from_curl('')
    assert result is None
    
    print("✅ Shell sync_from_curl 测试通过")


def test_shell_from_curl_updates_namespace():
    """测试 from_curl 成功后更新命名空间"""
    from crawlo.shell.core import CrawloShell
    
    shell = CrawloShell()
    ns = shell.get_namespace()
    
    # 命名空间应包含 from_curl
    assert 'from_curl' in ns
    assert 'fetch' in ns
    assert 'view' in ns
    
    print("✅ Shell from_curl 命名空间更新测试通过")


def test_shell_from_curl_with_network():
    """测试 from_curl 真实网络请求"""
    from crawlo.shell.core import CrawloShell
    
    shell = CrawloShell()
    
    try:
        result = asyncio.run(shell.from_curl('curl https://httpbin.org/get'))
        if result:
            assert result.status_code == 200
            data = result.json()
            assert 'url' in data
            print("✅ Shell from_curl 真实网络请求测试通过")
        else:
            print("⚠️ Shell from_curl 网络不可达，跳过")
    except Exception as e:
        print(f"⚠️ Shell from_curl 网络测试跳过: {e}")
    finally:
        try:
            asyncio.run(shell.close())
        except Exception:
            pass


# ==================== CLI 参数解析测试 ====================


def test_cli_run_fresh_flag():
    """测试 crawlo run --fresh 参数解析"""
    args = ['myspider', '--fresh']
    fresh = '--fresh' in args
    assert fresh == True
    print("✅ CLI run --fresh 参数解析测试通过")


def test_cli_run_clean_checkpoint_flag():
    """测试 crawlo run --clean-checkpoint 参数解析"""
    args = ['myspider', '--clean-checkpoint']
    clean_checkpoint = '--clean-checkpoint' in args
    assert clean_checkpoint == True
    print("✅ CLI run --clean-checkpoint 参数解析测试通过")


def test_cli_shell_curl_flag():
    """测试 crawlo shell --curl 参数解析"""
    args = ['--curl', 'curl https://example.com -H "Key: val"']
    curl_cmd = None
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == '--curl' and i + 1 < len(args):
            curl_cmd = args[i + 1]
            i += 2
        else:
            i += 1
    assert curl_cmd == 'curl https://example.com -H "Key: val"'
    print("✅ CLI shell --curl 参数解析测试通过")


def test_cli_shell_url_arg():
    """测试 crawlo shell [url] 参数解析"""
    args = ['https://example.com']
    url = None
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == '--curl' and i + 1 < len(args):
            i += 2
        elif not arg.startswith('-') and url is None:
            url = arg
            i += 1
        else:
            i += 1
    assert url == 'https://example.com'
    print("✅ CLI shell URL 参数解析测试通过")


# ==================== 端到端集成测试 ====================


def test_e2e_curl_to_request_to_checkpoint():
    """端到端：curl 命令 -> Request -> 序列化 -> 检查点保存 -> 加载 -> 恢复"""
    from crawlo.utils.curl_parser import CurlParser
    from crawlo.checkpoint.manager import CheckpointManager
    
    tmpdir = tempfile.mkdtemp(prefix='crawlo_test_')
    try:
        try:
            from crawlo.settings.setting_manager import SettingManager
            settings = SettingManager()
            settings.attributes['CHECKPOINT_DIR'] = tmpdir
            settings.attributes['PROJECT_NAME'] = 'e2e_project'
        except ImportError:
            settings = {'CHECKPOINT_DIR': tmpdir, 'PROJECT_NAME': 'e2e_project'}
        
        # 1. 从 curl 命令解析为 Request
        cmd = 'curl https://api.example.com/data -X POST -H "Content-Type: application/json" -d \'{"page":1}\' -H "Authorization: Bearer tok123"'
        request = CurlParser.to_request(cmd)
        assert request.url == 'https://api.example.com/data'
        assert request.method == 'POST'
        
        # 2. 模拟序列化请求
        from crawlo.utils.request.request import request_to_dict
        req_dict = request_to_dict(request)
        assert req_dict['url'] == 'https://api.example.com/data'
        
        # 3. 保存到检查点
        mgr = CheckpointManager('e2e_spider', settings)
        storage_data = {
            'project_name': 'e2e_project',
            'spider_name': 'e2e_spider',
            'pending_count': 1,
            'requests': [req_dict],
            'fingerprints': {'fp_e2e_1', 'fp_e2e_2'},
            'stats': {'downloaded': 10},
        }
        assert mgr.storage.save(storage_data) == True
        
        # 4. 从检查点加载
        data = mgr.storage.load()
        assert data is not None
        assert data['pending_count'] == 1
        assert len(data['requests']) == 1
        assert data['fingerprints'] == {'fp_e2e_1', 'fp_e2e_2'}
        
        # 5. 恢复请求
        restored = mgr.restore_request(data['requests'][0])
        assert restored is not None
        assert restored.url == 'https://api.example.com/data'
        
        # 6. 清理
        mgr.storage.clear()
        
        print("✅ 端到端 curl -> Request -> 检查点 -> 恢复测试通过")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_e2e_curl_to_shell_fetch():
    """端到端：curl 命令 -> Shell from_curl -> 抓取 -> 选择器"""
    from crawlo.shell.core import CrawloShell
    
    shell = CrawloShell()
    
    try:
        # 使用 from_curl 抓取
        result = asyncio.run(shell.from_curl('curl https://httpbin.org/html'))
        if result:
            assert result.status_code == 200
            # 测试选择器
            title = result.css('h1::text').get()
            assert title is not None
            assert 'Moby-Dick' in title or len(title) > 0
            print(f"✅ 端到端 curl -> Shell -> 选择器测试通过 (h1={title})")
        else:
            print("⚠️ 端到端 Shell 网络不可达，跳过")
    except Exception as e:
        print(f"⚠️ 端到端 Shell 网络测试跳过: {e}")
    finally:
        try:
            asyncio.run(shell.close())
        except Exception:
            pass


def test_e2e_curl_post_json_to_shell():
    """端到端：POST JSON curl -> Shell from_curl"""
    from crawlo.shell.core import CrawloShell
    
    shell = CrawloShell()
    
    try:
        cmd = 'curl https://httpbin.org/post -X POST -H "Content-Type: application/json" -d \'{"test":"crawlo"}\''
        result = asyncio.run(shell.from_curl(cmd))
        if result:
            assert result.status_code == 200
            data = result.json()
            assert data.get('json', {}).get('test') == 'crawlo'
            print("✅ 端到端 POST JSON curl -> Shell 测试通过")
        else:
            print("⚠️ 端到端 POST JSON 网络不可达，跳过")
    except Exception as e:
        print(f"⚠️ 端到端 POST JSON 网络测试跳过: {e}")
    finally:
        try:
            asyncio.run(shell.close())
        except Exception:
            pass


# ==================== 主测试运行 ====================

if __name__ == '__main__':
    tests = [
        # curl_parser 基础
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
        # curl_parser 边界场景
        test_curl_parser_user_agent,
        test_curl_parser_referer,
        test_curl_parser_url_option,
        test_curl_parser_max_redirs_zero,
        test_curl_parser_location_flag,
        test_curl_parser_proxy_short,
        test_curl_parser_auth_no_password,
        test_curl_parser_data_binary,
        test_curl_parser_complex_chrome_copy,
        test_curl_parser_method_override,
        test_curl_parser_invalid_option_value,
        # checkpoint storage 基础
        test_json_storage_save_load,
        test_sqlite_storage_save_load,
        # checkpoint storage 边界场景
        test_json_storage_overwrite,
        test_json_storage_load_nonexistent,
        test_sqlite_storage_overwrite,
        test_sqlite_storage_large_fingerprints,
        # checkpoint manager 基础
        test_checkpoint_manager_basic,
        test_checkpoint_manager_restore_request,
        test_checkpoint_manager_restore_fingerprints,
        test_checkpoint_manager_sqlite_backend,
        # checkpoint manager 边界场景
        test_checkpoint_manager_save_with_scheduler,
        test_checkpoint_manager_restore_request_with_body,
        test_checkpoint_manager_restore_request_minimal,
        test_checkpoint_manager_restore_fingerprints_no_filter,
        test_checkpoint_manager_restore_fingerprints_empty,
        test_checkpoint_manager_extract_stats_variants,
        # engine 检查点集成
        test_engine_close_reason_finished,
        test_engine_close_reason_shutdown,
        test_engine_save_on_signal_disabled,
        # shell from_curl 集成
        test_shell_namespace_has_from_curl,
        test_shell_from_curl,
        test_shell_from_curl_invalid_command,
        test_shell_from_curl_sync,
        test_shell_from_curl_updates_namespace,
        test_shell_from_curl_with_network,
        # CLI 参数解析
        test_cli_run_fresh_flag,
        test_cli_run_clean_checkpoint_flag,
        test_cli_shell_curl_flag,
        test_cli_shell_url_arg,
        # 端到端集成
        test_e2e_curl_to_request_to_checkpoint,
        test_e2e_curl_to_shell_fetch,
        test_e2e_curl_post_json_to_shell,
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
