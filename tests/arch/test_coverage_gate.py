"""
Phase 4 — 覆盖率门槛架构守护测试

分阶段策略（GATE_* 常量为当前阶段门槛，每完成 C 阶段补测试后逐级收紧）：

    Phase 4.START（先不修既有失败）        | crawler 15%  | engine 20%  | cluster 13%
    →  B 阶段：修复 8 个既有 unit failures
    Phase 4.MID                            | crawler 20%  | engine 25%  | cluster 18%
    →  C 阶段：为 3 个核心文件补单元测试
    Phase 4.END（交付）                    | crawler 30%  | engine 35%  | cluster 25%

运行方式：

    # 快速 — 不跑真实 coverage（默认 skip）
    pytest tests/arch/test_coverage_gate.py      # 全 SKIP（避免每次加 --cov）

    # 验收 — 必须带 --cov 且报告存在
    pytest tests/arch/test_coverage_gate.py --cov=crawlo
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest


# ============= 当前生效的覆盖率门槛（Phase 4.DELIVERED 快照） =============
# 基线（A2 阶段，0 补测试 + 有既有 failures）：
#   crawler.py 15.61% / engine.py 20.15% / coordinator.py 13.77%
# 第一轮补测试后（B + C 全部完成，66 新测试）：
#   crawler.py 21.03% (+5.42pp) / engine.py 33.73% (+13.58pp) / coordinator.py 16.40% (+2.63pp)
#
# Phase 5 已达成：crawler→30% / engine→40% / coordinator→25%
# 每次手动上调 GATE_*_PCT 常量 2-3pp，保证"门槛只增不减"。
GATE_CRAWLER_PCT     = 30.0
GATE_ENGINE_PCT      = 40.0
GATE_COORDINATOR_PCT = 25.0


ROOT = Path(__file__).resolve().parents[2]
COVERAGE_SQLITE = ROOT / ".coverage"
COVERAGE_XML     = ROOT / "coverage.xml"


def _coverage_available() -> bool:
    """True if coverage is active *now* (i.e. pytest was called with --cov) OR a
    .coverage sqlite / coverage.xml artifact is already present next to pyproject.toml."""
    try:
        from coverage import Coverage
        cov = Coverage.current()
        if cov is not None and getattr(cov, "_collector", None) is not None:
            return True
    except Exception:
        pass
    return COVERAGE_SQLITE.exists() or COVERAGE_XML.exists()


def _run_coverage_json() -> dict:
    """Invoke coverage to obtain per-file percent_covered dict.

    Strategy (best-effort, first hit wins):
      1. Coverage.current() live in-process (preferred — pytest ran with --cov)
      2. Load from ``.coverage`` sqlite next to pyproject.toml
      3. Otherwise, pytest.skip
    """
    try:
        from coverage import Coverage
    except ImportError:
        pytest.skip("coverage package unavailable; install pytest-cov and run with --cov=crawlo")
        return {}  # pragma: no cover

    cov: Optional[Coverage] = None

    # 1) live coverage collector (pytest --cov uses this, collector is non-None)
    live = Coverage.current()
    if live is not None and getattr(live, "_collector", None) is not None:
        try:
            live.stop()
            live.save()
        except Exception:
            pass
        cov = live

    # 2) load from .coverage sqlite file (fallback for 2-process runs)
    if cov is None and COVERAGE_SQLITE.exists():
        try:
            fresh = Coverage(data_file=str(COVERAGE_SQLITE))
            fresh.load()
            if fresh.get_data() and len(fresh.get_data().measured_files()) > 0:
                cov = fresh
        except Exception:
            pass

    if cov is None:
        pytest.skip(
            "Coverage 数据不可用。请以 `pytest --cov=crawlo` 方式运行，"
            "或先在前一个 pytest --cov 调用中生成 .coverage 文件。"
        )
        return {}  # pragma: no cover

    files_report: dict = {}
    data = cov.get_data()
    for abs_path in data.measured_files():
        rel = os.path.relpath(abs_path, str(ROOT)).replace(os.sep, "/")
        try:
            _fn, stmts_present, stmts_missing, _excl, _miss_str = cov.analysis2(abs_path)
            denom = len(stmts_present)
            covered = denom - len(stmts_missing)
            pct = round(100.0 * covered / denom, 2) if denom else 0.0
        except Exception:
            continue
        files_report[rel] = {
            'statements': denom,
            'covered': covered,
            'missing': list(stmts_missing) if isinstance(stmts_missing, list) else [],
            'percent_covered': pct,
        }
    return files_report


def _pick(report: dict, rel_path: str) -> float:
    """Return percent_covered or -1 if file not measured."""
    key = rel_path.replace("\\", "/")
    if key in report:
        return report[key]['percent_covered']
    for k, v in report.items():
        if k.endswith(rel_path):
            return v['percent_covered']
    return -1.0


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _coverage_available(), reason="Need --cov=crawlo to enable coverage gate")
class TestCoverageGates:
    """核心模块覆盖率门槛（Phase 4，分阶段收紧）"""

    @pytest.fixture(scope="class")
    @classmethod
    def report(cls):
        return _run_coverage_json()

    # ---------- 核心大文件：crawler.py (1350 行, 生命周期收敛主文件) ----------

    def test_crawler_py_coverage(self, report):
        """crawlo/crawler/_crawler.py 覆盖率 ≥ GATE_CRAWLER_PCT%（crawler.py 扁平文件已迁移为 re-export shim）"""
        pct = _pick(report, "crawlo/crawler/_crawler.py")
        assert pct >= GATE_CRAWLER_PCT, (
            f"crawlo/crawler/_crawler.py 覆盖率 {pct:.2f}% 低于门槛 {GATE_CRAWLER_PCT}%。\n"
            f"请补充 tests/unit/test_crawler_phase4.py 中的生命周期 / 资源注册类测试。"
        )

    # ---------- 核心大文件：core/engine.py (1510 行, Engine 主循环) ----------

    def test_core_engine_py_coverage(self, report):
        """crawlo/core/engine.py 覆盖率 ≥ GATE_ENGINE_PCT%"""
        pct = _pick(report, "crawlo/core/engine.py")
        assert pct >= GATE_ENGINE_PCT, (
            f"crawlo/core/engine.py 覆盖率 {pct:.2f}% 低于门槛 {GATE_ENGINE_PCT}%。\n"
            f"请补充 tests/unit/test_engine_phase4.py 中的 idle/close_spider/ACK 分支测试。"
        )

    # ---------- 分布式协调器：cluster/coordinator.py ----------

    def test_cluster_coordinator_py_coverage(self, report):
        """crawlo/cluster/coordinator.py 覆盖率 ≥ GATE_COORDINATOR_PCT%"""
        pct = _pick(report, "crawlo/cluster/coordinator.py")
        assert pct >= GATE_COORDINATOR_PCT, (
            f"crawlo/cluster/coordinator.py 覆盖率 {pct:.2f}% 低于门槛 {GATE_COORDINATOR_PCT}%。\n"
            f"请补充 tests/unit/test_coordinator_phase4.py 中的种子锁 Lua / Worker 注册测试。"
        )


@pytest.mark.skipif(not _coverage_available(), reason="Need --cov=crawlo to enable coverage gate")
def test_coverage_gate_summary(request):
    """控制台输出当前 3 文件覆盖率（非断言，仅展示辅助）。"""
    report = _run_coverage_json()
    lines = []
    for (name, path, gate) in [
        ("crawler",     "crawlo/crawler.py",           GATE_CRAWLER_PCT),
        ("engine",      "crawlo/core/engine.py",       GATE_ENGINE_PCT),
        ("coordinator", "crawlo/cluster/coordinator.py", GATE_COORDINATOR_PCT),
    ]:
        pct = _pick(report, path)
        status = "✓" if pct >= gate else "✗"
        lines.append(f"  {status} {name:<12} {pct:>6.2f}% (gate={gate}%)")
    summary = "\n" + "\n".join(lines) + "\n"
    request.config._coverage_gate_summary = summary
    print(summary)
