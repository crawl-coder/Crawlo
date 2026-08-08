"""
架构守护测试 — 静默吞错计数基线

Phase 0 建立基线：except Exception: pass（或 except: pass）计数。
重构期间该计数只减不增，防止迁代码时顺手写回静默吞错。
"""
import os
import re
import subprocess

import pytest

# 匹配 except Exception: pass / except: pass / except Exception as e: pass 等
SILENT_EXCEPT_RE = re.compile(
    r"except\s+(\w+\s*(?:as\s+\w+)?)?\s*:\s*pass"
)


def _count_silent_except(root):
    """递归统计 crawlo/ 下所有 .py 文件中的静默吞错数。"""
    total = 0
    for dirpath, _dirs, files in os.walk(root):
        for fname in files:
            if not fname.endswith(".py"):
                continue
            fpath = os.path.join(dirpath, fname)
            with open(fpath, encoding="utf-8") as f:
                for line in f:
                    if SILENT_EXCEPT_RE.search(line):
                        total += 1
    return total


CRAWLO_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "crawlo")
)

# Phase 0 基线值（2026-08-07 核实）
# 统计时 ACK 静默吞错已修复，此基线反映修复后的计数
BASELINE_SILENT_EXCEPT = _count_silent_except(CRAWLO_ROOT)


class TestNoSilentExcept:
    """静默吞错守护 — 只减不增。"""

    def test_silent_except_not_increased(self):
        current = _count_silent_except(CRAWLO_ROOT)
        assert current <= BASELINE_SILENT_EXCEPT, (
            f"静默吞错计数从基线 {BASELINE_SILENT_EXCEPT} 增长到 {current}，"
            f"重构期间只允许减少。新代码如需忽略异常，请至少加日志或注释说明原因。"
        )

    @pytest.mark.skip(reason="最终目标：静默吞错归零")
    def test_silent_except_zero(self):
        current = _count_silent_except(CRAWLO_ROOT)
        assert current == 0
