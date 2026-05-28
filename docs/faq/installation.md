# 安装问题

## 安装 Crawlo 的最低要求是什么？

- **Python**: 3.10+
- **操作系统**: Windows/Linux/macOS
- **内存**: 最少 512MB
- **磁盘**: 最少 100MB

## 如何安装 Crawlo？

### 基础安装

```bash
pip install crawlo
```

包含核心功能：异步请求、CSS/XPath 选择器、数据管道等。

### 完整安装（推荐）

```bash
pip install crawlo[render]  # 浏览器渲染
playwright install  # 安装浏览器内核

# 或者安装全部依赖
pip install crawlo[all]
```

包含：浏览器渲染、AI 集成等高级功能。

### 开发安装

```bash
git clone https://github.com/crawl-coder/Crawlo.git
cd Crawlo
pip install -e .
```

## 安装失败怎么办？

### 问题 1: pip 版本过旧

**错误信息**：
```
ERROR: Could not find a version that satisfies the requirement crawlo
```

**解决方案**：
```bash
pip install --upgrade pip
pip install crawlo
```

### 问题 2: Python 版本不兼容

**错误信息**：
```
ERROR: Package 'crawlo' requires a different Python: 3.9.x not in '>=3.10'
```

**解决方案**：
升级到 Python 3.10+：
```bash
# 使用 conda
conda create -n crawlo python=3.10
conda activate crawlo
pip install crawlo
```

### 问题 3: 权限不足

**错误信息**：
```
ERROR: Could not install packages due to an EnvironmentError: [Errno 13] Permission denied
```

**解决方案**：
```bash
# 方式1: 使用 --user
pip install --user crawlo

# 方式2: 使用虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
pip install crawlo
```

## Playwright 安装失败怎么办？

### 问题 1: 下载浏览器内核失败

**错误信息**：
```
ERROR: Failed to download browsers
```

**解决方案**：
```bash
# 使用国内镜像
export PLAYWRIGHT_DOWNLOAD_HOST=https://npmmirror.com/mirrors/playwright/
playwright install
```

### 问题 2: Windows 缺少依赖

**错误信息**：
```
ERROR: Missing dependencies
```

**解决方案**：
```bash
# 安装 Windows 依赖
playwright install --with-deps
```

### 问题 3: Linux 缺少系统库

**错误信息**：
```
ERROR: libnss3.so: cannot open shared object file
```

**解决方案**：
```bash
# Ubuntu/Debian
sudo apt-get install -y libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2

# CentOS/RHEL
sudo yum install -y nss atk at-spi2-libs cups-libs libdrm
```

## 如何验证安装是否成功？

运行以下命令：

```bash
# 检查版本
crawlo --version

# 创建测试项目
crawlo startproject test_project
cd test_project
crawlo genspider test example.com

# 运行测试
crawlo run test
```

如果能看到爬虫运行日志，说明安装成功！✅

## Crawlo 可以和其他爬虫框架共存吗？

可以！Crawlo 使用独立的命名空间，不会与 Scrapy 等框架冲突。

```bash
pip install crawlo scrapy  # 可以同时安装
```

## 如何升级 Crawlo？

```bash
# 升级到最新版
pip install --upgrade crawlo

# 升级到指定版本
pip install crawlo==1.6.0
```

## 如何卸载 Crawlo？

```bash
pip uninstall crawlo
```

## 安装后无法导入模块？

**错误信息**：
```
ModuleNotFoundError: No module named 'crawlo'
```

**可能原因**：
1. 安装到了错误的 Python 环境
2. 虚拟环境未激活

**解决方案**：
```bash
# 检查 Python 路径
which python  # Linux/Mac
where python  # Windows

# 检查 crawlo 安装位置
pip show crawlo

# 重新安装
pip install --force-reinstall crawlo
```

## 需要安装可选依赖吗？

可选依赖根据需求安装：

| 依赖 | 功能 | 安装命令 |
|------|------|---------|
| **render** | 浏览器渲染 | `pip install crawlo[render]` |
| **mcp** | AI 集成 | `pip install crawlo[mcp]` |
| **all** | 全部依赖 | `pip install crawlo[all]` |

> 💡 **说明**：Redis、MySQL、MongoDB 等数据库支持已包含在基础安装中，无需额外安装。

## 在 Docker 中使用 Crawlo？

创建 `Dockerfile`：

```dockerfile
FROM python:3.11-slim

RUN pip install crawlo

WORKDIR /app
COPY . /app

CMD ["crawlo", "crawl", "my_spider"]
```

构建和运行：
```bash
docker build -t crawlo-spider .
docker run crawlo-spider
```

---

**还有其他安装问题？** 查看 [一般问题](general.md) 或提交 [GitHub Issue](https://github.com/crawl-coder/Crawlo/issues)。
