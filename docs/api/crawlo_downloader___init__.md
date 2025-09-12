# crawlo.downloader.__init__

Crawlo Downloader Module
========================
提供多种高性能异步下载器实现。

下载器类型:
- AioHttpDownloader: 基于aiohttp的高性能下载器
- CurlCffiDownloader: 支持浏览器指纹模拟的curl-cffi下载器  
- HttpXDownloader: 支持HTTP/2的httpx下载器

核心类:
- DownloaderBase: 下载器基类
- ActivateRequestManager: 活跃请求管理器

## 导入的类

- abstractmethod
- ABCMeta
- Final
- Set
- Optional
- asynccontextmanager
- get_logger
- MiddlewareManager

## 类

### ActivateRequestManager
活跃请求管理器 - 跟踪和管理正在处理的请求

#### 方法

##### __init__

##### add
添加活跃请求

##### remove
移除活跃请求并更新统计

##### __len__
返回当前活跃请求数

##### get_stats
获取请求统计信息

##### reset_stats
重置统计信息

### DownloaderMeta

#### 方法

##### __subclasscheck__

### DownloaderBase
下载器基类 - 提供通用的下载器功能和接口

所有下载器实现都应该继承此基类。

#### 方法

##### __init__

##### create_instance
创建下载器实例

##### open
初始化下载器

##### idle
检查是否空闲（无活跃请求）

##### __len__
返回活跃请求数

##### get_stats
获取下载器统计信息

##### reset_stats
重置统计信息

##### health_check
健康检查

## 函数

### get_downloader_class
根据名称获取下载器类
