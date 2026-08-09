# MCP 快速上手示例

本目录演示如何通过 MCP 协议调用 Crawlo 的抓取能力。

## 前置条件

```bash
pip install "crawlo[mcp]"
```

## 1. 手动验证服务器

```bash
crawlo-mcp
```

正常启动后无输出（stdio 模式等待客户端连接）。Ctrl+C 退出。

## 2. 运行客户端示例

```bash
python client_example.py
```

脚本会：

1. 拉起 `crawlo-mcp` 子进程并建立 MCP 会话；
2. 列出服务器暴露的工具；
3. 用 `fetch`（basic 模式）抓取 example.com 并打印摘要；
4. 调用 `status` 查看服务器状态。

## 3. 接入 Claude / Cursor

在 MCP 客户端配置中注册：

```json
{
  "mcpServers": {
    "crawlo": {
      "command": "crawlo-mcp",
      "args": []
    }
  }
}
```

详细说明见 [MCP 集成指南](../../docs/guides/mcp-guide.md)。
