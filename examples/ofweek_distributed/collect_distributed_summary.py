#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""
在分布式测试跑完后自动收集完整日志和统计汇总，输出到 summary 文本文件。
用法：
  python collect_distributed_summary.py [--snapshot]
    --snapshot  不等待主进程结束，直接打印当前快照
"""
import subprocess
import time
import argparse
from pathlib import Path
from datetime import datetime

EXAMPLE_ROOT = Path(__file__).resolve().parent
LOG_DIR = EXAMPLE_ROOT / "logs" / "workers"
WORKER_LOGS = sorted(LOG_DIR.glob("worker_*.log")) if LOG_DIR.exists() else []
OUT_TXT = EXAMPLE_ROOT / "logs" / f"distributed_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
REDIS_HOST = "127.0.0.1"
REDIS_PORT = 6379
REDIS_DB = 0
PYTHON_BIN = "/Users/oscar/software/miniconda3/envs/crawlo/bin/python"


def get_redis():
    import redis as _redis
    return _redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)


def cmd(args):
    try:
        return subprocess.check_output(args, stderr=subprocess.STDOUT).decode("utf-8", "replace")
    except subprocess.CalledProcessError as e:
        return f"(exit {e.returncode}) " + (e.output or b"").decode("utf-8", "replace")


def h(title, char="="):
    return "\n" + char * 78 + f"\n  {title}\n" + char * 78


def redis_snapshot(out):
    r = get_redis()
    out.append(h("Redis 实时快照"))
    try:
        keys = list(r.scan_iter(match="crawlo:ofweek_distributed*"))
    except Exception as e:
        out.append(f"  (Redis scan error: {e})")
        keys = []
    if not keys:
        out.append("  (无 crawlo:ofweek_distributed* 键 — 测试数据已清理)")
    for sk in sorted(keys):
        try:
            t = r.type(sk)
        except Exception:
            continue
        if t == "stream":
            out.append(f"  STREAM {sk}")
            try:
                xlen = r.xlen(sk)
                out.append(f"    XLEN = {xlen}")
                groups = r.xinfo_groups(sk)
                for g in groups:
                    out.append(f"    GROUP {g.get('name', '?')} "
                               f"consumers={g.get('consumers', '?')} "
                               f"pending={g.get('pending', '?')} "
                               f"lag={g.get('lag', '?')}")
            except Exception as e:
                out.append(f"    (stream info error: {e})")
        elif t == "set":
            try:
                scard = r.scard(sk)
                out.append(f"  SET {sk}  SCARD = {scard}")
            except Exception as e:
                out.append(f"  SET {sk}  (error: {e})")
        elif t == "hash":
            try:
                hlen = r.hlen(sk)
                out.append(f"  HASH {sk}  HLEN = {hlen}")
                if "registry:workers" in sk:
                    vals = r.hgetall(sk)
                    for fid, v in vals.items():
                        try:
                            import json
                            obj = json.loads(v)
                            out.append(
                                f"    worker={obj.get('id','')[:24]} status={obj.get('status')} "
                                f"done={obj.get('tasks_completed')} fail={obj.get('tasks_failed')} "
                                f"proc={obj.get('tasks_processing')} pid={obj.get('pid')}"
                            )
                        except Exception:
                            out.append(f"    {fid} = {str(v)[:80]}")
            except Exception as e:
                out.append(f"  HASH {sk}  (error: {e})")
        elif t == "zset":
            try:
                zcard = r.zcard(sk)
                out.append(f"  ZSET {sk}  ZCARD = {zcard}")
            except Exception as e:
                out.append(f"  ZSET {sk}  (error: {e})")
        elif t == "string":
            try:
                val = r.get(sk) or ""
                ttl = r.ttl(sk)
                out.append(f"  STR {sk} = {str(val)[:64]}  (TTL={ttl}s)")
            except Exception as e:
                out.append(f"  STR {sk}  (error: {e})")
        else:
            out.append(f"  {t.upper()} {sk}")


def per_worker_stats(out):
    out.append(h("每个 Worker 最终统计"))
    import re
    for log in sorted(WORKER_LOGS):
        try:
            text = log.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            out.append(f"  [{log.name}] <读取失败: {e}>")
            continue
        lines = text.splitlines()
        out.append(f"\n  --- {log.name}  ({len(text):,} bytes / {len(lines):,} lines) ---")

        # 启动信息
        starts = re.findall(r"生成了 (\d+) 个起始URL", text)
        skipped = bool(re.search(r"another Worker is generating|Seed lock held by active worker|skipping start_requests", text))
        mode = re.search(r"Run mode:[\s\S]{0,40}", text)
        qt = re.search(r"Queue type: \w+", text)
        out.append(f"    启动信息: {mode.group(0) if mode else 'N/A'}  {qt.group(0) if qt else 'N/A'}")
        out.append(f"    start_requests 执行次数: {len(starts)} (seed生成: {starts})  skipped_seed: {skipped}")

        # 关键计数
        list_pages = len(re.findall(r"正在解析页面:.*CATList", text))
        detail_pages = len(re.findall(r"正在解析详情页", text))
        items_extracted = len(re.findall(r"提取到详情页链接", text))
        errors = len(re.findall(r" ERROR |Traceback|Exception", text))
        out.append(f"    解析计数: list_pages={list_pages}  detail_pages={detail_pages}  items_extracted={items_extracted}  errors={errors}")

        # Seed lock 相关
        for pat in [r"Acquired seed lock[^\n]*", r"Cleared stale seed lock[^\n]*",
                    r"Seed lock held by active worker[^\n]*", r"skipping start_requests[^\n]*"]:
            m = re.findall(pat, text)
            for l in m:
                out.append(f"    锁日志: {l.strip()}")

        # 最终 stats block（从 'of_week stats' 开始的一段 dict）
        m = re.search(r"of_week stats\s*=\s*\{", text)
        if m:
            start = m.end() - 1
            # 找到第一个配对的 }
            depth = 0
            end = None
            for i in range(start, len(text)):
                ch = text[i]
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        end = i + 1
                        break
            if end:
                out.append(f"    最终 stats:")
                block = text[start:end]
                for line in block.splitlines()[:60]:
                    out.append(f"      {line.rstrip()}")
        else:
            # 否则拿末尾 reason / request_scheduler_count 等
            for kw in ["reason", "request_scheduler_count", "response_received_count",
                       "request_filtered_count", "item_successful_count",
                       "item_dropped_count", "item_failed_count",
                       "download_fail_retry_count", "download_error_count"]:
                pat = rf"'crawlo:{kw}'\s*:\s*([^,\n\}}]+)"
                m2 = re.findall(pat, text)
                if m2:
                    out.append(f"    {kw} = {m2[-1].strip()}")
            # Coordinated shutdown
            cs = re.findall(r"Coordinated shutdown[^\n]*", text)
            for l in cs[:3]:
                out.append(f"    协调退出: {l.strip()}")

        # 结尾 30 行日志（用于查看最终状态）
        last = lines[-30:]
        if last:
            out.append(f"    末 30 行日志:")
            for line in last:
                # 去掉过长的 URL/标题
                if len(line) > 200:
                    line = line[:200] + " <...truncated>"
                out.append(f"      {line.rstrip()}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", action="store_true",
                    help="不等待主进程结束，直接打印当前快照")
    ap.add_argument("--watch", type=int, default=0, metavar="SECONDS",
                    help="每隔 SECONDS 查一次主进程是否结束，直到收集到最终总结（0 = 只看一次）")
    args = ap.parse_args()

    snap = args.snapshot or args.watch <= 0
    out = []
    out.append(h(f"Crawlo 10-Worker 分布式测试总结（{'快照' if snap else '最终'}） {datetime.now().isoformat(timespec='seconds')}",
                 char="#"))

    out.append(f"  示例根目录: {EXAMPLE_ROOT}")
    out.append(f"  Worker 日志目录: {LOG_DIR}")
    out.append(f"  Python: {PYTHON_BIN}")

    if not snap:
        # wait for no python run.py children
        print(f"[watch] 等待 distributed 测试结束（每 {args.watch}s 检查一次）...", flush=True)
        while True:
            try:
                running = subprocess.check_output(
                    ["pgrep", "-f", "ofweek_distributed/run.py"]
                ).decode().strip()
            except subprocess.CalledProcessError:
                running = ""
            if not running:
                print("[watch] 没有运行中的 run.py，收集最终总结")
                break
            time.sleep(args.watch)
        time.sleep(3)  # buffer flush / close hooks

    redis_snapshot(out)
    per_worker_stats(out)
    out.append(h("EOF", "-"))

    text = "\n".join(out)
    OUT_TXT.parent.mkdir(parents=True, exist_ok=True)
    OUT_TXT.write_text(text, encoding="utf-8")
    print(f"✅ 总结已写入: {OUT_TXT}")
    print()
    print(text)


if __name__ == "__main__":
    main()
