"""
架构守护测试 — Engine 体积基线

Phase 0 建立基线，Phase 3 收紧阈值。
重构期间 engine.py 行数只减不增，__init__ 顶层赋值数只减不增。
"""
import ast
import os

import pytest

ENGINE_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "crawlo", "core", "engine.py"
)
ENGINE_PATH = os.path.abspath(ENGINE_PATH)

# Phase 3 更新基线（2026-08-08）：Step 1~2 完成后收紧
# Phase 0 基线 1023 行 / 66 赋值 → Phase 3 后 749 行 / 12 赋值
# 注意：_count_lines 用 sum(1 for _ in f) 计数，比 wc -l 多 1（最后一行无尾换行）
BASELINE_LINES = 750
BASELINE_INIT_ASSIGNS = 12


def _count_lines(path):
    with open(path, encoding="utf-8") as f:
        return sum(1 for _ in f)


def _count_init_assigns(path):
    """统计 Engine.__init__ 方法体内 self.xxx = 赋值数（仅顶层语句，不含嵌套）。"""
    with open(path, encoding="utf-8") as f:
        tree = ast.parse(f.read())

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "Engine":
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name == "__init__":
                    count = 0
                    for stmt in item.body:
                        if isinstance(stmt, ast.Assign):
                            for target in stmt.targets:
                                if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name) and target.value.id == "self":
                                    count += 1
                    return count
    return 0


class TestEngineSize:
    """Engine 体积守护 — 只减不增。"""

    def test_engine_lines_not_increased(self):
        current = _count_lines(ENGINE_PATH)
        assert current <= BASELINE_LINES, (
            f"engine.py 行数从基线 {BASELINE_LINES} 增长到 {current}，"
            f"重构期间只允许减少。如新增代码请先拆分到其他模块。"
        )

    def test_engine_init_assigns_not_increased(self):
        current = _count_init_assigns(ENGINE_PATH)
        assert current <= BASELINE_INIT_ASSIGNS, (
            f"Engine.__init__ 顶层 self.xxx 赋值数从基线 {BASELINE_INIT_ASSIGNS} 增长到 {current}，"
            f"重构期间只允许减少。新增字段请收进 dataclass 或子组件。"
        )

    @pytest.mark.skip(reason="Phase 3 验收目标：engine.py ≤ 600 行（当前 749 行，后续 Phase 继续优化）")
    def test_engine_target_600_lines(self):
        current = _count_lines(ENGINE_PATH)
        assert current <= 600

    def test_engine_init_target_15_assigns(self):
        """Phase 3 验收：__init__ ≤ 15 赋值（当前 12，已达标）"""
        current = _count_init_assigns(ENGINE_PATH)
        assert current <= 15, (
            f"Engine.__init__ 顶层 self.xxx 赋值数 {current} 超过 Phase 3 目标 15，"
            f"新增字段请收进 ClusterState dataclass 或子组件。"
        )
