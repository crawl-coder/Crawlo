# crawlo 框架中间件优先级分配策略

## 1. 优先级数值范围和含义

在crawlo框架中，优先级数值越大，中间件执行越早：

- **高优先级 (80-100)**：请求预处理阶段，如过滤、验证等
- **中高优先级 (60-79)**：请求处理阶段，如添加请求头、代理设置等
- **中等优先级 (40-59)**：响应处理阶段，如重试、状态码处理等
- **低优先级 (0-39)**：响应后处理阶段，如过滤、记录等

## 2. 默认中间件优先级分配

根据 default_settings.py 中的配置，中间件优先级分配如下：

```python
# === 请求预处理阶段 ===
'crawlo.middleware.request_ignore.RequestIgnoreMiddleware': 100  # 1. 忽略无效请求（最高优先级）
'crawlo.middleware.download_delay.DownloadDelayMiddleware': 90   # 2. 控制请求频率
'crawlo.middleware.default_header.DefaultHeaderMiddleware': 80   # 3. 添加默认请求头
'crawlo.middleware.offsite.OffsiteMiddleware': 60               # 5. 站外请求过滤

# === 响应处理阶段 ===
'crawlo.middleware.retry.RetryMiddleware': 50                   # 6. 失败请求重试
'crawlo.middleware.response_code.ResponseCodeMiddleware': 40     # 7. 处理特殊状态码
'crawlo.middleware.response_filter.ResponseFilterMiddleware': 30  # 8. 响应内容过滤（最低优先级）
```

## 3. 用户自定义中间件优先级建议

### A. 请求处理类中间件
- **添加请求头/代理**：优先级 75-85（在默认请求头中间件之后，但早于其他处理）
- **请求过滤/验证**：优先级 85-95（在大部分中间件之前）
- **请求修改/增强**：优先级 60-75（在请求发送前处理）

### B. 响应处理类中间件
- **响应重试/恢复**：优先级 45-55（在默认重试中间件附近）
- **响应验证/解析**：优先级 30-40（在响应过滤之前）
- **响应后处理**：优先级 10-25（在最末尾处理）

### C. 特殊处理类中间件
- **安全/认证中间件**：优先级 90+（在请求早期处理）
- **日志/监控中间件**：优先级 20-40（在响应处理的后期）

## 4. 优先级设置原则

1. **请求处理优先于响应处理**：请求相关中间件优先级通常高于响应处理中间件
2. **过滤器通常优先级较高**：过滤无效请求的中间件应具有较高优先级
3. **依赖关系**：如果中间件A的输出是中间件B的输入，A的优先级应高于B
4. **性能考虑**：可能快速过滤请求的中间件应具有较高优先级

## 5. 实际示例

```python
# 用户自定义中间件示例
MIDDLEWARES = {
    # 自定义请求过滤器 - 高优先级
    'myproject.middlewares.CustomRequestFilter': 95,
    
    # 自定义请求头中间件 - 中高优先级
    'myproject.middlewares.CustomHeaderMiddleware': 82,  # 在默认头中间件之后
    
    # 自定义代理中间件 - 中高优先级
    'myproject.middlewares.CustomProxyMiddleware': 75,
    
    # 自定义重试中间件 - 中等优先级
    'myproject.middlewares.CustomRetryMiddleware': 52,   # 在默认重试中间件之后
    
    # 自定义响应过滤器 - 低优先级
    'myproject.middlewares.CustomResponseFilter': 25,
}
```

## 6. 推荐的优先级分配策略

- **100**：最紧急的请求过滤（如黑名单过滤）
- **90-99**：请求预处理（如认证、限流）
- **80-89**：请求增强（如添加头、代理）
- **60-79**：请求后处理
- **50-59**：响应预处理
- **40-49**：响应处理（如重试）
- **30-39**：响应后处理
- **0-29**：日志记录、监控等

## 7. 注意事项

- OffsiteMiddleware 只有在配置了 ALLOWED_DOMAINS 时才会启用，否则会因 NotConfiguredError 而被禁用
- 优先级数字越大，执行越早
- 用户配置会覆盖默认配置中的相同中间件优先级
- 中间件按优先级从高到低排序执行
