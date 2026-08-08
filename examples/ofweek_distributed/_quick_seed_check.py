#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Quick seed-lock sanity check: 2 Workers, OFWEEK_TEST_MAX_PAGE=5, verify exactly ONE worker runs start_requests.
"""
import os
import sys
import subprocess
import time
from pathlib import Path

PYTHON_BIN = "/Users/oscar/software/miniconda3/envs/crawlo/bin/python"
example_root = os.path.dirname(os.path.abspath(__file__))
crawlo_root = os.path.dirname(os.path.dirname(example_root))
os.chdir(example_root)
LOG_DIR = os.path.join(example_root, 'logs', 'workers')
Path(LOG_DIR).mkdir(parents=True, exist_ok=True)

env = os.environ.copy()
env['PYTHONPATH'] = crawlo_root
env['OFWEEK_TEST_MAX_PAGE'] = '5'

# flush redis first
subprocess.check_call(['redis-cli', '-h', '127.0.0.1', '-p', '6379', 'FLUSHDB'])

procs = []
for i in range(2):
    log_path = f'{LOG_DIR}/seed_check_{i+1}.log'
    log_f = open(log_path, 'w', buffering=1)
    p = subprocess.Popen(
        [PYTHON_BIN, os.path.join(example_root, 'run.py')],
        env=env,
        stdout=log_f,
        stderr=subprocess.STDOUT,
    )
    procs.append((p, i + 1, log_f, log_path))
    print(f"  Worker {i+1} PID={p.pid} -> {os.path.basename(log_path)}")
    time.sleep(1.2)

print("\n  Waiting for workers to finish...")
for p, wid, log_f, log_path in procs:
    p.wait()
    log_f.close()
    print(f"  Worker {wid} PID={p.pid} rc={p.returncode}")

print("\n=== Seed lock check ===")
seed_count = 0
holders = []
acquired = []
skipped = []
for p, wid, log_f, log_path in procs:
    with open(log_path) as f:
        text = f.read()
    import re
    starts = re.findall(r'生成了 (\d+) 个起始URL', text)
    if starts:
        seed_count += 1
        holders.append(wid)
    if 'another Worker is generating seed URLs' in text or 'Seed lock held by active worker' in text:
        skipped.append(wid)
    if 'Acquired seed lock' in text or 'Cleared stale seed lock' in text:
        acquired.append(wid)
    print(f"  Worker {wid}: 执行start_requests次数={len(starts)} acquired={wid in acquired} skipped={wid in skipped}")

print(f"\n  ✅ 执行 start_requests 的 Worker 数量: {seed_count}（预期=1）")
if seed_count == 1:
    print("  🎉 Seed lock fix OK!")
    sys.exit(0)
else:
    print("  ❌ Seed lock 仍有竞态，需要进一步排查")
    sys.exit(1)
