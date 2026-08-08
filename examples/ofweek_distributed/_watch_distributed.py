#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""
自动检测 ofweek 分布式测试是否结束，按用户指定的5步执行。
注意：此脚本必须用 crawlo conda 环境的 Python 运行，以确保 redis / psutil 可用。
"""
import os
import sys
import subprocess
import re
from datetime import datetime
from pathlib import Path

PYTHON_BIN = "/Users/oscar/software/miniconda3/envs/crawlo/bin/python"
FLAG_FILE = Path("/tmp/crawlo_distributed_summary_done.flag")
WATCH_LOG = Path("/tmp/crawlo_watch.log")
EXAMPLE_DIR = Path("/Users/oscar/projects/Crawlo/examples/ofweek_distributed")
STREAM_KEY_HIGH = "crawlo:ofweek_distributed:of_week_distributed:stream:tasks:high"
STREAM_KEY_LOW = "crawlo:ofweek_distributed:of_week_distributed:stream:tasks"
SUMMARY_SCRIPT = EXAMPLE_DIR / "collect_distributed_summary.py"


def count_processes():
    """Step 1: 用 pgrep -f（不可用时用 psutil）检查 ofweek_distributed/run.py 进程数."""
    target = "ofweek_distributed/run.py"
    # Try pgrep first
    for pgrep in ["/usr/bin/pgrep", "/usr/local/bin/pgrep", "/opt/homebrew/bin/pgrep"]:
        if os.path.exists(pgrep):
            try:
                out = subprocess.check_output(
                    [pgrep, "-f", target], stderr=subprocess.DEVNULL
                ).decode().strip()
                if out:
                    return len([l for l in out.splitlines() if l.strip()])
                return 0
            except subprocess.CalledProcessError as e:
                if e.returncode == 1:
                    return 0
                # other errors, fall through to psutil
    # Fallback: psutil
    try:
        import psutil
        cnt = 0
        for p in psutil.process_iter(["pid", "cmdline"]):
            try:
                cmdline = p.info.get("cmdline") or []
            except Exception:
                continue
            if any(target in c for c in cmdline):
                cnt += 1
        return cnt
    except Exception as e:
        print(f"  [WARN] psutil 不可用: {e}", file=sys.stderr)
    return -1


def get_stream_metrics(key):
    """用 redis-py 直接查询一个 stream key 的 (xlen, pending, lag)."""
    try:
        import redis
        r = redis.Redis(host="127.0.0.1", port=6379, db=0, decode_responses=True)
    except Exception as e:
        return -1, -1, -1, f"redis import error: {e}"

    try:
        xlen = r.xlen(key)
    except Exception as e:
        return -1, -1, -1, f"XLEN error: {e}"

    pending_total = 0
    lag_total = 0
    group_names = []
    try:
        groups = r.xinfo_groups(key)
        for g in groups:
            group_names.append(g.get("name", "?"))
            pending_total += int(g.get("pending", 0) or 0)
            lag_total += int(g.get("lag", 0) or 0)
    except Exception as e:
        return xlen, -1, -1, f"XINFO_GROUPS error: {e} groups={group_names}"

    return xlen, pending_total, lag_total, f"groups={group_names}"


def write_watch_log(msg):
    """Step 4: 写一条状态到 /tmp/crawlo_watch.log 带时间戳."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    WATCH_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(WATCH_LOG, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {msg}\n")


def run_summary():
    """Step 3: cd 到示例目录，调用 collect_distributed_summary.py --watch 0."""
    print(f"  运行总结脚本: {SUMMARY_SCRIPT} --watch 0", flush=True)
    old_cwd = os.getcwd()
    try:
        os.chdir(EXAMPLE_DIR)
        proc = subprocess.run(
            [PYTHON_BIN, str(SUMMARY_SCRIPT), "--watch", "0"],
            capture_output=True, timeout=300, encoding="utf-8", errors="replace"
        )
        if proc.stdout:
            print(proc.stdout, flush=True)
        if proc.stderr:
            print("  [STDERR]", proc.stderr[:2000], file=sys.stderr, flush=True)
        return proc.returncode == 0
    finally:
        os.chdir(old_cwd)


def main():
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"=== Crawlo 分布式测试 Watch 检测 {ts} ===", flush=True)

    # ---- Step 5: 检查 flag 文件，避免重复总结 ----
    if FLAG_FILE.exists():
        print(f"✅ Flag 文件已存在: {FLAG_FILE}")
        print("   （表示已生成过最终总结，跳过本次检测）")
        try:
            done_time = datetime.fromtimestamp(FLAG_FILE.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            print(f"   标记时间: {done_time}")
            print(f"   Flag 内容:\n{FLAG_FILE.read_text(encoding='utf-8').rstrip()}")
            summaries = sorted((EXAMPLE_DIR / "logs").glob("distributed_summary_*.txt"))
            if summaries:
                latest = summaries[-1]
                print(f"   最新总结: {latest} ({latest.stat().st_size:,} bytes)")
        except Exception as e:
            print(f"   [WARN] 读取 flag/summary 出错: {e}")
        return

    # ---- Step 1: 检查 ofweek_distributed/run.py 进程 ----
    proc_cnt = count_processes()
    print(f"[1/4] 运行中的 run.py 进程数: {proc_cnt}")

    # ---- Step 2: 检查 Redis Stream HIGH & LOW ----
    print(f"[2/4] 检查 Redis Stream（HIGH & LOW）...")
    xh, ph, lh, infoh = get_stream_metrics(STREAM_KEY_HIGH)
    xl, pl, ll, infol = get_stream_metrics(STREAM_KEY_LOW)
    print(f"   HIGH STREAM  key={STREAM_KEY_HIGH}")
    print(f"     xlen={xh}  pending_sum={ph}  lag_sum={lh}  ({infoh})")
    print(f"   LOW  STREAM  key={STREAM_KEY_LOW}")
    print(f"     xlen={xl}  pending_sum={pl}  lag_sum={ll}  ({infol})")

    no_process = (proc_cnt == 0)
    # HIGH: XLEN + pending == 0  OR  lag == 0
    high_ok = ((xh >= 0 and ph >= 0 and (xh + ph) == 0) or (lh == 0))
    # LOW: 同上
    low_ok = ((xl >= 0 and pl >= 0 and (xl + pl) == 0) or (ll == 0))
    stream_empty = high_ok and low_ok
    done = no_process and stream_empty

    print(f"[判定] 无进程={no_process}  HIGH_empty={high_ok}  LOW_empty={low_ok} → 已跑完={done}")

    if done:
        # ---- Step 3: 已跑完，生成总结并写 flag ----
        print("[3/4] ✅ 检测到分布式测试已结束，生成最终总结...", flush=True)
        ok = run_summary()
        if ok:
            FLAG_FILE.write_text(
                f"done_at={datetime.now().isoformat(timespec='seconds')}\n"
                f"processes={proc_cnt}\n"
                f"HIGH  xlen={xh} pending={ph} lag={lh}\n"
                f"LOW   xlen={xl} pending={pl} lag={ll}\n",
                encoding="utf-8"
            )
            print(f"[4/4] ✅ 写入 flag 文件: {FLAG_FILE}")
            write_watch_log(
                f"FINISHED 进程数={proc_cnt} "
                f"HIGH(xlen+pending={xh}+{ph}={xh+ph if xh>=0 and ph>=0 else 'N/A'} lag={lh}) "
                f"LOW(xlen+pending={xl}+{pl}={xl+pl if xl>=0 and pl>=0 else 'N/A'} lag={ll}) "
                f"→ 总结已生成"
            )
        else:
            print("[4/4] ⚠️  总结脚本执行失败，未写入 flag，下次 watch 将重试")
    else:
        # ---- Step 4: 仍在跑，记录到 watch log ----
        line = (
            f"RUNNING 进程数={proc_cnt} "
            f"HIGH(xlen+pending={xh}+{ph}={xh+ph if xh>=0 and ph>=0 else 'N/A'} lag={lh}) "
            f"LOW(xlen+pending={xl}+{pl}={xl+pl if xl>=0 and pl>=0 else 'N/A'} lag={ll})"
        )
        write_watch_log(line)
        print(f"[3/4] 测试仍在运行 → 追加写入: {WATCH_LOG}")
        print(f"[4/4]   {line}")


if __name__ == "__main__":
    main()
