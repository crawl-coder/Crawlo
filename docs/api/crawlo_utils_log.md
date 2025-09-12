# crawlo.utils.log

日志管理器：安全版本，使用字符串化 key 避免 unhashable 问题

## 导入的类

- Formatter
- StreamHandler
- FileHandler
- Logger
- DEBUG
- INFO
- WARNING
- ERROR
- CRITICAL

## 类

### LoggerManager

#### 方法

##### _to_level
安全转换为日志级别 int

##### configure
使用 settings 对象或关键字参数配置日志

##### get_logger
简化接口，只暴露必要参数
