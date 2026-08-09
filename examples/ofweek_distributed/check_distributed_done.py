#!/usr/bin/env python3
"""检测 ofweek 分布式测试是否结束并生成总结"""
import sys
import subprocess
import time
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path("/Users/oscar/projects/Crawlo")
EXAMPLE_DIR = PROJECT_ROOT / "examples" / "ofweek_distributed"
FLAG_FILE = Path("/tmp/crawlo_distributed_summary_done.flag")
WATCH_LOG = Path("/tmp/crawlo_watch.log")

def check_processes():
    """检查是否还有 ofweek_distributed/run.py 进程"""
    try:
        # 使用 subprocess.Popen 获取进程列表
        result = subprocess.run(
            ["osascript", "-e", 'tell application "System Events" to get name of every process'],
            capture_output=True,
            text=True,
            timeout=5
        )
        # 这个方法不太可靠，我们改用 ps 命令
    except:
        pass

    # 尝试通过 /proc 文件系统（macOS 不支持）或其他方式
    # 最可靠的方法是检查日志文件最后修改时间
    log_dir = EXAMPLE_DIR / "logs"
    if not log_dir.exists():
        return 0, []

    # 检查 worker 日志文件
    worker_logs = list(log_dir.glob("worker_*.log"))
    if not worker_logs:
        return 0, []

    # 检查最近修改的日志文件
    now = time.time()
    recent_logs = []
    for log in worker_logs:
        mtime = log.stat().st_mtime
        if now - mtime < 300:  # 5分钟内更新过
            recent_logs.append(log.name)

    # 如果有日志在5分钟内更新，认为进程还在运行
    return len(recent_logs), recent_logs


def check_redis_lag():
    """检查 Redis Stream lag"""
    try:
        # 添加项目路径到 sys.path
        sys.path.insert(0, str(PROJECT_ROOT))
        import redis

        # 从 settings 获取 Redis 配置
        sys.path.insert(0, str(EXAMPLE_DIR))
        from settings import REDIS_HOST, REDIS_PORT, REDIS_PASSWORD, REDIS_DB

        client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            password=REDIS_PASSWORD,
            db=REDIS_DB,
            decode_responses=True
        )

        stream_key = ":stream:tasks:high"
        group_name = "workers"

        # 获取 stream 长度
        stream_len = client.xlen(stream_key)

        # 获取 consumer group 信息
        try:
            groups = client.xinfo_groups(stream_key)
            lag = 0
            for group in groups:
                if group['name'] == group_name:
                    lag = int(group.get('lag', 0))
                    break
        except:
            # 如果 group 不存在，lag = stream_len
            lag = stream_len

        # 获取 pending 数量
        try:
            pending = client.xpending(stream_key, group_name)
            pending_count = pending.get('pending', 0) if pending else 0
        except:
            pending_count = 0

        return {
            'stream_len': stream_len,
            'lag': lag,
            'pending': pending_count,
            'total_remaining': stream_len + pending_count
        }
    except Exception as e:
        return {
            'error': str(e),
            'stream_len': -1,
            'lag': -1,
            'pending': -1,
            'total_remaining': -1
        }


def generate_summary():
    """生成分布式总结"""
    summary_script = EXAMPLE_DIR / "collect_distributed_summary.py"
    if not summary_script.exists():
        print(f"错误：总结脚本不存在: {summary_script}")
        return False

    try:
        result = subprocess.run(
            [sys.executable, str(summary_script), "--watch", "0"],
            cwd=str(EXAMPLE_DIR),
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode == 0:
            print("✅ 总结生成成功")
            print(result.stdout)
            # 创建完成标记
            FLAG_FILE.write_text(f"{datetime.now().isoformat()}\n")
            return True
        else:
            print(f"❌ 总结生成失败: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ 执行总结脚本异常: {e}")
        return False


def write_watch_log(process_count, redis_info):
    """写入监控日志"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] 进程数: {process_count}, Redis Lag: {redis_info.get('lag', 'N/A')}, Pending: {redis_info.get('pending', 'N/A')}, Stream Len: {redis_info.get('stream_len', 'N/A')}\n"

    with open(WATCH_LOG, 'a', encoding='utf-8') as f:
        f.write(log_line)

    print(log_line.strip())


def main():
    print("=" * 80)
    print("检测 ofweek 分布式测试结束状态")
    print("=" * 80)

    # 步骤 1: 检查进程
    print("\n[步骤 1] 检查进程状态...")
    process_count, recent_logs = check_processes()
    print(f"  发现 {process_count} 个活跃的 worker 日志: {recent_logs if recent_logs else '无'}")

    # 步骤 2: 检查 Redis lag
    print("\n[步骤 2] 检查 Redis Stream 状态...")
    redis_info = check_redis_lag()

    if 'error' in redis_info:
        print(f"  ❌ Redis 连接失败: {redis_info['error']}")
    else:
        print(f"  Stream 长度: {redis_info['stream_len']}")
        print(f"  Consumer Group Lag: {redis_info['lag']}")
        print(f"  Pending 任务数: {redis_info['pending']}")
        print(f"  总剩余任务: {redis_info['total_remaining']}")

    # 判断是否完成
    has_processes = process_count > 0
    has_tasks = redis_info.get('total_remaining', 1) > 0 if 'error' not in redis_info else True

    # 步骤 5: 检查是否已生成过总结
    if FLAG_FILE.exists():
        print(f"\n✅ 已生成过总结文件（标记文件: {FLAG_FILE}），跳过")
        return

    # 如果还在运行，写入监控日志
    if has_processes or has_tasks:
        print("\n⏳ 测试仍在运行中...")
        write_watch_log(process_count, redis_info)
        return

    # 步骤 3: 生成总结
    print("\n✅ 测试已完成！开始生成总结...")
    success = generate_summary()

    if success:
        print(f"\n{'='*80}")
        print("✅ 分布式测试已结束，总结已生成")
        print(f"{'='*80}")
    else:
        print(f"\n{'='*80}")
        print("❌ 总结生成失败，请手动检查")
        print(f"{'='*80}")


if __name__ == "__main__":
    main()