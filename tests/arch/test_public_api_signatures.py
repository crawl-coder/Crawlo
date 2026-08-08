#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
架构守护测试 — 公共 API 签名快照
================================

目的
----
对 Crawlo 框架 5 个核心类的公共方法签名做快照，重构期间保证公共 API
100% 向后兼容。

守护范围（5 个核心类）：
    1. crawlo.core.engine.Engine
    2. crawlo.core.application.ApplicationContext
    3. crawlo.core.task_scheduler.Scheduler
    4. crawlo.queue.queue_manager.QueueManager
    5. crawlo.core.processor.Processor

规则
----
- 仅允许加 @property 委托
- 不允许删除或修改已有公共方法 / property 的签名
- 加新方法是允许的（不会导致现有签名哈希变化，因为是逐方法比较，
  而不是整体比较；新增方法不在基线中，自然不会被检查）

实现方式
--------
1. 用 inspect 遍历每个类的 MRO（排除 object），收集公共成员
   （不以 _ 开头，dunder 全部排除，仅保留 __init__ 作为公共构造函数）
2. 对每个方法用 inspect.signature() 获取签名；property 取 fget 的签名；
   classmethod / staticmethod 取底层函数签名
3. 签名字符串格式：method_name(arg1, arg2, /, *, kw1=default) -> ReturnType
4. 对签名字符串取 hashlib.sha256 得到哈希
5. 把哈希存为基线常量 BASELINE，断言当前签名哈希 == 基线
6. 签名变更 → 测试失败，提示更新基线

如何更新基线
------------
当且仅当签名变更经过评审且确认向后兼容时，才更新基线。步骤：
    1. 直接运行本文件，打印当前所有方法的签名哈希：
           python tests/arch/test_public_api_signatures.py
    2. 将打印结果填回下方 BASELINE 字典（或对照失败信息只更新变更项）
    3. PR 中说明签名变更原因与兼容性评估

基线快照日期：2026-08-07（Phase 0）
ApplicationContext.__init__ 更新：2026-08-07（Phase 4 Step 1，组合三子上下文）
"""
import hashlib
import inspect

import pytest

from crawlo.core.engine import Engine
from crawlo.core.application import ApplicationContext
from crawlo.core.task_scheduler import Scheduler
from crawlo.queue.queue_manager import QueueManager
from crawlo.core.processor import Processor


# 基线快照（2026-08-07 Phase 0）
# {class_name: {method_name: signature_hash}}
BASELINE = {
    "Engine": {
        "__init__": "e84ddfdd330611281f9f36e93203bf7aa149f54923f0fd34da1a62bac70b9700",
        "engine_start": "15f9ce84574fa0b8112c4594967cc7716e6e51d4cd9f35e7bf6fc62530eaf115",
        "start_spider": "9f4e836eaff526d9e0bace2b773e258059459d562800126cdde7697d986d5bd8",
        "crawl": "8806d5b8e61d8a7d9cfa31fcab42a5907d4b3b9a779bac6147fa1b5afda6cb49",
        "enqueue_request": "1a16a2d9c6f555933639163a7e115437502439fb3d093f2a39259fb07694370f",
        "close_spider": "1ea8edf49ff42b4c44d2a86002509d46ce49dca8390dff40e17c44b94855ec9c",
        "get_generation_stats": "32e1c911d979875a565fea772857fad0b60e8505d984f57cc483413e8012c5a0",
    },
    "ApplicationContext": {
        "register_spider": "5209587c4dede7e30c7f454f72c8faeb9bd6a5587d40200d669329c418a90c52",
        "get_spider": "c5fee40e2237de9a68729e5b88f31eb634c6a0e31bc45032dbd97615b9c043a0",
        "unregister_spider": "1fa18b85ab663a04c443d79a6eb472942ad19663181125c709c1e3730e0f9a8e",
        "add_resource": "9b324660dddae84ff13afd946eda078278fb8feed80925e60c3eca5a02025a64",
        "remove_resource": "44d4d471c9cc0731f4285c435ed960f37456af16072706b3f4b5cc744605e177",
        "cleanup": "4c35a25c06b480d5d793e4806397b867d256c3b1501e6cec13a695d74d8ae7bd",
        "__init__": "131ab68902f35c149966a1cdec7cb80515339e7a6d172815c08441d445a46f93",
    },
    "Scheduler": {
        "__init__": "e22069f369ca4a3e1d364101060d13fc068ea71b160acf136d1232c39fbe6dc7",
        "queue_type": "4b0d5100f864457a4e1c97b4e407a9220e7a1303b8847466cc352379caf52852",
        "create_instance": "a141372e386c1b3ca3b5a5b19270e5783efe3410816de68564511b70a6fd207c",
        "open": "00ce6c9990e8fe906af6f0eb06820eabc5f529133eab9c6e9507ba1253a88ee4",
        "next_request": "5bf8d17cda1ee20d7827689e6c2d0f442c109cff9357397a6a2d72f1942ee6f7",
        "next_request_blocking": "e461cb879f8e20610bb334d9a562d1fce5242f682c6c36ded48f37e3825fe481",
        "enqueue_request": "40d18b85b0d882e8e7d6edd64e724ab1f690a5573a196561c2f7826962cc3878",
        "async_idle": "5ee527be0e0d97668fc6f7be024f806c5ade7de2f682969432778bc818f6625e",
        "async_size": "7ea9f3b04c7883da3bd9d42730e3cb0f7855c3e2559681d231fa873a93aa60bb",
        "close": "67b62c975aef34675343142a609e597b59d5e3cd93484c23e074eaa09b3df031",
        "next_request_with_ack": "e2967eafce2437980c1ea8e9ef39e1bfdcdaeb84ffbf42636d628b0fa063e6c7",
        "ack_request": "86abbd6f3cda5a78ffabafa6b62060deb6fa65edb9c9ed837ed0e958ff73c3ef",
        "nack_request": "af75f5d6ff16c752c3702999fdd9a937d6b592c69a700b212607c4a837940225",
    },
    "QueueManager": {
        "__init__": "31dc3008e2bf32e64d4b3574dd62d89abcdee2585b6850e8273225821bb4feb3",
        "logger": "f923b55ab4e0d7eb76312282cfa803ec0175990ad65ce17fd4e51132f954f6e4",
        "error_handler": "a4f806b6fbd62522a24c5a1397c328ad1652bded11f1b8b8f4e173b4aed4b642",
        "initialize": "d092f53af6b06bc6dc2074c21e9f17c9b7ddc3dcdce308df1ea3ca34aff18a31",
        "put": "230295d9ac6e488c403f4ff3a6e41bcbb65d01babade3dd4babe4433c768a1cb",
        "get": "92d70d5483ec3395fb18056c2993463e0bf860e21ab705ddb1f02a42d6112e04",
        "get_blocking": "a90a0ced02b0df983c0dc0d06bb17e2bb684762a6bca3db034620ed29a130ba8",
        "size": "6880a6dc0ea1cfb23464576c2c04d0cf94f48a3910f90440bd2c823b0e7a6dc0",
        "max_size": "8858d2835ce143962699221851f72afe2cc167de51fbf97305b2538ad9caec01",
        "async_empty": "3959594f2cacd0bc2f933842023cca11a42172a1d81dbf6167b1dee9823ff5ec",
        "close": "57595719c388c9e1859af92ca830a3a26f611820a328e6428de2fae25de39280",
        "get_status": "77853bfbbfcd0462175fdf48f9e639aa23d4318acdb17f9ec9ecb2a6c1e6c149",
        "get_queue_stats": "8dd53dd8eff1f86524cee8260e93288827fd77e12333b3b7738c21d9dcb134c3",
    },
    "Processor": {
        "__init__": "e84ddfdd330611281f9f36e93203bf7aa149f54923f0fd34da1a62bac70b9700",
        "open": "12a7f11d963dc370a43bd7300dc7140d78778bee4acde7b0d1da2645d5d7c8cb",
        "start": "aa9e6e106bed8dc7f871eacbb6a6c05e1655800ef3ed6c0efcfeed6b548b4d9b",
        "stop": "0758f078d0b203b36a71b8d8f7166f8565be646df459eb472e9d62e9878c4856",
        "enqueue": "8ffc19bbdef16cee6ebbbea662d5782648d46c488f3c861554d5c06fc9bfc50d",
        "process_once": "cac1364919a927d757ae892153d2af33f341ac5dd92e8e34c9735929f11219c3",
        "idle_async": "adfe4d9dd4ef79a5b63a1d00a3d9017bc26db81e4d343776fb9b9764481fcfff",
        "close": "57595719c388c9e1859af92ca830a3a26f611820a328e6428de2fae25de39280",
        "get_stats": "e31fb793d99103adc89cb6e3b3c5ba7b08cb9ff3c4b1d108619644202b1c262b",
    },
}


def _signature_string(name, attr):
    """构造签名字符串：method_name(arg1, arg2, ...) -> ReturnType

    - property：取 fget 的签名
    - classmethod / staticmethod：取底层函数签名（保留 cls/self）
    - 普通函数：直接取签名
    """
    if isinstance(attr, property):
        func = attr.fget
        if func is None:
            return None
    elif isinstance(attr, classmethod):
        func = attr.__func__
    elif isinstance(attr, staticmethod):
        func = attr.__func__
    elif callable(attr):
        func = attr
    else:
        return None
    try:
        sig = inspect.signature(func)
    except (ValueError, TypeError):
        return None
    return f"{name}{sig}"


def _public_members(cls):
    """枚举类的公共成员（含继承，排除 object 继承与 dunder，保留 __init__）。

    遍历 cls.__mro__（跳过 object），收集：
      - 不以 _ 开头的可调用成员 / property / classmethod / staticmethod
      - __init__ 保留（公共构造函数）
      - 其它 dunder（__len__、__repr__ 等）一律排除
    子类成员优先（覆盖父类同名成员）。
    """
    members = {}
    for klass in cls.__mro__:
        if klass is object:
            continue
        for name, attr in vars(klass).items():
            if name in members:
                continue  # 子类已覆盖，跳过父类版本
            if name.startswith('_') and name != '__init__':
                continue
            if name.startswith('__') and name.endswith('__') and name != '__init__':
                continue
            if callable(attr) or isinstance(attr, (property, staticmethod, classmethod)):
                members[name] = attr
    return members


def _signature_hash(name, attr):
    sig_str = _signature_string(name, attr)
    if sig_str is None:
        return None
    return hashlib.sha256(sig_str.encode('utf-8')).hexdigest()


def _check_class(cls, cls_name):
    """对单个类逐方法比对签名哈希，返回失败信息列表。"""
    baseline = BASELINE[cls_name]
    members = _public_members(cls)
    failures = []
    for method_name, expected_hash in baseline.items():
        if method_name not in members:
            failures.append(
                f"  {cls_name}.{method_name}: 已被删除或改为私有（基线中记录的公共方法丢失）"
            )
            continue
        actual_hash = _signature_hash(method_name, members[method_name])
        if actual_hash != expected_hash:
            failures.append(
                f"  {cls_name}.{method_name}: 签名变更\n"
                f"    基线哈希: {expected_hash}\n"
                f"    当前哈希: {actual_hash}\n"
                f"    当前签名: {_signature_string(method_name, members[method_name])}"
            )
    return failures


_UPDATE_HINT = (
    "如确需变更，请运行 `python tests/arch/test_public_api_signatures.py` "
    "打印当前哈希，评审后更新 BASELINE 字典。"
)


class TestPublicAPISignatures:
    """公共 API 签名守护 — 重构期间 100% 向后兼容。"""

    def test_engine_signatures(self):
        failures = _check_class(Engine, "Engine")
        assert not failures, (
            "Engine 公共 API 签名发生变更。重构期间仅允许加 @property 委托，"
            "不允许删除或修改已有签名。\n" + "\n".join(failures) + "\n" + _UPDATE_HINT
        )

    def test_application_context_signatures(self):
        failures = _check_class(ApplicationContext, "ApplicationContext")
        assert not failures, (
            "ApplicationContext 公共 API 签名发生变更。重构期间仅允许加 @property 委托，"
            "不允许删除或修改已有签名。\n" + "\n".join(failures) + "\n" + _UPDATE_HINT
        )

    def test_scheduler_signatures(self):
        failures = _check_class(Scheduler, "Scheduler")
        assert not failures, (
            "Scheduler 公共 API 签名发生变更。重构期间仅允许加 @property 委托，"
            "不允许删除或修改已有签名。\n" + "\n".join(failures) + "\n" + _UPDATE_HINT
        )

    def test_queue_manager_signatures(self):
        failures = _check_class(QueueManager, "QueueManager")
        assert not failures, (
            "QueueManager 公共 API 签名发生变更。重构期间仅允许加 @property 委托，"
            "不允许删除或修改已有签名。\n" + "\n".join(failures) + "\n" + _UPDATE_HINT
        )

    def test_processor_signatures(self):
        failures = _check_class(Processor, "Processor")
        assert not failures, (
            "Processor 公共 API 签名发生变更。重构期间仅允许加 @property 委托，"
            "不允许删除或修改已有签名。\n" + "\n".join(failures) + "\n" + _UPDATE_HINT
        )


if __name__ == "__main__":
    # 辅助工具：打印当前所有类的公共方法签名哈希，便于更新 BASELINE。
    # 用法：python tests/arch/test_public_api_signatures.py
    _ALL_CLASSES = [
        ("Engine", Engine),
        ("ApplicationContext", ApplicationContext),
        ("Scheduler", Scheduler),
        ("QueueManager", QueueManager),
        ("Processor", Processor),
    ]
    print("# === 当前公共方法签名哈希（用于更新 BASELINE） ===")
    for cls_name, cls in _ALL_CLASSES:
        print(f'\n    "{cls_name}": {{')
        for name, attr in _public_members(cls).items():
            sig_str = _signature_string(name, attr)
            if sig_str is None:
                continue
            h = _signature_hash(name, attr)
            print(f'        "{name}": "{h}",')
        print("    },")
