# 爬虫演进示例

本目录包含从单机爬虫逐步演进到分布式过滤的各个阶段示例代码。

## 目录结构

```
evolution_examples/
├── stage1_standalone.py      # 阶段1：基础单机模式
├── stage3_distributed.py     # 阶段3：分布式模式
├── stage4_optimized.py       # 阶段4：分布式模式优化
└── README.md                # 本说明文件
```

## 各阶段说明

### 阶段1：基础单机模式 (stage1_standalone.py)
- 使用内存队列和内存去重过滤器
- 适合开发测试和小规模数据采集
- 配置简单，无需额外依赖

运行方式：
```bash
python evolution_examples/stage1_standalone.py
```

### 阶段3：分布式模式 (stage3_distributed.py)
- 使用 Redis 队列和去重过滤器
- 支持多节点协同工作
- 需要 Redis 环境支持

运行前请确保 Redis 服务正在运行：
```bash
# 启动 Redis (如果使用 Docker)
docker run -d -p 6379:6379 redis

# 或者启动本地 Redis 服务
redis-server
```

运行方式：
```bash
python evolution_examples/stage3_distributed.py
```

### 阶段4：分布式模式优化 (stage4_optimized.py)
- 配置 Redis 连接池
- 优化去重性能
- 增加监控和故障恢复机制

运行方式：
```bash
python evolution_examples/stage4_optimized.py
```

## 演进过程详细说明

请查看项目根目录的 [DISTRIBUTED_EVOLUTION.md](../DISTRIBUTED_EVOLUTION.md) 文件，其中详细说明了从单机爬虫到分布式过滤的完整演进过程，包括各阶段的复杂性分析和注意事项。