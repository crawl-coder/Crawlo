#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""crawlo-mcp 客户端示例。

用法:
    python client_example.py

依赖:
    pip install "crawlo[mcp]"
"""

import asyncio
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main() -> int:
    # 使用当前 Python 解释器启动服务器，避免 PATH 中的旧入口指向其他环境
    params = StdioServerParameters(command=sys.executable, args=["-m", "crawlo.mcp.server"])

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # 1. 列出工具
            tools = await session.list_tools()
            print("可用工具:", [t.name for t in tools.tools])
            print()

            # 2. 抓取 example.com（basic 模式，markdown 输出，限制长度）
            result = await session.call_tool(
                "fetch",
                {
                    "url": "https://example.com",
                    "mode": "basic",
                    "format": "markdown",
                    "max_length": 500,
                },
            )
            print("=== fetch 结果 ===")
            for block in result.content:
                print(getattr(block, "text", str(block))[:600])
            print()

            # 3. 服务器状态
            status = await session.call_tool("status", {})
            print("=== status 结果 ===")
            for block in status.content:
                print(getattr(block, "text", str(block))[:300])

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
