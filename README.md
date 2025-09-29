<!-- markdownlint-disable MD033 MD041 -->
<div align="center">
  <h1 align="center">Crawlo</h1>
  <p align="center">异步分布式爬虫框架</p>
  <p align="center"><strong>基于 asyncio 的高性能异步分布式爬虫框架，支持单机和分布式部署</strong></p>
  
  <p align="center">
    <a href="https://www.python.org/downloads/">
      <img src="https://img.shields.io/badge/python-%3C%3D3.12-blue" alt="Python Version">
    </a>
    <a href="LICENSE">
      <img src="https://img.shields.io/badge/license-MIT-green" alt="License">
    </a>
    <a href="https://crawlo.readthedocs.io/">
      <img src="https://img.shields.io/badge/docs-latest-brightgreen" alt="Documentation">
    </a>
    <a href="https://github.com/crawlo/crawlo/actions">
      <img src="https://github.com/crawlo/crawlo/workflows/CI/badge.svg" alt="CI Status">
    </a>
  </p>
  
  <p align="center">
    <a href="#-特性">特性</a> •
    <a href="#-快速开始">快速开始</a> •
    <a href="#-命令行工具">命令行工具</a> •
    <a href="#-示例项目">示例项目</a>
  </p>
</div>

<br />

```
# Crawlo 爬虫框架

Crawlo 是一个高性能、可扩展的 Python 爬虫框架，支持单机和分布式部署。

## 特性

- 高性能异步爬取
- 支持多种下载器 (aiohttp, httpx, curl-cffi)
- 内置数据清洗和验证
- 分布式爬取支持
- 灵活的中间件系统
- 强大的配置管理系统
- 详细的日志记录和监控
- Windows 和 Linux 兼容

## 安装

```bash
pip install crawlo
```

或者从源码安装：

```bash
git clone https://github.com/your-username/crawlo.git
cd crawlo
pip install -r requirements.txt
pip install .
```

## 快速开始

```python
from crawlo import Spider

class MySpider(Spider):
    name = 'example'
    
    def parse(self, response):
        # 解析逻辑
        pass

# 运行爬虫
# crawlo run example
```

## Windows 兼容性说明

在 Windows 系统上使用日志轮转功能时，可能会遇到文件锁定问题。为了解决这个问题，建议安装 `concurrent-log-handler` 库：

```bash
pip install concurrent-log-handler
```

Crawlo 框架会自动检测并使用这个库来提供更好的 Windows 兼容性。

如果未安装 `concurrent-log-handler`，在 Windows 上运行时可能会出现以下错误：
```
PermissionError: [WinError 32] 另一个程序正在使用此文件，进程无法访问。
```

## 文档

请查看 [文档](https://your-docs-url.com) 获取更多信息。

## 许可证

MIT
