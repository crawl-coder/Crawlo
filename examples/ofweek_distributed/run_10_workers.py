#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
10 Worker 分布式测试 — 启动 10 个子进程运行 run.py

v2.0 改进：
1. 使用指定 Python 解释器路径（避免 sys.executable 混用虚拟环境）
2. 每个 worker 输出重定向到独立日志文件，便于排查
3. 汇总展示每个 worker 的退出状态与处理统计

运行方式：
    cd examples/ofweek_distributed
    python run_10_workers.py
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

WORKER_COUNT = 10
RUN_SCRIPT = os.path.join(example_root, 'run.py')
LOG_DIR = os.path.join(example_root, 'logs', 'workers')


def main():
    if not os.path.exists(PYTHON_BIN):
        print(f"❌ Python 解释器不存在: {PYTHON_BIN}")
        sys.exit(1)

    Path(LOG_DIR).mkdir(parents=True, exist_ok=True)

    print("=" * 72)
    print("  10 Worker Distributed Test")
    print(f"  Python: {PYTHON_BIN}")
    print(f"  WORKER_COUNT: {WORKER_COUNT}")
    print(f"  RUN_MODE=distributed, QUEUE_TYPE=redis_stream")
    print(f"  Worker logs: {LOG_DIR}")
    print("=" * 72)
    print()

    processes = []
    env = os.environ.copy()
    env['PYTHONPATH'] = crawlo_root

    for i in range(WORKER_COUNT):
        worker_id = i + 1
        log_path = os.path.join(LOG_DIR, f"worker_{worker_id:02d}.log")
        log_f = open(log_path, 'w', buffering=1)
        p = subprocess.Popen(
            [PYTHON_BIN, RUN_SCRIPT],
            env=env,
            stdout=log_f,
            stderr=subprocess.STDOUT,
        )
        processes.append((p, worker_id, log_f, log_path))
        print(f"  Worker {worker_id:02d} started (PID={p.pid:>6}) -> {os.path.basename(log_path)}")
        # 错开启动，避免同时争夺种子锁 / Redis 连接波峰
        time.sleep(1.0)

    print(f"\n  All {len(processes)} workers started\n")
    print("=" * 72)
    print("  Waiting for workers to complete... (Ctrl+C once to graceful stop)\n")

    results = []
    try:
        for p, worker_id, log_f, log_path in processes:
            p.wait()
            log_f.close()
            results.append((worker_id, p.pid, p.returncode, log_path))
            status = "✅ OK" if p.returncode == 0 else f"❌ FAIL(code={p.returncode})"
            print(f"  Worker {worker_id:02d} (PID={p.pid:>6}) {status} -> {os.path.basename(log_path)}")
    except KeyboardInterrupt:
        print("\n  Interrupted, terminating all workers...")
        for p, worker_id, log_f, log_path in processes:
            if p.poll() is None:
                p.terminate()
        for p, worker_id, log_f, log_path in processes:
            try:
                p.wait(timeout=8)
            except subprocess.TimeoutExpired:
                p.kill()
                try:
                    p.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    pass
            if not log_f.closed:
                log_f.close()
            results.append((worker_id, p.pid, p.returncode, log_path))

    # 汇总统计
    print("\n" + "=" * 72)
    print("  Summary")
    print("=" * 72)
    success = sum(1 for _, _, rc, _ in results if rc == 0)
    failed = len(results) - success
    print(f"  Success: {success}   Failed: {failed}   Total: {len(results)}")

    # 从每个 worker 日志中抽几行关键 stats 输出
    for worker_id, pid, rc, log_path in results:
        marker = "✅" if rc == 0 else "❌"
        print()
        print(f"  {marker} Worker {worker_id:02d} (PID={pid}, rc={rc}) {os.path.basename(log_path)}:")
        try:
            with open(log_path) as f:
                lines = f.readlines()
            # 关键信息抓取
            interesting = []
            for line in lines:
                if any(k in line for k in [
                    'of_week stats', 'reason', 'request_scheduler_count',
                    'response_received_count', 'item_successful_count',
                    'Run mode:', 'Queue type:', 'All components are idle',
                    'Coordinated shutdown', 'Consumer group', 'seed lock', 'Seed',
                    'ERROR', 'Error', 'Exception', 'Traceback',
                ]):
                    interesting.append(line.rstrip())
            for line in interesting[-8:]:  # 最后 8 条关键行
                print(f"      {line}")
            if not interesting:
                print(f"      (no key stats captured — see log file)")
        except Exception as e:
            print(f"      (failed to read log: {e})")

    print("\n" + "=" * 72)
    print("  Test complete")


if __name__ == '__main__':
    main()
