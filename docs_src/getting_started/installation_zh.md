# 安装指南

## 先决条件

在安装 Crawlo 之前，请确保您具备以下先决条件：

- Python 3.10 或更高版本
- pip（Python 包安装程序）
- Git（用于克隆仓库）

## 安装方法

### 方法 1：从 PyPI 安装（推荐给用户）

要从 PyPI 安装 Crawlo，只需运行：

```bash
pip install crawlo
```

### 方法 2：从源码安装（推荐给开发者）

要从源码安装 Crawlo，请按照以下步骤操作：

1. 克隆仓库：
   ```bash
   git clone https://github.com/crawl-coder/Crawlo.git
   cd crawlo
   ```

2. 创建虚拟环境（可选但推荐）：
   ```bash
   python -m venv venv
   source venv/bin/activate  # 在 Windows 上：venv\Scripts\activate
   ```

3. 以开发模式安装：
   ```bash
   pip install -e .
   ```

## 验证安装

要验证 Crawlo 是否正确安装，请运行：

```bash
crawlo --version
```

您应该会看到显示的 Crawlo 版本号。

## 系统依赖

Crawlo 需要以下系统依赖：

- Redis（用于分布式爬取）
- MySQL 或 MongoDB（用于数据存储，可选）

### 安装 Redis

#### 在 Ubuntu/Debian 上：
```bash
sudo apt update
sudo apt install redis-server
```

#### 在 macOS 上（使用 Homebrew）：
```bash
brew install redis
```

#### 在 Windows 上：
从[官方网站](https://redis.io/download/)下载 Redis 或使用 [WSL](https://docs.microsoft.com/en-us/windows/wsl/install)。

### 安装 MySQL

#### 在 Ubuntu/Debian 上：
```bash
sudo apt update
sudo apt install mysql-server
```

#### 在 macOS 上（使用 Homebrew）：
```bash
brew install mysql
```

#### 在 Windows 上：
从[官方网站](https://dev.mysql.com/downloads/installer/)下载 MySQL。

## 下一步

安装 Crawlo 后，您可以继续阅读[快速入门指南](quick_start_zh.md)来创建您的第一个项目。