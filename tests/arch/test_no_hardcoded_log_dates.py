"""架构守护：禁止测试中硬编码"近期"日志时间戳文件名（日期炸弹）。

背景：cleanup_old_logs 按文件名里的时间戳判断日志保留期，若测试硬编码
固定日期（如 ``recent_2026MMDD_HHMMSS.log``）作为"新文件"，跨过一天后
它就会被当成过期文件，测试必然 flaky（曾导致 master CI 全红）。

规则：tests/ 下任何 ``_YYYYMMDD_HHMMSS.log`` 字面量，若日期距今 ≤ 60 天，
一律拒绝，要求用相对当前时间生成。
"""

import re
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PATTERN = re.compile(r"_(\d{8})_\d{6}\.log")
CUTOFF = timedelta(days=60)


def test_no_hardcoded_recent_log_dates():
    today = datetime.now()
    offenders = []
    for path in sorted((ROOT / "tests").rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        for match in PATTERN.finditer(text):
            try:
                file_date = datetime.strptime(match.group(1), "%Y%m%d")
            except ValueError:
                continue
            if today - file_date <= CUTOFF:
                offenders.append(
                    f"{path.relative_to(ROOT)}: {match.group(0)} ({match.group(1)})"
                )
    assert not offenders, (
        "测试中硬编码了近期日志时间戳文件名，跨天后会变成'过期文件'导致 flaky：\n"
        + "\n".join(offenders)
        + "\n请改用相对当前时间生成（如 datetime.now() - timedelta(...)）"
    )
