#!/usr/bin/env python3
"""
自动检测 10 Worker ofweek 分布式测试是否结束。

步骤：
1) pgrep -f 检查 ofweek_distributed/run.py 进程
2) 无进程 且 Redis Stream :stream:tasks:high (XLEN+pending==0 或 lag==0) → 跑完
3) 调用 collect_distributed_summary.py --watch 0 生成总结
4) 仍在跑 → 写监控日志到 /tmp/crawlo_watch.log
5) flag 文件已存在 → 跳过，避免重复
"""
import os
import sys
import subprocess
import time
from datetime import datetime
from pathlib import Path

EXAMPLE_DIR = Path("/Users/oscar/projects/Crawlo/examples/ofweek_distributed")
FLAG_FILE = Path("/tmp/crawlo_distributed_summary_done.flag")
WATCH_LOG = Path("/tmp/crawlo_watch.log")
PYTHON_BIN = "/Users/oscar/software/miniconda3/envs/crawlo/bin/python"

# 确保 subprocess 能找到标准系统命令（cron/计划任务 PATH 可能很窄）
_STD_ENV = os.environ.copy()
_STD_ENV["PATH"] = "/usr/bin:/bin:/usr/sbin:/sbin:" + _STD_ENV.get("PATH", "")

# Redis 配置（与 settings.py 保持一致）
REDIS_HOST = "127.0.0.1"
REDIS_PORT = 6379
REDIS_DB = 0
REDIS_PASSWORD = ""

# Stream key: crawlo:ofweek_distributed:stream:tasks:high
STREAM_KEY = "crawlo:ofweek_distributed:stream:tasks:high"
GROUP_NAME = "workers"


def pgrep_count() -> int:
    """步骤 1: 用 pgrep -f 检查 ofweek_distributed/run.py 进程数"""
    # 先尝试 psutil（更稳，不受 PATH 影响）
    try:
        import psutil
        count = 0
        for proc in psutil.process_iter(["pid", "cmdline"]):
            try:
                cmd = proc.info.get("cmdline") or []
                # 拼成完整命令行字符串，匹配 pgrep -f 的语义
                full = " ".join(cmd)
                if "ofweek_distributed/run.py" in full:
                    count += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return count
    except ImportError:
        pass

    # psutil 不可用时，用 /usr/bin/pgrep 绝对路径
    try:
        output = subprocess.check_output(
            ["/usr/bin/pgrep", "-f", "ofweek_distributed/run.py"],
            stderr=subprocess.DEVNULL,
            env=_STD_ENV,
        ).decode("utf-8", "replace").strip()
        if not output:
            return 0
        return len(output.splitlines())
    except subprocess.CalledProcessError:
        return 0
    except FileNotFoundError:
        # 最后兜底：用 /bin/ps + 过滤
        try:
            ps_out = subprocess.check_output(
                ["/bin/ps", "aux"],
                stderr=subprocess.DEVNULL,
                env=_STD_ENV,
            ).decode("utf-8", "replace")
            count = 0
            for line in ps_out.splitlines():
                if "ofweek_distributed/run.py" in line and "check_distributed_done" not in line:
                    count += 1
            return count
        except Exception as e2:
            print(f"  [pgrep 兜底异常] {e2}")
            return -1
    except Exception as e:
        print(f"  [pgrep 异常] {e}")
        return -1


def check_redis_stream():
    """
    步骤 2: 检查 Redis Stream 状态
    返回 (xlen, pending, lag, total_remaining, is_empty)
    key 不存在 → 视为空队列
    """
    try:
        import redis as _redis
    except ImportError as e:
        return None, None, None, None, str(e)

    try:
        client = _redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            password=REDIS_PASSWORD or None,
            db=REDIS_DB,
            decode_responses=True,
            socket_timeout=5,
        )

        # 先检查 key 是否存在（不存在 = 空）
        if not client.exists(STREAM_KEY):
            return 0, 0, 0, 0, True  # xlen, pending, lag, total, is_empty

        xlen = client.xlen(STREAM_KEY)

        # 获取 consumer group info（含 lag）
        lag = None
        try:
            groups = client.xinfo_groups(STREAM_KEY)
            for g in groups:
                if g.get("name") == GROUP_NAME:
                    lag = int(g.get("lag", 0) or 0)
                    break
        except Exception:
            # xinfo_groups 可能在 key 刚删时失败，按无 group 处理
            groups = []

        # 获取 pending 数量（group 不存在时 pending=0）
        pending = 0
        try:
            pending_info = client.xpending(STREAM_KEY, GROUP_NAME)
            if pending_info:
                pending = int(pending_info.get("pending", 0) or 0)
        except Exception:
            # group 不存在 → 无 pending
            pending = 0

        total_remaining = xlen + pending

        # 两种判定方式任一满足即可认为已空
        is_empty_by_total = (total_remaining == 0)
        is_empty_by_lag = (lag is not None and lag == 0)
        is_empty = is_empty_by_total or is_empty_by_lag

        return xlen, pending, lag, total_remaining, is_empty

    except Exception as e:
        return None, None, None, None, str(e)


def generate_summary() -> bool:
    """步骤 3: 调用 collect_distributed_summary.py --watch 0 生成最终总结"""
    script = EXAMPLE_DIR / "collect_distributed_summary.py"
    if not script.exists():
        print(f"  ❌ 总结脚本不存在: {script}")
        return False

    try:
        result = subprocess.run(
            [PYTHON_BIN, str(script), "--watch", "0"],
            cwd=str(EXAMPLE_DIR),
            capture_output=True,
            text=True,
            timeout=120,
            env=_STD_ENV,
        )
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)

        if result.returncode == 0:
            # 创建 flag 文件，避免重复生成
            FLAG_FILE.write_text(
                f"done_at={datetime.now().isoformat(timespec='seconds')}\n",
                encoding="utf-8",
            )
            return True
        else:
            print(f"  ❌ 总结脚本 exit code = {result.returncode}")
            return False
    except subprocess.TimeoutExpired:
        print("  ❌ 总结脚本执行超时（120s）")
        return False
    except Exception as e:
        print(f"  ❌ 执行总结脚本异常: {e}")
        return False


def write_watch_log(proc_count: int, xlen, pending, lag):
    """步骤 4: 写监控日志到 /tmp/crawlo_watch.log（带时间戳）"""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = (
        f"[{ts}] pgrep进程数={proc_count}  "
        f"Redis: XLEN={xlen}  Pending={pending}  Lag={lag}\n"
    )
    try:
        with open(WATCH_LOG, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception as e:
        print(f"  [写日志失败] {e}")
    # 同时 stdout 打出来
    print(line.rstrip())


def main():
    print("=" * 70)
    print(f"Crawlo ofweek 分布式测试自动检测 — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # ---------- 步骤 5: 检查 flag，已生成过总结就直接跳过 ----------
    if FLAG_FILE.exists():
        flag_content = FLAG_FILE.read_text(encoding="utf-8").strip()
        print(f"\n✅ flag 文件已存在（{FLAG_FILE}），跳过本次检测。")
        print(f"   flag 内容: {flag_content}")
        return

    # ---------- 步骤 1: pgrep 进程检查 ----------
    print("\n[步骤 1] pgrep -f ofweek_distributed/run.py ...")
    proc_count = pgrep_count()
    if proc_count < 0:
        print("  ⚠️  pgrep 执行异常，按未知处理（视为仍在跑，写入日志）")
    else:
        print(f"  运行中的 run.py 进程数: {proc_count}")

    # ---------- 步骤 2: Redis Stream 状态检查 ----------
    print(f"\n[步骤 2] 检查 Redis Stream {STREAM_KEY} ...")
    xlen, pending, lag, total_remaining, redis_result = check_redis_stream()

    if isinstance(redis_result, str):
        # 异常信息
        print(f"  ⚠️  Redis 访问异常: {redis_result}，无法确认是否已空，按未完成处理")
        redis_empty = False
    else:
        redis_empty = bool(redis_result)
        print(f"  XLEN={xlen}  Pending={pending}  XLEN+Pending={total_remaining}  Lag={lag}")
        print(f"  Redis 是否判定为空: {redis_empty}  "
              f"(XLEN+Pending==0: {total_remaining == 0 if total_remaining is not None else 'N/A'}  "
              f"或 Lag==0: {lag == 0 if lag is not None else 'N/A'})")

    # ---------- 综合判定 ----------
    no_process = (proc_count == 0)
    is_done = no_process and redis_empty

    if is_done:
        # ---------- 步骤 3: 生成最终总结 ----------
        print("\n[步骤 3] 无进程 + Redis 已空 → 确认跑完，开始生成总结...")
        ok = generate_summary()
        if ok:
            print("\n" + "=" * 70)
            print("✅ 分布式测试全部结束，最终总结已生成（flag 已写入，后续自动跳过）")
            print("=" * 70)
        else:
            print("\n⚠️  检测到已跑完，但总结生成失败，请手动执行总结脚本。")
    else:
        # ---------- 步骤 4: 仍在跑 → 写监控日志 ----------
        reason_parts = []
        if not no_process:
            reason_parts.append(f"仍有 {proc_count} 个 run.py 进程")
        if not redis_empty:
            reason_parts.append(
                f"Redis 非空 (XLEN={xlen},Pending={pending},Lag={lag})"
            )
        print(f"\n[步骤 4] 尚未跑完 — {'; '.join(reason_parts) if reason_parts else '状态未知'}，写入监控日志")
        write_watch_log(proc_count, xlen, pending, lag)


if __name__ == "__main__":
    main()
