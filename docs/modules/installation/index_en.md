# Installation Guide

This guide provides detailed instructions on how to install and configure the Crawlo framework so you can use it for web crawling development in your local environment.

## System Requirements

The Crawlo framework supports the following operating systems:

- Windows 7 and above
- macOS 10.12 and above
- Linux (Ubuntu 16.04+, CentOS 7+, etc.)

Required Python version:

- Python 3.7 and above

## Installation Methods

### 1. Installing with pip (Recommended)

This is the simplest way to install Crawlo:

```bash
pip install crawlo
```

### 2. Installing a Specific Version from PyPI

```bash
pip install crawlo==1.0.0
```

### 3. Installing from Source

If you need the latest development version, you can clone the source code from GitHub and install it:

```bash
git clone https://github.com/crawl-coder/Crawlo.git
cd crawlo
pip install -r requirements.txt
pip install .
```

### 4. Development Mode Installation

If you plan to develop or modify the Crawlo framework, you can use development mode installation:

```bash
git clone https://github.com/crawl-coder/Crawlo.git
cd crawlo
pip install -r requirements.txt
pip install -e .
```

## Dependencies

The Crawlo framework will automatically install the following dependencies:

- aiohttp - Asynchronous HTTP client
- httpx - Modern HTTP client
- curl-cffi - curl-based HTTP client
- redis - Redis client (for distributed crawling)
- lxml - XML and HTML parsing library
- cssselect - CSS selector support
- pyyaml - YAML configuration file support

## Optional Dependencies

Depending on your specific needs, you may also need to install the following optional dependencies:

### Browser Automation

```bash
# Selenium support
pip install selenium

# Playwright support
pip install playwright
playwright install
```

### Data Storage

```bash
# MySQL support
pip install aiomysql

# PostgreSQL support
pip install asyncpg

# MongoDB support
pip install motor

# Elasticsearch support
pip install elasticsearch
```

### Documentation Building

```bash
# Documentation building tools
pip install mkdocs mkdocs-material
```

## Verifying Installation

After installation, you can verify that the installation was successful in the following ways:

```bash
# Check version
crawlo --version

# View help information
crawlo --help
```

You can also import Crawlo in a Python environment:

```python
import crawlo
print(crawlo.__version__)
```

## Environment Configuration

### Setting up a Python Virtual Environment (Recommended)

To isolate project dependencies, it is recommended to use a Python virtual environment:

```bash
# Create virtual environment
python -m venv crawlo_env

# Activate virtual environment
# Windows:
crawlo_env\Scripts\activate
# macOS/Linux:
source crawlo_env/bin/activate

# Using conda to create and activate environment (Recommended)
conda create -n crawlo python=3.9
conda activate crawlo

# Install Crawlo
pip install crawlo
```

### Configuring Proxy (Optional)

If you need to use a proxy server, you can set environment variables:

```bash
# Windows (PowerShell)
$env:HTTP_PROXY="http://proxy.example.com:8080"
$env:HTTPS_PROXY="https://proxy.example.com:8080"

# macOS/Linux
export HTTP_PROXY=http://proxy.example.com:8080
export HTTPS_PROXY=https://proxy.example.com:8080
```

## Common Issues

### 1. Permission Errors During Installation

If you encounter permission errors during installation, you can try the following solutions:

```bash
# Install to user directory with --user parameter
pip install --user crawlo

# Or use virtual environment (recommended)
python -m venv crawlo_env
crawlo_env\Scripts\activate
pip install crawlo

# Or use conda environment (recommended)
conda create -n crawlo python=3.9
conda activate crawlo
pip install crawlo
```

### 2. Dependency Installation Failures

If some dependencies fail to install, you can try:

```bash
# Upgrade pip
pip install --upgrade pip

# Install failed dependencies separately
pip install <package_name>
```

### 3. Python Version Incompatibility

Make sure you are using Python 3.7 or higher:

```bash
python --version
```

## Upgrading Crawlo

To upgrade to the latest version of Crawlo:

```bash
pip install --upgrade crawlo
```

To upgrade to a specific version:

```bash
pip install --upgrade crawlo==1.0.0
```

## Uninstalling Crawlo

To uninstall Crawlo:

```bash
pip uninstall crawlo
```

## Next Steps

- Read the [Quick Start](../quickstart/index_en.md) guide to create your first project
- Learn about Crawlo's [Core Concepts](../architecture/index_en.md)
- Explore the [Configuration System](../configuration/index_en.md)