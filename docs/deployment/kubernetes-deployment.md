# Kubernetes 部署指南

> 规模化部署 Crawlo 分布式爬虫集群：Deployment + 水平伸缩 + 优雅排空。
> 适合多 Worker、需要自动扩缩容或与现有 K8s 体系整合的场景；
> 中小规模优先用 [Docker Compose](docker-deployment.md)。

## 1. 总体架构

```text
┌─────────────────────────────────────────────┐
│ Kubernetes 集群 │
│ │
│ ┌─────────┐ ┌─────────┐ ┌─────────┐ │
│ │ Worker │ │ Worker │ │ Worker │ │ HPA 按队列深度/CPU 扩缩
│ │ (Pod) │ │ (Pod) │ │ (Pod) │ │
│ └────┬────┘ └────┬────┘ └────┬────┘ │
│ └────────────┼────────────┘ │
│ ▼ │
│ ┌────────────────────┐ │
│ │ Redis (外部/托管) │ Sentinel/Cluster
│ └────────────────────┘ │
└─────────────────────────────────────────────┘
```

- **Worker**无状态（队列/指纹/检查点都在 Redis/卷，Pod 可随时替换）；
- **Redis**建议用托管服务（云厂商）或独立部署（见 [Redis HA](redis-ha.md)），
 不要放集群内单点；
- **结果存储**（MySQL/文件）挂 PV 或外部服务。

## 2. 镜像

镜像构建见 [Docker 部署](docker-deployment.md)，打版本 tag：

```bash
docker build -t registry.example.com/crawlo-worker:1.7.3 .
docker push registry.example.com/crawlo-worker:1.7.3
```

## 3. Deployment 清单

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
 name: crawlo-worker
spec:
 replicas: 3
 selector:
 matchLabels:
 app: crawlo-worker
 template:
 metadata:
 labels:
 app: crawlo-worker
 spec:
 terminationGracePeriodSeconds: 60 # 优雅排空在途请求
 containers:
        - name: crawler
 image: registry.example.com/crawlo-worker:1.7.3
 args: ["python", "run.py", "--distributed"]
 env:
            - name: QUEUE_TYPE
 value: "redis_stream"
            - name: REDIS_SENTINEL_URLS
 value: "redis://sentinel-1:26379,redis://sentinel-2:26379"
            - name: REDIS_SENTINEL_SERVICE
 value: "mymaster"
            - name: LOG_LEVEL
 value: "INFO"
 resources:
 requests: { cpu: "500m", memory: "512Mi" }
 limits: { cpu: "2", memory: "2Gi" }
 readinessProbe:
 exec:
 command: ["python", "-c", "import crawlo; print(crawlo.__version__)"]
 initialDelaySeconds: 5
 periodSeconds: 30
 volumeMounts:
            - name: output
 mountPath: /app/output
 volumes:
        - name: output
 persistentVolumeClaim:
 claimName: crawlo-output
```

## 4. 水平伸缩（HPA）

### 4.1 按队列深度（推荐）

用 Prometheus Adapter 暴露 Redis 队列深度，HPA 按队列积压扩缩：

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
 name: crawlo-worker
spec:
 scaleTargetRef:
 apiVersion: apps/v1
 kind: Deployment
 name: crawlo-worker
 minReplicas: 2
 maxReplicas: 20
 metrics:
    - type: Pods
 pods:
 metric:
 name: crawlo_queue_size
 target:
 type: AverageValue
 averageValue: "1000" # 每 Worker 平均队列深度 > 1000 时扩容
```

### 4.2 按 CPU

```yaml
 metrics:
    - type: Resource
 resource:
 name: cpu
 target:
 type: Utilization
 averageUtilization: 70
```

> **注意**：缩容太快会触发 XCLAIM 风暴（大量 pending 重新分配）。
> 建议 `behavior.scaleDown.stabilizationWindowSeconds: 300`。

## 5. 优雅停机与排空

分布式模式 Leader 协调退出，Pod 终止流程：

```yaml
spec:
 terminationGracePeriodSeconds: 60
 # 可选：preStop 通知 Leader 本 Worker 即将退出
 lifecycle:
 preStop:
 exec:
 command: ["python", "-c", "print('draining')"]
```

Worker 优雅退出后，其未 ACK 任务由 `XCLAIM/XAUTOCLAIM` 在
`DISTRIBUTED_IDLE_XCLAIM_MIN_IDLE` 后自动回收，不丢任务。

## 6. 配置管理

settings 用 ConfigMap 管理，环境变量覆盖：

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
 name: crawlo-settings
data:
 CONCURRENCY: "16"
 DOWNLOAD_DELAY: "0.5"
 STATS_BACKEND: prometheus
 PROMETHEUS_METRICS_PORT: "9100"
```

```yaml
 envFrom:
          - configMapRef:
 name: crawlo-settings
```

敏感配置（webhook / DB 密码）用 Secret，勿进 ConfigMap。

## 7. 监控与升级

- **监控**：Pod 暴露 `PROMETHEUS_METRICS_PORT`，ServiceMonitor 采集，
 面板与告警见 [监控与告警](monitoring-alerting.md)；
- **升级**：滚动更新 `kubectl rollout restart deployment/crawlo-worker`，
 配合 [升级与回滚](upgrade-rollback.md) 的兼容性检查；
- **回滚**：`kubectl rollout undo deployment/crawlo-worker`（镜像按版本 tag）。

## 8. 什么时候不要用 K8s

| 场景 | 用 Compose | 用 K8s |
|---|---|---|
| 1-3 个 Worker | ✅ | |
| 需要自动扩缩容 | | ✅ |
| 已有 K8s 集群 | | ✅ |
| 追求最小运维 | ✅ | |
| 任务长期稳定、负载可预测 | ✅ | |
