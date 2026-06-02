#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
5 Worker 分布式测试 — 启动 5 个子进程运行 run.py

运行方式：
    cd examples/ofweek_distributed
    python run_5_workers.py
"""
import os
import sys
import subprocess
import time
import signal

example_root = os.path.dirname(os.path.abspath(__file__))
# run.py 在 examples/ofweek_distributed/ 下，crawlo 包在 ../../ 下
crawlo_root = os.path.dirname(os.path.dirname(example_root))
os.chdir(example_root)

WORKER_COUNT = 5
RUN_SCRIPT = os.path.join(example_root, 'run.py')


def main():
    print("=" * 60)
    print("  5 Worker Distributed Test")
    print("  max_page=200, ~4000 Requests")
    print("  RUN_MODE=distributed, QUEUE_TYPE=redis_stream")
    print("=" * 60)
    print()

    # Start 5 worker processes
    processes = []
    env = os.environ.copy()
    env['PYTHONPATH'] = crawlo_root

    for i in range(WORKER_COUNT):
        log_file = open(f'worker_{i+1}.log', 'w', encoding='utf-8')
        p = subprocess.Popen(
            [sys.executable, RUN_SCRIPT],
            env=env,
            stdout=log_file,
            stderr=subprocess.STDOUT,
        )
        processes.append((p, log_file))
        print(f"  Worker {i+1} started (PID={p.pid})")
        print(f"  Waiting 5s before next worker...")
        time.sleep(5)

    print(f"\n  All {len(processes)} workers started\n")
    print("=" * 60)
    print("  Waiting for workers to complete... (Ctrl+C to stop)\n")

    # Wait for all workers
    try:
        for i, (p, log_file) in enumerate(processes):
            p.wait()
            log_file.close()
            print(f"  Worker {i+1} (PID={p.pid}) exited with code {p.returncode}")
    except KeyboardInterrupt:
        print("\n  Interrupted, terminating all workers...")
        for p, log_file in processes:
            p.terminate()
            log_file.close()
        for p, _ in processes:
            try:
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                p.kill()

    print("\n" + "=" * 60)
    print("  Test complete")


if __name__ == '__main__':
    main()
