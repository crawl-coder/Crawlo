#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
develop 分支修复验证测试

验证本次修复的关键问题：
1. Item 动态字段类级污染 Bug
2. pickle 默认序列化 RCE 风险
3. ACK/NACK 不再静默吞错
4. 信号量 release 对称性
5. 种子锁 Lua 脚本存在
6. 代码质量清理（无 or True / 无 print）
"""
import asyncio
import os
import sys

# 确保项目根目录在 path 中
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# ============================================================================
# 1. Item 动态字段类级污染 Bug 修复验证
# ============================================================================

def test_item_dynamic_field_no_class_pollution():
    """动态字段不应污染类级 FIELDS"""
    from crawlo.items.item import Item
    from crawlo.items.fields import Field

    class TestItem(Item):
        name = Field()

    # 实例 A 设置动态字段
    item_a = TestItem()
    item_a['name'] = 'a_name'
    item_a['dynamic_a'] = 'value_a'

    # 实例 B 不应有 dynamic_a
    item_b = TestItem()
    assert 'dynamic_a' not in TestItem.FIELDS, "动态字段污染了类级 FIELDS"
    assert 'dynamic_a' not in item_b._values, "动态字段泄露到其他实例"

    # item_b 可以设置不同的动态字段
    item_b['dynamic_b'] = 'value_b'
    assert 'dynamic_b' not in item_a._values, "dynamic_b 不应出现在 item_a"
    assert item_a['dynamic_a'] == 'value_a'
    assert item_b['dynamic_b'] == 'value_b'

    print("  [OK] Item 动态字段无类级污染")


def test_item_dynamic_field_values_isolated():
    """多次设置动态字段，FIELDS 不应无限增长"""
    from crawlo.items.item import Item
    from crawlo.items.fields import Field

    class TestItem(Item):
        fixed = Field()

    initial_fields_count = len(TestItem.FIELDS)

    # 设置 100 个不同的动态字段
    for i in range(100):
        item = TestItem()
        item[f'dyn_{i}'] = i

    # FIELDS 不应增长
    assert len(TestItem.FIELDS) == initial_fields_count, (
        f"FIELDS 增长了: {initial_fields_count} -> {len(TestItem.FIELDS)}"
    )
    print("  [OK] FIELDS 不会因动态字段无限增长")


# ============================================================================
# 2. pickle 默认序列化 RCE 风险修复验证
# ============================================================================

def test_default_serialization_is_json():
    """默认序列化格式应为 json，不是 pickle"""
    from crawlo.settings.default_settings import QUEUE_SERIALIZATION_FORMAT
    assert QUEUE_SERIALIZATION_FORMAT == 'json', (
        f"默认序列化应为 json，实际为 {QUEUE_SERIALIZATION_FORMAT}"
    )
    assert QUEUE_SERIALIZATION_FORMAT != 'pickle', "默认序列化不应是 pickle（RCE 风险）"
    print("  [OK] 默认序列化格式为 json（安全）")


# ============================================================================
# 3. ACK/NACK 不再静默吞错验证
# ============================================================================

def test_ack_message_logs_on_failure():
    """_ack_message 失败时应记录日志而非静默吞错"""
    from crawlo.core.engine_cluster import _ack_message

    class FakeStats:
        def __init__(self):
            self.counts = {}
        def inc_value(self, key):
            self.counts[key] = self.counts.get(key, 0) + 1

    class FakeCrawler:
        def __init__(self):
            self.stats = FakeStats()

    class FakeEngine:
        def __init__(self):
            self._cluster_worker_id = 'worker_1'
            self.scheduler = None  # 触发早期返回路径
            self.crawler = FakeCrawler()
            class _L:
                def warning(self, *a, **k): pass
                def debug(self, *a, **k): pass
                def info(self, *a, **k): pass
                def error(self, *a, **k): pass
            self.logger = _L()

    class FakeRequest:
        def __init__(self):
            self.meta = {'__stream_message_id': 'msg_123'}

    # 测试 scheduler 为 None 时直接返回（不抛错）
    engine = FakeEngine()
    engine.scheduler = None
    asyncio.get_event_loop().run_until_complete(
        _ack_message(FakeRequest(), engine, success=True)
    )

    # 测试有 scheduler 但 ack 抛异常时，记录日志
    class FailingScheduler:
        async def ack_request(self, msg_id):
            raise RuntimeError("Redis connection lost")

    engine.scheduler = FailingScheduler()
    asyncio.get_event_loop().run_until_complete(
        _ack_message(FakeRequest(), engine, success=True)
    )

    # 验证统计计数
    assert engine.crawler.stats.counts.get('scheduler/ack_failure_count', 0) >= 1, (
        f"ACK 失败应增加 ack_failure_count，实际: {engine.crawler.stats.counts}"
    )
    print("  [OK] ACK/NACK 失败不再静默吞错，记录统计")


# ============================================================================
# 4. 信号量 release 对称性验证
# ============================================================================

def test_semaphore_released_on_invalid_dequeue():
    """反序列化失败返回 None 时，信号量应仍被释放"""
    from crawlo.queue.queue_manager import QueueManager
    from crawlo.queue.queue_types import QueueType
    from crawlo.queue.config import QueueConfig

    # 构造内存队列配置
    class FakeSettings:
        def get(self, key, default=None):
            return default
        def get_int(self, key, default=0):
            return default

    config = QueueConfig()
    config.queue_type = QueueType.MEMORY
    config.max_queue_size = 5
    config.settings = FakeSettings()

    qm = QueueManager(config)

    async def run():
        await qm.initialize()
        # 手动注入一个无效元素（非 Request 的 tuple）
        await qm._queue.put((0, "not_a_request"))

        # 获取前信号量状态
        sem_before = qm._queue_semaphore._value if qm._queue_semaphore else None

        result = await qm.get()

        # 获取后信号量状态
        sem_after = qm._queue_semaphore._value if qm._queue_semaphore else None

        assert result is None, "无效元素应返回 None"
        assert sem_before is not None, "信号量应存在"
        assert sem_after == sem_before + 1, (
            f"信号量应被释放 (+1)，before={sem_before}, after={sem_after}"
        )
        await qm.close()

    asyncio.get_event_loop().run_until_complete(run())
    print("  [OK] 信号量在反序列化失败时仍被释放")


# ============================================================================
# 5. 种子锁 Lua 脚本存在验证
# ============================================================================

def test_seed_lock_lua_script_exists():
    """Engine 应有种子锁的 Lua 脚本和原子获取方法"""
    from crawlo.core.engine import Engine

    assert hasattr(Engine, '_SEED_LOCK_LUA'), "Engine 缺少 _SEED_LOCK_LUA 脚本"
    assert hasattr(Engine, '_try_acquire_seed_lock_atomic'), (
        "Engine 缺少 _try_acquire_seed_lock_atomic 方法"
    )

    lua_script = Engine._SEED_LOCK_LUA
    assert 'redis.call' in lua_script, "Lua 脚本应包含 redis.call"
    assert 'DEL' in lua_script, "Lua 脚本应包含死锁清理 DEL"
    assert 'SET' in lua_script, "Lua 脚本应包含 SET 抢占"
    print("  [OK] 种子锁 Lua 脚本存在且包含原子清理逻辑")


# ============================================================================
# 6. 代码质量清理验证
# ============================================================================

def test_no_or_true_in_queue_manager():
    """queue_manager.py 不应再有 `or True` 调试残留"""
    qm_path = os.path.join(PROJECT_ROOT, 'crawlo', 'queue', 'queue_manager.py')
    with open(qm_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 检查 `or True` 模式（排除字符串内的）
    lines = content.split('\n')
    for i, line in enumerate(lines, 1):
        stripped = line.split('#')[0]  # 去掉注释
        if 'or True' in stripped:
            raise AssertionError(f"queue_manager.py:{i} 仍含 `or True`: {line.strip()}")
    print("  [OK] queue_manager.py 无 `or True` 调试残留")


def test_no_print_in_framework():
    """framework.py 不应再用 print 输出警告"""
    fw_path = os.path.join(PROJECT_ROOT, 'crawlo', 'framework.py')
    with open(fw_path, 'r', encoding='utf-8') as f:
        content = f.read()

    lines = content.split('\n')
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        # 跳过注释和字符串内的 print
        if stripped.startswith('#'):
            continue
        if stripped.startswith('print(') and 'print(' in stripped:
            raise AssertionError(f"framework.py:{i} 仍使用 print: {line.strip()}")
    print("  [OK] framework.py 无 print 警告输出")


def test_license_consistency():
    """setup.cfg license 应一致（BSD）"""
    cfg_path = os.path.join(PROJECT_ROOT, 'setup.cfg')
    with open(cfg_path, 'r', encoding='utf-8') as f:
        content = f.read()

    assert 'BSD License' in content or 'BSD-3-Clause' in content, (
        "setup.cfg 应声明 BSD License"
    )
    assert 'MIT License' not in content, "setup.cfg 不应再有 MIT License（与 BSD 矛盾）"
    print("  [OK] setup.cfg License 一致 (BSD)")


def test_no_aioredis_dependency():
    """setup.cfg 不应再依赖已废弃的 aioredis"""
    cfg_path = os.path.join(PROJECT_ROOT, 'setup.cfg')
    with open(cfg_path, 'r', encoding='utf-8') as f:
        content = f.read()

    lines = content.split('\n')
    for i, line in enumerate(lines, 1):
        if 'aioredis' in line and not line.strip().startswith('#'):
            raise AssertionError(f"setup.cfg:{i} 仍依赖 aioredis: {line.strip()}")
    print("  [OK] setup.cfg 不再依赖废弃的 aioredis")


def test_no_emoji_in_engine_log():
    """engine.py 日志不应包含 emoji"""
    eng_path = os.path.join(PROJECT_ROOT, 'crawlo', 'core', 'engine.py')
    with open(eng_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 检查 logger 调用中是否含 emoji（⚠️ 等）
    import re
    # 匹配 logger.xxx("...emoji...") 或 logger.xxx('...emoji...')
    emoji_pattern = re.compile(r'[\U0001F000-\U0001FAFF\u2600-\u27BF]')
    lines = content.split('\n')
    for i, line in enumerate(lines, 1):
        if 'logger.' in line and emoji_pattern.search(line):
            raise AssertionError(f"engine.py:{i} 日志含 emoji: {line.strip()}")
    print("  [OK] engine.py 日志无 emoji")


# ============================================================================
# 运行所有测试
# ============================================================================

def run_all():
    tests = [
        ("Item 动态字段无类级污染", test_item_dynamic_field_no_class_pollution),
        ("FIELDS 不会无限增长", test_item_dynamic_field_values_isolated),
        ("默认序列化为 json", test_default_serialization_is_json),
        ("ACK 失败不再静默", test_ack_message_logs_on_failure),
        ("信号量对称释放", test_semaphore_released_on_invalid_dequeue),
        ("种子锁 Lua 脚本存在", test_seed_lock_lua_script_exists),
        ("无 or True 残留", test_no_or_true_in_queue_manager),
        ("无 print 警告", test_no_print_in_framework),
        ("License 一致", test_license_consistency),
        ("无 aioredis 依赖", test_no_aioredis_dependency),
        ("无 emoji 日志", test_no_emoji_in_engine_log),
    ]

    passed = 0
    failed = 0
    errors = []

    print("=" * 60)
    print("Crawlo develop 分支修复验证测试")
    print("=" * 60)

    for name, test_func in tests:
        print(f"\n[RUN] {name}")
        try:
            test_func()
            passed += 1
        except Exception as e:
            failed += 1
            errors.append((name, str(e)))
            print(f"  [FAIL] {e}")

    print("\n" + "=" * 60)
    print(f"结果: {passed} passed, {failed} failed, 共 {len(tests)} 个测试")
    print("=" * 60)

    if failed > 0:
        print("\n失败详情:")
        for name, err in errors:
            print(f"  - {name}: {err}")
        sys.exit(1)
    else:
        print("\n所有修复验证通过！")


if __name__ == '__main__':
    run_all()
