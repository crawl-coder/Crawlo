# 安装指南

本指南介绍如何安装 Crawlo 框架及其依赖。

## 📋 系统要求

- **Python**: 3.7+（推荐 3.9+）
- **操作系统**: Windows / macOS / Linux
- **内存**: 至少 512MB（推荐 2GB+）
- **磁盘空间**: 50MB+

---

## 🚀 快速安装

### 方式1: 使用 pip（推荐）

```bash
pip install crawlo
```

### 方式2: 安装最新开发版本

```bash
pip install git+https://github.com/crawl-coder/Crawlo.git
```

### 方式3: 从源码安装

```bash
# 克隆仓库
git clone https://github.com/crawl-coder/Crawlo.git
cd Crawlo

# 安装
pip install -e .
```

---

## 📦 可选依赖

### 浏览器渲染支持

如果你需要抓取动态网页（JavaScript渲染），需要安装渲染依赖：

```bash
pip install crawlo[render]

# 安装 Playwright 浏览器
playwright install
```

> 💡 **说明**：`render` 包含 Playwright 浏览器自动化库。

### MCP Server 支持

如果你需要使用 AI 集成（MCP Server）：

```bash
pip install crawlo[mcp]
```

### 全部依赖

```bash
pip install crawlo[all]
```

> 💡 **注意**：Redis、MySQL、MongoDB 等数据库支持已包含在基础安装中，无需额外安装。

---

## ✅ 验证安装

安装完成后，验证是否成功：

```bash
# 检查版本
crawlo --version

# 创建测试项目
crawlo startproject test_project
cd test_project

# 生成测试爬虫
crawlo genspider test example.com

# 运行爬虫
crawlo run test
```

如果看到爬虫成功运行并输出日志，说明安装成功！

---

## 🔧 常见问题

### 问题1: pip 安装失败

**原因**: Python 版本不兼容或 pip 版本过低

**解决方案**:

```bash
# 升级 pip
pip install --upgrade pip

# 检查 Python 版本
python --version

# 重新安装
pip install crawlo
```

### 问题2: Playwright 安装失败

**原因**: 网络问题或缺少系统依赖

**解决方案**:

```bash
# 使用国内镜像
pip install playwright -i https://pypi.tuna.tsinghua.edu.cn/simple

# 安装浏览器（可能需要科学上网）
playwright install
```

### 问题3: Windows 上的编码问题

**原因**: Windows 控制台编码设置

**解决方案**:

```bash
# 设置 UTF-8 编码
chcp 65001

# 或在 Python 脚本开头添加
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
```

---

## 📚 下一步

- 🚀 [5分钟快速上手](../getting-started/5min-quickstart.md) - 创建你的第一个爬虫
- 📖 [运行模式详解](../guides/configuration/run-modes.md) - 了解三种运行模式
- ❓ [安装问题 FAQ](../faq/installation.md) - 解决安装问题

---

**遇到问题？** 查看 [FAQ](../faq/) 或提交 [GitHub Issue](https://github.com/crawl-coder/Crawlo/issues)
