#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
集群消息通信（Redis Pub/Sub + 持久化 Key 兜底）

双通道设计原因：
- Pub/Sub：即时通知所有订阅 Worker，延迟低
- 持久化 Key：Worker 断连期间的消息不会丢失，重连后可恢复状态

预定义频道：
    crawlo:{project}:control     — 控制指令（暂停/恢复/停止）
    crawlo:{project}:config      — 配置变更（限速调整/种子URL/并发度）
    crawlo:{project}:events      — 事件通知（Worker 加入/退出）
    crawlo:{project}:alerts      — 告警（限速触发/封禁检测）
"""
import json
import asyncio
from typing import Optional, Callable, Dict, Any

from crawlo.logging import get_logger


class ClusterMessenger:
    """
    节点间消息通信。

    使用示例：
        messenger = ClusterMessenger(redis_client, "crawlo:project:spider")
        await messenger.start()

        # 订阅控制消息
        async def on_pause(msg):
            print("Pausing...")
        await messenger.subscribe("control", on_pause)

        # 发布消息
        await messenger.publish("control", {"action": "pause"})

        # 持久化兜底
        state = await messenger.get_control_state()
    """

    # 频道常量
    CHANNEL_CONTROL = "control"
    CHANNEL_CONFIG = "config"
    CHANNEL_EVENTS = "events"
    CHANNEL_ALERTS = "alerts"

    def __init__(
        self,
        redis_client,
        namespace: str = "crawlo:default",
    ):
        """
        初始化消息通信。

        Args:
            redis_client: Redis 异步客户端
            namespace: 命名空间
        """
        self._redis = redis_client
        self._ns = namespace

        # 订阅存储
        self._subscribers: Dict[str, list] = {
            self.CHANNEL_CONTROL: [],
            self.CHANNEL_CONFIG: [],
            self.CHANNEL_EVENTS: [],
            self.CHANNEL_ALERTS: [],
        }

        # 持久化 Key
        self._control_state_key = f"{self._ns}:control:state"

        self._pubsub: Optional[asyncio.Task] = None
        self._running = False
        self._listener_task: Optional[asyncio.Task] = None

        self.logger = get_logger(self.__class__.__name__)

    # ---- 启停 ----

    async def start(self):
        """启动消息监听（后台协程）"""
        if self._running:
            return

        self._running = True
        self._listener_task = asyncio.create_task(self._listen_loop())
        self.logger.debug("Messenger started")

    async def stop(self):
        """停止消息监听"""
        self._running = False
        if self._listener_task and not self._listener_task.done():
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
        self.logger.debug("Messenger stopped")

    # ---- 发布 ----

    async def publish(self, channel: str, message: Dict[str, Any]):
        """
        发布消息到频道。

        Args:
            channel: 频道名（control/config/events/alerts）
            message: 消息体（dict，自动 JSON 序列化）
        """
        topic = f"{self._ns}:{channel}"
        payload = json.dumps(message, ensure_ascii=False)
        try:
            await self._redis.publish(topic, payload)
        except Exception as e:
            self.logger.debug(f"Publish to {topic} failed: {e}")

    # ---- 订阅 ----

    async def subscribe(self, channel: str, handler: Callable):
        """
        订阅频道消息。

        Args:
            channel: 频道名
            handler: 异步回调 async def handler(message)
        """
        if channel not in self._subscribers:
            self._subscribers[channel] = []
        self._subscribers[channel].append(handler)

    # ---- 持久化状态兜底 ----

    async def get_control_state(self) -> str:
        """
        读取持久化控制状态（兜底机制）。

        弥补 Pub/Sub 的 fire-and-forget 特性：
        Worker 断连期间发布的 pause/shutdown 不会丢失，
        重连后读取此 Key 即可恢复正确状态。

        Returns:
            "running" / "paused" / "shutdown"
        """
        try:
            state = await self._redis.get(self._control_state_key)
            if state:
                return state.decode("utf-8") if isinstance(state, bytes) else state
        except Exception:
            pass
        return "running"

    # ---- 内部监听循环 ----

    async def _listen_loop(self):
        """消息监听主循环"""
        while self._running:
            try:
                pubsub = self._redis.pubsub()

                # 订阅所有预定义频道
                channels = [
                    f"{self._ns}:{c}"
                    for c in (self.CHANNEL_CONTROL, self.CHANNEL_CONFIG,
                              self.CHANNEL_EVENTS, self.CHANNEL_ALERTS)
                ]
                await pubsub.subscribe(*channels)

                # 监听消息
                async for message in pubsub.listen():
                    if not self._running:
                        break
                    if message["type"] != "message":
                        continue

                    await self._dispatch(message)

                await pubsub.unsubscribe()
                await pubsub.close()

            except asyncio.CancelledError:
                raise
            except Exception as e:
                self.logger.debug(f"Listener error, reconnect in 2s: {e}")
                await asyncio.sleep(2)

    async def _dispatch(self, message: dict):
        """分发消息到订阅者"""
        channel_full = (
            message["channel"].decode("utf-8")
            if isinstance(message["channel"], bytes)
            else message["channel"]
        )
        data_raw = (
            message["data"].decode("utf-8")
            if isinstance(message["data"], bytes)
            else message["data"]
        )

        # 提取短频道名
        channel = channel_full.replace(f"{self._ns}:", "", 1)

        # 解析消息
        try:
            data = json.loads(data_raw) if data_raw else {}
        except json.JSONDecodeError:
            data = {"raw": data_raw}

        # 分发给订阅者
        handlers = self._subscribers.get(channel, [])
        for handler in handlers:
            try:
                await handler(data)
            except Exception as e:
                self.logger.debug(f"Message handler error: {e}")


__all__ = ["ClusterMessenger"]
