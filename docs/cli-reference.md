# 命令行工具 (CLI) 参考

Crawlo 提供了一个功能齐全的命令行工具，用于管理项目、运行爬虫和监控状态。

## 1. 项目管理

### `crawlo startproject`
创建新的 Crawlo 项目。
```bash
crawlo startproject <project_name> [directory]
```

### `crawlo genspider`
在当前项目中生成新的爬虫模板。
```bash
crawlo genspider <spider_name> <domain>
```

---

## 2. 爬虫执行

### `crawlo run`
运行指定的爬虫。
```bash
crawlo run <spider_name> [options]
```
**常用选项**:
- `-L, --log-level`: 设置日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)。
- `-s, --set`: 覆盖配置项 (如 `-s CONCURRENCY=10`)。
- `-a, --arg`: 传递爬虫参数 (如 `-a category=news`)。
- `--mode`: 运行模式 (standalone, distributed, auto)。

---

## 3. 信息查询

### `crawlo list`
列出当前项目中的所有爬虫。
```bash
crawlo list
```

### `crawlo check`
检查项目配置及依赖项（如 Playwright, Redis）的连通性。
```bash
crawlo check
```

---

## 4. 状态监控

### `crawlo stats`
查看正在运行或已完成的爬虫统计信息。
```bash
crawlo stats [spider_name]
```

### `crawlo-mcp`
启动 MCP Server，供 Claude/Cursor 调用。
```bash
crawlo-mcp [options]
```
**常用选项**:
- `--host`: 绑定 IP 地址。
- `--port`: 绑定端口。
- `--transport`: 传输协议 (stdio, sse)。
