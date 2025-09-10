# Installation Guide

## Prerequisites

Before installing Crawlo, ensure you have the following prerequisites:

- Python 3.10 or higher
- pip (Python package installer)
- Git (for cloning the repository)

## Installation Methods

### Method 1: Install from PyPI (Recommended for Users)

To install Crawlo from PyPI, simply run:

```bash
pip install crawlo
```

### Method 2: Install from Source (Recommended for Developers)

To install Crawlo from source, follow these steps:

1. Clone the repository:
   ```bash
   git clone https://github.com/crawl-coder/Crawlo.git
   cd crawlo
   ```

2. Create a virtual environment (optional but recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install in development mode:
   ```bash
   pip install -e .
   ```

## Verify Installation

To verify that Crawlo is installed correctly, run:

```bash
crawlo --version
```

You should see the version number of Crawlo displayed.

## System Dependencies

Crawlo requires the following system dependencies:

- Redis (for distributed crawling)
- MySQL or MongoDB (for data storage, optional)

### Installing Redis

#### On Ubuntu/Debian:
```bash
sudo apt update
sudo apt install redis-server
```

#### On macOS (using Homebrew):
```bash
brew install redis
```

#### On Windows:
Download Redis from the [official website](https://redis.io/download/) or use [WSL](https://docs.microsoft.com/en-us/windows/wsl/install).

### Installing MySQL

#### On Ubuntu/Debian:
```bash
sudo apt update
sudo apt install mysql-server
```

#### On macOS (using Homebrew):
```bash
brew install mysql
```

#### On Windows:
Download MySQL from the [official website](https://dev.mysql.com/downloads/installer/).

## Next Steps

After installing Crawlo, you can proceed to the [Quick Start Guide](quick_start.md) to create your first project.