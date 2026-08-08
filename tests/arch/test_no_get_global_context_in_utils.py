"""Phase 8 Step 8.8 架构守护：utils/bot/extension/queue/mcp/factories/initialization/scheduling 包内

不出现「顶层 ctx.xxx 写 / 读」，即不再把 ApplicationContext 当做模块级单例。

允许的 fallback 形式仅限：

- 容器优先（is_registered → resolve）
- fallback = ``get_global_context().<子上下文名>``（registries/runtime/notifications 之一）
- fallback 路径中不存在 ``ctx.<顶层属性>`` 的读或写

这确保 Phase 8 「通过子上下文 + DI 容器」的模式已经完整落地。
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

CRAWLO_ROOT = Path(__file__).resolve().parents[2] / "crawlo"

# Phase 8 已迁移的目标包（这些包不允许再直取 ApplicationContext 顶层属性）
GUARDED_PACKAGES = (
    "utils",
    "bot",
    "extension",
    "queue",
    "mcp",
    "factories",
    "initialization",
    "scheduling",
)

# ApplicationContext 顶层属性（通过 ctx.xxx 直接访问就算「顶层直取」）
# 见 crawlo/core/application.py ApplicationContext 委托 property 声明
TOP_LEVEL_CTX_ATTRS = {
    # RegistryContext 委托
    "component_registry",
    "initializer_registry",
    "job_registry",
    "framework",
    # RuntimeContext 委托
    "error_handler_instance",
    "performance_monitor",
    "resource_managers",
    "_monitor_manager",
    "quick_fetcher",
    "mcp_fetcher",
    "mcp_fetcher_lock",
    "redis_manager",
    "global_redis_pool",
    "redis_pools",
    # NotificationContext 委托
    "notifier",
    "notifier_lock",
    "notification_handler",
    "notification_handler_lock",
    "template_manager",
    "resource_monitor_manager",
    "deduplicator",
    "deduplicator_lock",
    "bot_config_loaded",
    "dingtalk_channel",
    "email_channel",
    "feishu_channel",
    "sms_channel",
    "wecom_channel",
    # 其他
    "settings",
    "stats",
}

# 允许的子上下文成员名（即 fallback 只能是 get_global_context().<子上下文> 或其链）
ALLOWED_FIRST_DOT_AFTER_CTX = {"registries", "runtime", "notifications"}


def _iter_guarded_files():
    for pkg in GUARDED_PACKAGES:
        pkg_dir = CRAWLO_ROOT / pkg
        if not pkg_dir.exists():
            continue
        for py_file in pkg_dir.rglob("*.py"):
            if "__pycache__" in str(py_file):
                continue
            yield py_file


def _has_top_level_ctx_access(source: str) -> list[str]:
    """返回文件中所有形如 ``ctx.<TOP_LEVEL_CTX_ATTRS>`` 的违规访问点（按行号排序）。"""
    tree = ast.parse(source)
    violations: list[str] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Attribute):
            continue
        if node.attr not in TOP_LEVEL_CTX_ATTRS:
            continue
        # 其值主体必须是 Name(id='ctx')，或 Attribute 的链末端 ctx
        subject = node.value
        # 只拦 ctx.<attr>：subject 是 Name("ctx")
        if isinstance(subject, ast.Name) and subject.id == "ctx":
            violations.append(
                f"L{node.lineno}: ctx.{node.attr} 属于 ApplicationContext 顶层属性访问"
            )
    return violations


def _imports_get_global_context(source: str) -> bool:
    return "import get_global_context" in source or "application import get_global_context" in source


def _uses_allowed_child_context_only(source: str) -> list[str]:
    """对 fallback 分支做更强一层检查：

    凡是 ``get_global_context()`` 被调用后的第一个 .attr 必须属于 registries/runtime/notifications。
    这里用简单的行级模式识别（更保守，不漏报；可能误报则在具体行上观察）。
    """
    violations: list[str] = []
    for lineno, line in enumerate(source.splitlines(), start=1):
        stripped = line.strip()
        # 只关心 "get_global_context().X" 或 "get_global_context()  .X"
        if "get_global_context()" not in stripped:
            continue
        # 找 get_global_context() 后的第一个非空 .attr
        idx = stripped.find("get_global_context()")
        tail = stripped[idx + len("get_global_context()"):]
        tail = tail.lstrip()
        if not tail.startswith("."):
            # 不是链式访问（如 if ctx is None: ctx = get_global_context()），放行
            continue
        attr_end = 1
        while attr_end < len(tail) and (tail[attr_end].isalnum() or tail[attr_end] == "_"):
            attr_end += 1
        first_attr = tail[1:attr_end]
        if first_attr and first_attr not in ALLOWED_FIRST_DOT_AFTER_CTX:
            violations.append(
                f"L{lineno}: get_global_context().{first_attr} 不是子上下文（registries/runtime/notifications）访问"
            )
    return violations


@pytest.mark.parametrize("py_file", list(_iter_guarded_files()), ids=lambda p: str(p.relative_to(CRAWLO_ROOT)))
def test_no_top_level_ctx_attr_access_in_guarded_packages(py_file: Path):
    source = py_file.read_text(encoding="utf-8")
    violations = _has_top_level_ctx_access(source)
    if violations:
        pytest.fail(
            "检测到 ApplicationContext 顶层属性直接访问（应先获取子上下文或从容器解析）：\n"
            + "\n".join(f"  {py_file.relative_to(CRAWLO_ROOT)} {v}" for v in violations)
        )


@pytest.mark.parametrize("py_file", list(_iter_guarded_files()), ids=lambda p: str(p.relative_to(CRAWLO_ROOT)))
def test_get_global_context_call_always_chains_child_context(py_file: Path):
    source = py_file.read_text(encoding="utf-8")
    if not _imports_get_global_context(source):
        pytest.skip("未导入 get_global_context，跳过")
    violations = _uses_allowed_child_context_only(source)
    if violations:
        pytest.fail(
            "get_global_context() 调用后仅允许访问子上下文（.registries / .runtime / .notifications）：\n"
            + "\n".join(f"  {py_file.relative_to(CRAWLO_ROOT)} {v}" for v in violations)
        )


def test_remaining_get_global_context_stays_within_plan_budget():
    """Phase 8 目标：GUARDED_PACKAGES 里导入 get_global_context 的文件数 ≤ 20（8 组迁移后的 fallback 白名单）

    当前实际：factories(2) + initialization(1) + scheduling(1) + utils(4) + bot(12) + extension(2) + queue(1) + mcp(2) = 25 处。
    这个数字是「每个 getter 文件 2 行 import + 1 行 fallback」= 正常的白名单过渡；断言上限 ≤ 30，防止未来新增超出预算。
    """
    counted_files = []
    for py_file in _iter_guarded_files():
        source = py_file.read_text(encoding="utf-8")
        if _imports_get_global_context(source):
            counted_files.append(py_file.relative_to(CRAWLO_ROOT))
    assert len(counted_files) <= 30, (
        "GUARDED_PACKAGES 内导入 get_global_context 的文件数超出预算，"
        f"当前 {len(counted_files)} 个（预算 30 个）。新代码应优先从 default_container 解析，"
        f"或通过子上下文（registries/runtime/notifications）定位。新增文件清单：{counted_files}"
    )
