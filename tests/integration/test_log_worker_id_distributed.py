#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
分布式 Worker 日志隔离（端到端集成测试）
========================================

真实场景验证：
1. 2 个 Worker 通过 Redis Stream 分布式跑一个本地 HTTP 站点的爬虫；
2. 每个 Worker 进集群后，日志文件名自动追加 worker_id：
   ``logs/{project}.{worker_id}.log``，两个 Worker 日志互不覆盖；
3. 基础文件 ``logs/{project}.log`` 不因切换而被删除。

验证点在“进集群后立即切换日志文件”，因此两个 Worker 日志就绪后即终止进程，
避免等待框架协调退出（10s 级轮询）拖慢测试。

前置条件：本地 Redis（127.0.0.1:6379）可用，否则跳过。
"""

import os
import subprocess
import sys
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest


PAGES = {f"page{i}.html": f"<html><body>page {i} content</body></html>" for i in range(1, 6)}


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        name = self.path.lstrip("/")
        body = PAGES.get(name, "<html><body>404</body></html>")
        status = 200 if name in PAGES else 404
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body.encode("utf-8"))))
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))

    def log_message(self, *args):
        pass


def _redis_available() -> bool:
    try:
        import redis
        r = redis.Redis(host="127.0.0.1", port=6379, socket_connect_timeout=2)
        return bool(r.ping())
    except Exception:
        return False


def _make_fixture_project(root: Path, project_name: str, port: int) -> Path:
    """构造最小分布式项目（settings / spider / run.py / crawlo.cfg）。"""
    pkg = root / project_name
    (pkg / "spiders").mkdir(parents=True)
    (root / "logs").mkdir()

    (root / "crawlo.cfg").write_text(
        "[settings]\ndefault = {}.settings\n".format(project_name),
        encoding="utf-8",
    )
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "spiders" / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "settings.py").write_text(
        f"""# -*- coding: UTF-8 -*-
import os
from crawlo.core.config import CrawloConfig

config = CrawloConfig.distributed(
    project_name={project_name!r},
    concurrency=2,
    download_delay=0.05,
)
globals().update(config.to_dict())

SPIDER_MODULES = [{project_name!r} + '.spiders']

LOG_LEVEL = 'INFO'
LOG_FILE = 'logs/{project_name}.log'
LOG_FILE_WHEN = 'midnight'
LOG_FILE_BACKUP_COUNT = 7
LOG_FILE_UTF8_BACKUP = True
LOG_CONSOLE_ENABLED = False
PORT = int(os.environ.get('ITEST_PORT', {port}))
""",
        encoding="utf-8",
    )
    (pkg / "spiders" / "hello.py").write_text(
        f"""# -*- coding: UTF-8 -*-
import os
from crawlo.spider import Spider
from crawlo import Request


class HelloSpider(Spider):
    name = 'hello'

    def start_requests(self):
        port = os.environ.get('ITEST_PORT', {port})
        for i in range(1, 6):
            yield Request(
                f'http://127.0.0.1:{{port}}/page{{i}}.html',
                callback=self.parse,
            )

    def parse(self, response):
        self.logger.info(f'parsed {{response.url}} len={{len(response.text)}}')
        yield {{'url': response.url}}
""",
        encoding="utf-8",
    )
    (root / "run.py").write_text(
        """#!/usr/bin/python
# -*- coding: UTF-8 -*-
import asyncio
from crawlo.crawler import CrawlerProcess


def main():
    process = CrawlerProcess()
    asyncio.run(process.crawl('hello'))


if __name__ == '__main__':
    main()
""",
        encoding="utf-8",
    )
    return root


@pytest.mark.skipif(not _redis_available(), reason="本地 Redis 不可用")
def test_distributed_workers_get_independent_logs(tmp_path):
    """2 个 Worker 各自产出 logs/{project}.{worker_id}.log，互不覆盖。"""
    repo_root = Path(__file__).resolve().parents[2]

    # 本地 HTTP 站点
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    port = server.server_address[1]
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    project_name = f"itest_{uuid.uuid4().hex[:8]}"
    fixture = _make_fixture_project(tmp_path / project_name, project_name, port)

    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(
        [str(fixture), str(repo_root), env.get("PYTHONPATH", "")]
    )
    env["ITEST_PORT"] = str(port)

    procs = []
    try:
        for _ in range(2):
            procs.append(subprocess.Popen(
                [sys.executable, "run.py"],
                cwd=str(fixture),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            ))

        # 轮询：两个 Worker 的独立日志均出现且含集群初始化记录
        log_dir = fixture / "logs"
        deadline = time.time() + 90
        worker_logs = []
        while time.time() < deadline:
            worker_logs = sorted(log_dir.glob(f"{project_name}.*.log"))
            if len(worker_logs) >= 2:
                texts = [p.read_text(encoding="utf-8", errors="replace") for p in worker_logs]
                if all("Cluster initialized: worker=" in t for t in texts):
                    break
            time.sleep(1)
        else:
            for p in procs:
                p.kill()
            pytest.fail(
                "等待超时：未在 90s 内看到两个含集群初始化记录的 Worker 日志，"
                f"当前: {sorted(p.name for p in log_dir.iterdir())}"
            )

        # 目标已达成，终止 Worker（避免等待协调退出）
        for p in procs:
            if p.poll() is None:
                p.terminate()
        time.sleep(2)
        for p in procs:
            if p.poll() is None:
                p.kill()

        outputs = []
        for p in procs:
            try:
                out, _ = p.communicate()
            except Exception:
                out = ""
            outputs.append(out)
    finally:
        server.shutdown()
        server.server_close()
        for p in procs:
            if p.poll() is None:
                p.kill()

    assert len(worker_logs) == 2, (
        f"应产出 2 个独立 Worker 日志，实际 {len(worker_logs)}: "
        f"{sorted(p.name for p in log_dir.iterdir())}"
    )

    worker_ids = []
    for log_file in worker_logs:
        text = log_file.read_text(encoding="utf-8", errors="replace")
        assert text.strip(), f"Worker 日志为空: {log_file}"
        assert "Cluster initialized: worker=" in text, (
            f"日志内容异常（缺少集群初始化记录）: {log_file}"
        )
        assert "Failed to clean up expired log files" not in text, (
            f"日志清理应正常（存在 AttributeError 回归）: {log_file}"
        )
        worker_ids.append(log_file.name[len(project_name) + 1: -len(".log")])

    assert worker_ids[0] != worker_ids[1], "两个 Worker 日志名应包含不同 worker_id"

    # 基础文件（进集群前少量日志）保留，未被删除
    base_log = log_dir / f"{project_name}.log"
    assert base_log.exists() or any(log_dir.glob(f"{project_name}.log.*")), \
        "基础日志文件/轮转文件不应丢失"

    print(f"\n  Worker 日志: {[p.name for p in worker_logs]}")
    print(f"  Worker IDs : {worker_ids}")
