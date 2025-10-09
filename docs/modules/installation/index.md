# �安装指南

本指南将详细介绍如何安装和配置 Crawlo 框架，以便您可以在本地环境中使用它进行网络爬虫开发。

## 系统要求

Crawlo 框架支持以下操作系统：

- Windows 7 及以上版本
- macOS 10.12 及以上版本
- Linux (Ubuntu 16.04+, CentOS 7+, 等)

需要的 Python 版本：

- Python 3.7 及以上版本

## 安装方式

### 1. 使用 pip 安装（推荐）

这是安装 Crawlo 最简单的方式：

```bash
pip install crawlo
```

### 2. 从 PyPI 安装特定版本

```bash
pip install crawlo==1.0.0
```

### 3. 从源码安装

如果您需要最新的开发版本，可以从 GitHub 克隆源码并安装：

```bash
git clone https://github.com/crawl-coder/Crawlo.git
cd crawlo
pip install -r requirements.txt
pip install .
```

### 4. 开发模式安装

如果您计划对 Crawlo 框架进行开发或修改，可以使用开发模式安装：

```bash
git clone https://github.com/crawl-coder/Crawlo.git
cd crawlo
pip install -r requirements.txt
pip install -e .
```

## 依赖项

Crawlo 框架会自动安装以下依赖项：

- aiohttp - 异步 HTTP 客户端
- httpx - 现代化的 HTTP 客户端
- curl-cffi - 基于 curl 的 HTTP 客户端
- redis - Redis 客户端（用于分布式爬取）
- lxml - XML 和 HTML 解析库
- cssselect - CSS 选择器支持
- pyyaml - YAML 配置文件支持

## 可选依赖项

根据您的具体需求，您可能还需要安装以下可选依赖项：

### 浏览器自动化

```bash
# Selenium 支持
pip install selenium

# Playwright 支持
pip install playwright
playwright install
```

### 数据存储

```bash
# MySQL 支持
pip install aiomysql

# PostgreSQL 支持
pip install asyncpg

# MongoDB 支持
pip install motor

# Elasticsearch 支持
pip install elasticsearch
```

### 文档构建

```bash
# 文档构建工具
pip install mkdocs mkdocs-material
```

## 验证安装

安装完成后，您可以通过以下方式验证安装是否成功：

```bash
# 检查版本
crawlo --version

# 查看帮助信息
crawlo --help
```

您也可以在 Python 环境中导入 Crawlo：

```python
import crawlo
print(crawlo.__version__)
```

## 配置环境

### 设置 Python 虚拟环境（推荐）

为了隔离项目依赖，建议使用 Python 虚拟环境：

```bash
# 创建虚拟环境
python -m venv crawlo_env

# 激活虚拟环境
# Windows:
crawlo_env\Scripts\activate
# macOS/Linux:
source crawlo_env/bin/activate

# 使用 conda 创建和激活环境（推荐）
conda create -n crawlo python=3.9
conda activate crawlo

# 安装 Crawlo
pip install crawlo
```

### 配置代理（可选）

如果您需要使用代理服务器，可以设置环境变量：

```bash
# Windows (PowerShell)
$env:HTTP_PROXY="http://proxy.example.com:8080"
$env:HTTPS_PROXY="https://proxy.example.com:8080"

# macOS/Linux
export HTTP_PROXY=http://proxy.example.com:8080
export HTTPS_PROXY=https://proxy.example.com:8080
```

## 常见问题

### 1. 安装过程中出现权限错误

如果您在安装过程中遇到权限错误，可以尝试以下解决方案：

```bash
# 使用 --user 参数安装到用户目录
pip install --user crawlo

# 或者使用虚拟环境（推荐）
python -m venv crawlo_env
crawlo_env\Scripts\activate
pip install crawlo

# 或者使用 conda 环境（推荐）
conda create -n crawlo python=3.9
conda activate crawlo
pip install crawlo
```

### 2. 依赖项安装失败

如果某些依赖项安装失败，可以尝试：

```bash
# 升级 pip
pip install --upgrade pip

# 单独安装失败的依赖项
pip install <package_name>
```

### 3. Python 版本不兼容

确保您使用的是 Python 3.7 或更高版本：

```bash
python --version
```

## 升级 Crawlo

要升级到最新版本的 Crawlo：

```bash
pip install --upgrade crawlo
```

要升级到特定版本：

```bash
pip install --upgrade crawlo==1.0.0
```

## 卸载 Crawlo

要卸载 Crawlo：

```bash
pip uninstall crawlo
```

## 下一步

- 阅读[快速开始](../quickstart/index.md)指南创建您的第一个项目
- 了解 Crawlo 的[核心概念](../architecture/index.md)
- 探索[配置系统](../configuration/index.md)