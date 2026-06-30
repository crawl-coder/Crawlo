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
- `--mode`: 部署模式：standalone（内存模式）、distributed（分布式系统）、auto（多节点协作）。
- `--fresh` 或 `--no-resume`: 忽略检查点，从头开始爬取。
- `--clean-checkpoint`: 清除检查点文件后从头开始。

**检查点相关**:
```bash
crawlo run myspider              # 默认：检查点未启用
crawlo run myspider --fresh      # 忽略检查点，从头开始
crawlo run myspider --clean-checkpoint  # 清除检查点并从头开始
```

> 注意：检查点功能默认关闭，需在 `settings.py` 中设置 `CHECKPOINT_ENABLED = True` 启用。

详细用法请参阅 [检查点持久化](checkpoint-guide.md)。

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

### `crawlo dead-letter`
管理分布式模式下的死信队列。
```bash
crawlo dead-letter list <project> <spider>    # 查看死信列表
crawlo dead-letter retry <project> <spider>  # 重新入队 (--count N)
crawlo dead-letter stats <project> <spider>  # 查看死信统计
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

---

## 5. 交互式终端

### `crawlo shell`
启动交互式终端，用于调试选择器、测试动态渲染和验证逻辑。
```bash
crawlo shell [url]
```

**示例**:
```bash
crawlo shell                       # 启动空 Shell
crawlo shell https://example.com   # 启动并预抓取 URL
crawlo shell --curl 'curl https://api.com -H "Key: val"'  # 使用 curl 命令
crawlo shell --curl "curl https://httpbin.org/post -X POST -d 'key=val'"
```

**curl 转换**:

Shell 支持直接将浏览器的 curl 命令转换为 Request 并执行：

```bash
# 从浏览器 DevTools 复制 curl 命令后执行
crawlo shell --curl 'curl https://api.example.com -H "Authorization: Bearer xxx"'
```

详细用法请参阅 [curl 命令转换](migration/curl-conversion.md) 和 [Shell 交互式终端](shell-guide.md)。
