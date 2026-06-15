#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
动态配置管理器

运行时调整集群行为：限速、暂停/恢复、动态种子 URL、Worker 并发度。
采用双通道通知机制：
- Pub/Sub：即时通知所有 Worker
- 持久化 Key：断连重连后的兜底恢复

Key 设计：
    crawlo:{project}:control:state         String   控制状态（running/paused/shutdown）
    crawlo:{project}:config:rate_limits    HASH     域名级速率覆盖
    crawlo:{project}:config:seed_urls      LIST     动态种子 URL
"""
import json
from typing import Dict, Any, Optional, List

from crawlo.logging import get_logger


class DynamicConfig:
    """
    分布式动态配置。

    使用示例：
        config = DynamicConfig(redis_client, messenger, "crawlo:project:spider")
        await config.pause_spider()        # Pub/Sub + SET
        await config.resume_spider()       # Pub/Sub + SET
        await config.set_rate_limit("example.com", 2.0)  # HSET + PUBLISH
    """

    def __init__(
        self,
        redis_client,
        messenger=None,
        namespace: str = "crawlo:default",
        rate_limiter=None,
        enabled: bool = True,
    ):
        """
        初始化动态配置。

        Args:
            redis_client: Redis 异步客户端
            messenger: ClusterMessenger 实例（用于 Pub/Sub 通知）
            namespace: 命名空间
            rate_limiter: DistributedRateLimiter 实例（用于同步限速调整）
            enabled: 是否启用动态配置
        """
        self._redis = redis_client
        self._messenger = messenger
        self._ns = namespace
        self._rate_limiter = rate_limiter
        self._enabled = enabled

        # Keys
        self._control_key = f"{self._ns}:control:state"
        self._rate_key = f"{self._ns}:config:rate_limits"
        self._seed_key = f"{self._ns}:config:seed_urls"
        self._concurrency_key = f"{self._ns}:config:concurrency"

        self.logger = get_logger(self.__class__.__name__)

    # ---- 控制指令（双通道） ----

    async def pause_spider(self):
        """
        暂停爬虫（所有 Worker 停止消费新任务）。

        双通道通知：
        1. SET control:state = "paused"（持久化，断连可恢复）
        2. PUBLISH channel:control {action: "pause"}（即时通知）
        """
        await self._redis.set(self._control_key, "paused")
        await self._publish("control", {"action": "pause"})
        self.logger.info("Cluster paused")

    async def resume_spider(self):
        """恢复爬虫"""
        await self._redis.set(self._control_key, "running")
        await self._publish("control", {"action": "resume"})
        self.logger.info("Cluster resumed")

    async def shutdown_cluster(self, cleanup: bool = True):
        """
        通知所有 Worker 停止，并清理运行数据。

        Args:
            cleanup: 是否清理 Redis 中的运行数据（stream、dedup、registry 等）。
                     默认 True。设为 False 可保留数据用于调试。
        """
        await self._redis.set(self._control_key, "shutdown")
        await self._publish("control", {"action": "shutdown"})
        self.logger.warning("Cluster shutdown signal sent")

        if cleanup:
            await self._cleanup_run_data()

    async def get_control_state(self) -> str:
        """
        读取持久化控制状态（兜底）。

        Worker 每次处理请求前调用此方法，检查控制状态。

        Returns:
            "running" / "paused" / "shutdown" / None（未设置）
        """
        state = await self._redis.get(self._control_key)
        if state:
            return state.decode("utf-8") if isinstance(state, bytes) else state
        return "running"  # 默认正常运行

    async def _cleanup_run_data(self):
        """
        清理本轮运行的 Redis 数据。

        在 Leader 确认所有任务完成后调用。

        清理策略：
        - control:state  → 必须清理（残留 shutdown 会导致下次启动立即退出）
        - cluster:leader → 清理（释放 leader 锁）
        - 其他 key 均保留：
          - stream:tasks        → ACK+XDEL 已逐条删除，空 Stream 下次启动可直接复用
          - registry:workers/heartbeats → 保留 Worker 信息供运维查看
          - dedup:request/item  → 保留，跨运行去重有价值

        注意：不删除 config:rate_limits 和 config:seed_urls，这些是用户配置。
        """
        keys_to_delete = [
            f"{self._ns}:cluster:leader",
        ]

        try:
            deleted = await self._redis.delete(*keys_to_delete)
            # 重置 control:state 为 running（而非删除），防止后续 Worker
            # 在 Leader 退出后获取锁时误判为 running 并重复触发 shutdown
            await self._redis.set(f"{self._ns}:control:state", "running")

            # 不清理以下 key：
            # - stream:tasks：ACK+XDEL 已逐条删除消息，空 Stream 下次启动复用（XGROUP CREATE MKSTREAM）
            # - registry:workers / registry:heartbeats：保留 Worker 信息供运维查看
            # - dedup:request / dedup:item：跨运行去重有价值

            self.logger.info(
                f"Cleanup: deleted {deleted} Redis keys for completed run "
                f"(namespace={self._ns}, dedup_preserved=True, "
                f"stream_preserved=True, registry_preserved=True)"
            )
        except Exception as e:
            self.logger.warning(f"Cleanup failed (data will persist until TTL expires): {e}")

    # ---- 限速调整（双通道） ----

    async def set_rate_limit(self, domain: str, rate: float, capacity: Optional[int] = None):
        """
        动态调整域名级速率限制。

        1. HSET config:rate_limits {domain} = {rate}
        2. PUBLISH channel:config {action: "rate_limit", domain, rate}
        3. 如果绑定了 rate_limiter，同步生效
        """
        data = {"rate": rate}
        if capacity:
            data["capacity"] = capacity

        await self._redis.hset(self._rate_key, domain, json.dumps(data))

        await self._publish("config", {
            "action": "rate_limit",
            "domain": domain,
            "rate": rate,
            "capacity": capacity,
        })

        # 同步到限流器
        if self._rate_limiter:
            await self._rate_limiter.set_rate(domain, rate, capacity)

        self.logger.info(f"Rate limit updated: {domain} = {rate} req/s")

    async def remove_rate_limit(self, domain: str):
        """移除域名级速率限制"""
        await self._redis.hdel(self._rate_key, domain)
        await self._publish("config", {"action": "rate_limit_remove", "domain": domain})
        if self._rate_limiter:
            await self._rate_limiter.remove_rate(domain)

    async def get_rate_limits(self) -> Dict[str, Dict]:
        """获取所有速率限制"""
        raw = await self._redis.hgetall(self._rate_key)
        result = {}
        for k, v in raw.items():
            k_str = k.decode("utf-8") if isinstance(k, bytes) else k
            v_str = v.decode("utf-8") if isinstance(v, bytes) else v
            result[k_str] = json.loads(v_str)
        return result

    # ---- 动态种子 URL ----

    async def add_seed_urls(self, urls: List[str]):
        """
        动态添加种子 URL。

        所有 Worker 监听 config 频道，收到通知后入队这些 URL。
        """
        for url in urls:
            await self._redis.rpush(self._seed_key, url)

        await self._publish("config", {
            "action": "seed_urls",
            "count": len(urls),
        })
        self.logger.info(f"{len(urls)} seed URLs added dynamically")

    async def pop_seed_urls(self, count: int = 10) -> List[str]:
        """Worker 拉取动态种子 URL"""
        urls = []
        for _ in range(count):
            url = await self._redis.lpop(self._seed_key)
            if url:
                urls.append(url.decode("utf-8") if isinstance(url, bytes) else url)
            else:
                break
        return urls

    # ---- Worker 并发度 ----

    async def set_concurrency(self, worker_id: str, concurrency: int):
        """调整指定 Worker 的并发度"""
        await self._redis.hset(self._concurrency_key, worker_id, concurrency)
        await self._publish("config", {
            "action": "concurrency",
            "worker_id": worker_id,
            "concurrency": concurrency,
        })

    async def get_concurrency(self, worker_id: str) -> int:
        """获取 Worker 的并发度配置"""
        val = await self._redis.hget(self._concurrency_key, worker_id)
        if val:
            return int(val.decode("utf-8") if isinstance(val, bytes) else val)
        return 0

    # ---- 内部 ----

    async def _publish(self, channel: str, message: dict):
        """通过 Messenger 发布消息"""
        if not self._enabled:
            return
        if self._messenger:
            try:
                await self._messenger.publish(channel, message)
            except Exception as e:
                self.logger.debug(f"Publish failed: {e}")


__all__ = ["DynamicConfig"]
