#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
10 Worker 分布式测试 — 启动 10 个子进程运行 run.py

运行方式：
    cd examples/ofweek_distributed
    python run_10_workers.py
"""
import os
import sys
import subprocess
import time

example_root = os.path.dirname(os.path.abspath(__file__))
crawlo_root = os.path.dirname(os.path.dirname(example_root))
os.chdir(example_root)

WORKER_COUNT = 10
RUN_SCRIPT = os.path.join(example_root, 'run.py')


def main():
    print("=" * 60)
    print("  10 Worker Distributed Test")
    print(f"  max_page=1800, ~{1800 * 20} Requests")
    print("  RUN_MODE=distributed, QUEUE_TYPE=redis_stream")
    print("=" * 60)
    print()

    processes = []
    env = os.environ.copy()
    env['PYTHONPATH'] = crawlo_root

    for i in range(WORKER_COUNT):
        p = subprocess.Popen(
            [sys.executable, RUN_SCRIPT],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
        )
        processes.append(p)
        print(f"  Worker {i+1} started (PID={p.pid})")
        time.sleep(2)

    print(f"\n  All {len(processes)} workers started\n")
    print("=" * 60)
    print("  Waiting for workers to complete... (Ctrl+C to stop)\n")

    try:
        for i, p in enumerate(processes):
            p.wait()
            print(f"  Worker {i+1} (PID={p.pid}) exited with code {p.returncode}")
    except KeyboardInterrupt:
        print("\n  Interrupted, terminating all workers...")
        for p in processes:
            p.terminate()
        for p in processes:
            try:
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                p.kill()

    print("\n" + "=" * 60)
    print("  Test complete")


if __name__ == '__main__':
    main()
