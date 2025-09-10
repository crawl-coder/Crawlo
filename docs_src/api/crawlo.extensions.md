# crawlo.extensions

扩展组件模块为 Crawlo 框架提供了额外的功能。

## 内置扩展

### LogIntervalExtension

定时日志扩展，定期输出爬虫的运行统计信息。

#### 类定义

```python
class LogIntervalExtension(object)
```

#### 方法

##### `__init__(self, crawler)`
初始化扩展实例。

**参数:**
- `crawler`: 爬虫实例

##### `create_instance(cls, crawler)`
创建扩展实例的工厂方法。

**参数:**
- `crawler`: 爬虫实例

**返回:**
- `LogIntervalExtension`: 扩展实例

##### `spider_opened(self)`
爬虫启动时调用的方法。

##### `spider_closed(self)`
爬虫关闭时调用的方法。

##### `interval_log(self)`
定时输出日志信息的异步方法。

### LogStats

统计信息扩展，收集和记录爬虫运行过程中的各种统计数据。

#### 类定义

```python
class LogStats(object)
```

#### 方法

##### `__init__(self, stats)`
初始化扩展实例。

**参数:**
- `stats`: 统计信息收集器

##### `create_instance(cls, crawler)`
创建扩展实例的工厂方法。

**参数:**
- `crawler`: 爬虫实例

**返回:**
- `LogStats`: 扩展实例

##### `spider_opened(self)`
爬虫启动时调用的方法。

##### `spider_closed(self)`
爬虫关闭时调用的方法。

##### `item_successful(self, _item, _spider)`
处理成功处理的项目。

##### `item_discard(self, _item, exc, _spider)`
处理被丢弃的项目。

##### `response_received(self, _response, _spider)`
处理接收到的响应。

##### `request_scheduled(self, _request, _spider)`
处理调度的请求。

### CustomLoggerExtension

自定义日志扩展，初始化和配置日志系统。

#### 类定义

```python
class CustomLoggerExtension
```

#### 方法

##### `__init__(self, settings)`
初始化扩展实例。

**参数:**
- `settings`: 配置设置

##### `create_instance(cls, crawler, *args, **kwargs)`
创建扩展实例的工厂方法。

**参数:**
- `crawler`: 爬虫实例
- `*args`: 位置参数
- `**kwargs`: 关键字参数

**返回:**
- `CustomLoggerExtension`: 扩展实例

##### `spider_opened(self, spider)`
爬虫启动时调用的方法。

## 可选扩展

### MemoryMonitorExtension

内存监控扩展，监控爬虫进程的内存使用情况。

#### 类定义

```python
class MemoryMonitorExtension
```

#### 方法

##### `__init__(self, crawler)`
初始化扩展实例。

**参数:**
- `crawler`: 爬虫实例

##### `create_instance(cls, crawler)`
创建扩展实例的工厂方法。

**参数:**
- `crawler`: 爬虫实例

**返回:**
- `MemoryMonitorExtension`: 扩展实例

##### `spider_opened(self)`
爬虫启动时调用的方法。

##### `spider_closed(self)`
爬虫关闭时调用的方法。

##### `_monitor_loop(self)`
内存监控循环的异步方法。

### RequestRecorderExtension

请求记录扩展，记录所有发送的请求和接收到的响应信息。

#### 类定义

```python
class RequestRecorderExtension
```

#### 方法

##### `__init__(self, crawler)`
初始化扩展实例。

**参数:**
- `crawler`: 爬虫实例

##### `create_instance(cls, crawler)`
创建扩展实例的工厂方法。

**参数:**
- `crawler`: 爬虫实例

**返回:**
- `RequestRecorderExtension`: 扩展实例

##### `request_scheduled(self, request, spider)`
记录调度的请求。

##### `response_received(self, response, spider)`
记录接收到的响应。

##### `spider_closed(self, spider)`
爬虫关闭时调用的方法。

##### `_write_record(self, record)`
写入记录到文件的异步方法。

### PerformanceProfilerExtension

性能分析扩展，在爬虫运行期间进行性能分析。

#### 类定义

```python
class PerformanceProfilerExtension
```

#### 方法

##### `__init__(self, crawler)`
初始化扩展实例。

**参数:**
- `crawler`: 爬虫实例

##### `create_instance(cls, crawler)`
创建扩展实例的工厂方法。

**参数:**
- `crawler`: 爬虫实例

**返回:**
- `PerformanceProfilerExtension`: 扩展实例

##### `spider_opened(self)`
爬虫启动时调用的方法。

##### `spider_closed(self)`
爬虫关闭时调用的方法。

##### `_periodic_save(self)`
定期保存分析结果的异步方法。

##### `_save_profile(self, name)`
保存分析结果到文件的异步方法。

### HealthCheckExtension

健康检查扩展，监控爬虫的健康状态。

#### 类定义

```python
class HealthCheckExtension
```

#### 方法

##### `__init__(self, crawler)`
初始化扩展实例。

**参数:**
- `crawler`: 爬虫实例

##### `create_instance(cls, crawler)`
创建扩展实例的工厂方法。

**参数:**
- `crawler`: 爬虫实例

**返回:**
- `HealthCheckExtension`: 扩展实例

##### `spider_opened(self)`
爬虫启动时调用的方法。

##### `spider_closed(self)`
爬虫关闭时调用的方法。

##### `request_scheduled(self, request, spider)`
记录调度的请求。

##### `response_received(self, response, spider)`
记录接收到的响应。

##### `_health_check_loop(self)`
健康检查循环的异步方法。

##### `_check_health(self)`
执行健康检查并输出报告的异步方法。