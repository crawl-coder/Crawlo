#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""
自动检测 ofweek 10-Worker 分布式测试是否结束，严格按用户指定的5步执行：
  1) pgrep -f（不可用时 psutil fallback）检查 ofweek_distributed/run.py 进程数
  2) 无进程 且 Redis Stream :stream:tasks:high 的 XLEN+pending==0 或 lag==0 → 认为已跑完
  3) cd 到示例目录，调用 collect_distributed_summary.py --watch 0 生成总结
  4) 仍在跑 → 追加一条「进程数 + Redis lag」到 /tmp/crawlo_watch.log（带时间戳）
  5) 已跑完且 flag 文件(/tmp/crawlo_distributed_summary_done.flag)存在 → 跳过，避免重复

此脚本必须用 crawlo conda 环境的 Python 运行，以确保 redis / psutil 可用。
"""
import os
import sys
import subprocess
from datetime import datetime
from pathlib import Path

PYTHON_BIN = "/Users/oscar/software/miniconda3/envs/crawlo/bin/python"
FLAG_FILE = Path("/tmp/crawlo_distributed_summary_done.flag")
WATCH_LOG = Path("/tmp/crawlo_watch.log")
EXAMPLE_DIR = Path("/Users/oscar/projects/Crawlo/examples/ofweek_distributed")
# 用户关注的 stream key 后缀（不写死前缀，通过 SCAN 自动发现）
STREAM_KEY_SUFFIX = ":stream:tasks:high"
SUMMARY_SCRIPT = EXAMPLE_DIR / "collect_distributed_summary.py"
PROCESS_TARGET = "ofweek_distributed/run.py"


def count_processes():
    """Step 1: 用 pgrep -f 统计 ofweek_distributed/run.py 进程数；失败时 fallback 到 psutil."""
    # --- pgrep 优先 ---
    for pgrep in ["/usr/bin/pgrep", "/bin/pgrep", "/usr/local/bin/pgrep", "/opt/homebrew/bin/pgrep"]:
        if os.path.exists(pgrep):
            try:
                proc = subprocess.run(
                    [pgrep, "-f", PROCESS_TARGET],
                    capture_output=True, text=True, timeout=10
                )
                if proc.returncode == 0 and proc.stdout.strip():
                    # 排除掉当前脚本自身/子命令的匹配（pgrep 不会匹配自己，但会匹配包含目标字符串的父进程）
                    lines = [l for l in proc.stdout.splitlines() if l.strip().isdigit()]
                    # 二次过滤：通过 /proc/<pid>/cmdline 或 psutil 确认真实 run.py 进程
                    real = 0
                    try:
                        import psutil
                        valid_pids = {int(x) for x in lines}
                        for p in psutil.process_iter(["pid", "cmdline"]):
                            if p.info.get("pid") not in valid_pids:
                                continue
                            cmdline = p.info.get("cmdline") or []
                            joined = " ".join(cmdline)
                            # 必须是真正运行 run.py 的进程，而不是 grep/pgrep/watch 本身
                            if ("run.py" in joined
                                    and "ofweek_distributed" in joined
                                    and "_watch_distributed" not in joined
                                    and "grep" not in joined
                                    and "pgrep" not in joined):
                                real += 1
                        return real
                    except Exception:
                        return len(lines)
                return 0
            except (subprocess.TimeoutExpired, OSError):
                break  # pgrep 不可用，fallback

    # --- Fallback: psutil ---
    try:
        import psutil
    except Exception as e:
        print(f"  [WARN] pgrep 不可用且 psutil import 失败: {e}", file=sys.stderr)
        return -1
    cnt = 0
    for p in psutil.process_iter(["pid", "cmdline"]):
        try:
            cmdline = p.info.get("cmdline") or []
        except Exception:
            continue
        joined = " ".join(cmdline)
        # 严格匹配：真正运行 run.py 的进程，排除当前 watch 脚本/检测命令自身
        if ("run.py" in joined
                and "ofweek_distributed" in joined
                and "_watch_distributed" not in joined
                and "grep" not in joined):
            cnt += 1
    return cnt


def find_high_stream_key(r):
    """通过 SCAN 查找匹配 *:stream:tasks:high 后缀的 stream key；优先选 ofweek_distributed 项目下的。"""
    candidates = []
    try:
        for k in r.scan_iter(match=f"*{STREAM_KEY_SUFFIX}"):
            if r.type(k) == "stream":
                candidates.append(k)
    except Exception:
        pass
    if not candidates:
        return None
    # 优先包含 ofweek_distributed 的 key
    for k in candidates:
        if "ofweek_distributed" in k:
            return k
    return candidates[0]


def get_high_stream_metrics():
    """Step 2: 查询 :stream:tasks:high 的 (xlen, pending, lag)，返回 dict.
    通过 SCAN 自动发现匹配后缀的 key，避免硬编码前缀。"""
    info = {"key": None, "xlen": -1, "pending": -1, "lag": -1, "note": ""}
    try:
        import redis
    except Exception as e:
        info["note"] = f"redis import error: {e}"
        return info

    try:
        r = redis.Redis(host="127.0.0.1", port=6379, db=0, decode_responses=True)
    except Exception as e:
        info["note"] = f"redis connect error: {e}"
        return info

    stream_key = find_high_stream_key(r)
    info["key"] = stream_key or f"(auto-discover:*{STREAM_KEY_SUFFIX})"

    if stream_key is None:
        info.update({"xlen": 0, "pending": 0, "lag": 0,
                     "note": "no_matching_stream_key(empty_stream)"})
        return info

    try:
        info["xlen"] = r.xlen(stream_key)
    except Exception as e:
        info["note"] = f"XLEN error on {stream_key}: {e}"
        return info

    group_names = []
    pending_total = 0
    lag_total = 0
    try:
        groups = r.xinfo_groups(stream_key)
        for g in groups:
            group_names.append(g.get("name", "?"))
            pending_total += int(g.get("pending", 0) or 0)
            lag_total += int(g.get("lag", 0) or 0)
    except Exception as e:
        info["note"] = f"XINFO_GROUPS error on {stream_key}: {e} groups={group_names}"
        return info

    info.update({
        "pending": pending_total,
        "lag": lag_total,
        "note": f"groups={group_names}" if group_names else "no_consumer_group"
    })
    return info


def write_watch_log(process_count, metrics):
    """Step 4: 写一条状态到 /tmp/crawlo_watch.log，带时间戳."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    xlen = metrics.get("xlen", "N/A")
    pending = metrics.get("pending", "N/A")
    lag = metrics.get("lag", "N/A")
    total = (xlen + pending) if isinstance(xlen, int) and isinstance(pending, int) else "N/A"
    line = (f"[{ts}] RUNNING 进程数={process_count} "
            f"HIGH(xlen+pending={xlen}+{pending}={total} lag={lag})")
    try:
        WATCH_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(WATCH_LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
        print(f"  → 已写入监控日志: {WATCH_LOG}")
        print(f"    {line}")
    except Exception as e:
        print(f"  [WARN] 写入监控日志失败: {e}")
        print(f"    {line}")


def run_summary_and_mark_flag(metrics):
    """Step 3: cd 到示例目录，调用 collect_distributed_summary.py --watch 0，成功后写 flag."""
    print(f"  进入目录: {EXAMPLE_DIR}")
    print(f"  执行: {PYTHON_BIN} {SUMMARY_SCRIPT} --watch 0", flush=True)
    old_cwd = os.getcwd()
    ok = False
    try:
        os.chdir(EXAMPLE_DIR)
        proc = subprocess.run(
            [PYTHON_BIN, str(SUMMARY_SCRIPT), "--watch", "0"],
            capture_output=True, timeout=300, encoding="utf-8", errors="replace"
        )
        if proc.stdout:
            print(proc.stdout, flush=True)
        if proc.stderr:
            sys.stderr.write("  [STDERR]\n" + proc.stderr[:3000] + "\n")
            sys.stderr.flush()
        ok = (proc.returncode == 0)
    except Exception as e:
        print(f"  [ERROR] 执行总结脚本异常: {e}", file=sys.stderr)
    finally:
        os.chdir(old_cwd)

    if ok:
        # Step 5: 写入 flag，避免后续重复生成
        xlen = metrics.get("xlen", "?")
        pending = metrics.get("pending", "?")
        lag = metrics.get("lag", "?")
        flag_content = (
            f"done_at={datetime.now().isoformat(timespec='seconds')}\n"
            f"processes=0\n"
            f"HIGH xlen={xlen} pending={pending} lag={lag}\n"
            f"summary_script={SUMMARY_SCRIPT}\n"
        )
        try:
            FLAG_FILE.write_text(flag_content, encoding="utf-8")
            print(f"  ✅ 写入完成标记: {FLAG_FILE}")
        except Exception as e:
            print(f"  [WARN] 写入 flag 失败: {e}")

        # 写一条 FINISHED 到 watch log
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        total = (xlen + pending) if isinstance(xlen, int) and isinstance(pending, int) else "N/A"
        finish_line = (f"[{ts}] FINISHED 进程数=0 "
                       f"HIGH(xlen+pending={xlen}+{pending}={total} lag={lag}) → 总结已生成")
        try:
            WATCH_LOG.parent.mkdir(parents=True, exist_ok=True)
            with open(WATCH_LOG, "a", encoding="utf-8") as f:
                f.write(finish_line + "\n")
        except Exception:
            pass
    return ok


def main():
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"=== Crawlo 10-Worker 分布式测试自动检测 {ts} ===", flush=True)
    print()

    # ---------- Step 5(前置): 已生成过总结 → 直接跳过 ----------
    if FLAG_FILE.exists():
        print(f"✅ Flag 文件已存在: {FLAG_FILE}")
        print("   （表示已生成过最终总结，跳过本次检测）")
        try:
            done_time = datetime.fromtimestamp(FLAG_FILE.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            print(f"   标记时间: {done_time}")
            content = FLAG_FILE.read_text(encoding="utf-8").rstrip()
            print(f"   Flag 内容:\n{content}")
            summaries = sorted((EXAMPLE_DIR / "logs").glob("distributed_summary_*.txt"))
            if summaries:
                latest = summaries[-1]
                print(f"   最新总结文件: {latest}  ({latest.stat().st_size:,} bytes)")
            else:
                print("   ⚠️  未找到 distributed_summary_*.txt 总结文件")
        except Exception as e:
            print(f"   [WARN] 读取 flag/summary 信息出错: {e}")
        return

    # ---------- Step 1: 检查 ofweek_distributed/run.py 进程 ----------
    print("[1/4] Step 1: 检查运行中的 run.py 进程 (pgrep -f / psutil fallback) ...")
    proc_cnt = count_processes()
    if proc_cnt < 0:
        print("      ⚠️  进程检测失败，暂时认为仍有进程在跑（保守策略）")
    print(f"      → 进程数 = {proc_cnt}")

    # ---------- Step 2: 检查 Redis Stream :stream:tasks:high ----------
    print("[2/4] Step 2: 检查 Redis Stream :stream:tasks:high ...")
    metrics = get_high_stream_metrics()
    print(f"      key      = {metrics['key']}")
    print(f"      xlen     = {metrics['xlen']}")
    print(f"      pending  = {metrics['pending']}")
    print(f"      lag      = {metrics['lag']}")
    print(f"      note     = {metrics['note']}")

    # 判定：无进程 且 (XLEN+pending==0  OR  lag==0)
    no_process = (proc_cnt == 0)
    xlen_int = metrics["xlen"]
    pending_int = metrics["pending"]
    lag_int = metrics["lag"]
    cond_a = (isinstance(xlen_int, int) and isinstance(pending_int, int)
              and (xlen_int + pending_int) == 0)
    cond_b = (isinstance(lag_int, int) and lag_int == 0)
    stream_ok = cond_a or cond_b
    is_done = no_process and stream_ok

    print()
    print(f"      [判定条件]")
    print(f"        无进程(proc_cnt==0)       → {no_process}")
    print(f"        XLEN+pending==0           → {cond_a}  ({xlen_int}+{pending_int}="
          f"{xlen_int + pending_int if isinstance(xlen_int,int) and isinstance(pending_int,int) else 'N/A'})")
    print(f"        lag==0                    → {cond_b}  (lag={lag_int})")
    print(f"        stream_ok=(A∨B)           → {stream_ok}")
    print(f"        最终 is_done=(无∧ok)      → {is_done}")
    print()

    if is_done:
        # ---------- Step 3: 生成最终总结 ----------
        print("[3/4] Step 3: ✅ 检测到分布式测试已结束，开始生成最终总结 ...", flush=True)
        ok = run_summary_and_mark_flag(metrics)
        print()
        if ok:
            print("[4/4] ✅ 全部完成：总结已生成 + flag 已写入，后续 watch 将自动跳过")
        else:
            print("[4/4] ⚠️  总结脚本执行失败，未写入 flag — 下次 watch 将重试生成总结")
    else:
        # ---------- Step 4: 仍在跑 → 写 watch log ----------
        print("[3/4] Step 3: 测试仍在运行中（或 Redis 状态未清空），跳过总结生成")
        print("[4/4] Step 4: 写入监控日志 ...")
        write_watch_log(proc_cnt if proc_cnt >= 0 else "UNKNOWN", metrics)


if __name__ == "__main__":
    main()
