# 调度模式日志分流问题分析与解决方案

## 问题描述
在执行 `python run.py --schedule` 运行调度模式时，会出现日志分流现象：
1. 调度任务的 **开始** 和 **结束** 日志正确写入了项目配置的日志文件（例如 `logs/ofweek_standalone.log`）。
2. 调度任务 **中间执行过程**（即爬虫运行期间）的日志被写入了框架默认的日志文件（`logs/crawlo.log`）。

## 原因分析
经过代码排查，问题根源在于 `SchedulerDaemon` 启动爬虫任务时，`CrawlerProcess` 的实例化方式导致了日志配置被重置。

具体流程如下：
1. **调度器启动**：`SchedulerDaemon` 初始化，获取了正确的 Logger 实例（持有指向 `ofweek_standalone.log` 的 Handler）。
2. **任务开始**：`SchedulerDaemon._run_spider_job` 方法被调用。
3. **日志重置（第一次，正确）**：代码调用 `configure_logging(job_args)` 将全局日志配置设置为项目的正确配置。
4. **日志重置（第二次，错误）**：
   - 代码执行 `process = CrawlerProcess()`，**未传递 settings 参数**。
   - `CrawlerProcess.__init__` 检查发现 `settings` 为空，于是调用 `initialize_framework()`。
   - `initialize_framework()` 重新运行初始化流程，其中包括 `LoggingInitializer`。
   - 由于缺乏上下文，`LoggingInitializer` 加载了默认配置（即 `crawlo.log`），覆盖了刚刚设置好的全局配置。
5. **爬虫运行**：爬虫组件在运行时获取 Logger。由于 `LoggerFactory` 缓存已被清空，它基于当前的全局配置（此时已变回默认值）创建新 Logger，导致日志写入 `crawlo.log`。
6. **任务结束**：`SchedulerDaemon` 使用它一直持有的旧 Logger 实例记录结束信息，因此这条日志依然被写入正确的 `ofweek_standalone.log`。

## 解决方案

修改 `crawlo/scheduling/scheduler_daemon.py` 文件中的 `_run_spider_job` 方法，在实例化 `CrawlerProcess` 时明确传入配置对象，避免框架重新初始化。

### 修改前
```python
# crawlo/scheduling/scheduler_daemon.py:317
process = CrawlerProcess()
```

### 修改后
需要构造一个包含当前配置的 `SettingManager` 对象（或字典）传给 `CrawlerProcess`。建议使用当前 `job_args` 构造配置，或者直接复用 `self.settings`。

```python
# crawlo/scheduling/scheduler_daemon.py

# ... (前文代码保持不变)

# 311行: configure_logging(job_args)  <-- 这里配置了正确的日志

# 构造配置对象，避免 CrawlerProcess 重新初始化框架
from crawlo.settings.setting_manager import SettingManager
spider_settings = SettingManager()
spider_settings.update_attributes(job_args)

# 实例化 CrawlerProcess 时传入配置
process = CrawlerProcess(settings=spider_settings)

# ... (后续代码保持不变)
```

通过传入 `settings` 参数，`CrawlerProcess` 将直接使用该配置，而不会触发 `initialize_framework()`，从而保留了正确的全局日志配置。
