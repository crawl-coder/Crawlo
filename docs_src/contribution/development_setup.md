# Development Environment Setup

This guide will help you set up a development environment for contributing to the Crawlo framework.

## Prerequisites

Before setting up your development environment, ensure you have the following installed:

- Python 3.10 or higher
- Git
- pip (Python package installer)
- Virtual environment tool (venv or virtualenv)
- Redis (for testing distributed features)
- MySQL or MongoDB (optional, for testing database pipelines)

## Setting Up the Development Environment

### 1. Clone the Repository

First, fork the Crawlo repository on GitHub, then clone your fork:

```bash
git clone https://github.com/your-username/Crawlo.git
cd Crawlo
```

### 2. Create a Virtual Environment

Create and activate a virtual environment:

```bash
# Using venv (Python 3.3+)
python -m venv crawlo-dev
source crawlo-dev/bin/activate  # On Windows: crawlo-dev\Scripts\activate

# Or using virtualenv
virtualenv crawlo-dev
source crawlo-dev/bin/activate  # On Windows: crawlo-dev\Scripts\activate
```

### 3. Install Dependencies

Install Crawlo in development mode along with all dependencies:

```bash
pip install -e ".[dev]"
```

Or install dependencies manually:

```bash
pip install -e .
pip install -r requirements-dev.txt
```

### 4. Install Pre-commit Hooks

Crawlo uses pre-commit hooks to ensure code quality:

```bash
pre-commit install
```

### 5. Set Up Redis (Optional)

For testing distributed features, you'll need Redis:

```bash
# On Ubuntu/Debian
sudo apt install redis-server

# On macOS (using Homebrew)
brew install redis

# On Windows, use WSL or download Redis from the official website
```

Start Redis:

```bash
redis-server
```

## Project Structure

Understanding the project structure is important for development:

```
Crawlo/
├── crawlo/                 # Main source code
│   ├── core/              # Core components (engine, scheduler, etc.)
│   ├── spider/            # Spider base classes
│   ├── network/           # Network components (request, response)
│   ├── downloader/        # Downloaders (aiohttp, httpx, curl-cffi)
│   ├── queue/             # Queue implementations
│   ├── filters/           # Filter implementations
│   ├── middleware/        # Middleware components
│   ├── pipelines/         # Pipeline components
│   ├── extension/         # Extension components
│   ├── settings/          # Configuration system
│   ├── utils/             # Utility functions
│   ├── templates/         # Project templates
│   └── cli.py             # Command-line interface
├── tests/                 # Test suite
├── docs/                  # Documentation
├── examples/              # Example projects
├── requirements.txt       # Runtime dependencies
├── requirements-dev.txt   # Development dependencies
├── setup.py              # Package setup
├── pyproject.toml        # Build system configuration
├── MANIFEST.in           # Package manifest
├── .gitignore            # Git ignore file
├── .pre-commit-config.yaml # Pre-commit configuration
└── README.md             # Project README
```

## Running Tests

### Running the Full Test Suite

```bash
# Run all tests
pytest

# Run tests with coverage
pytest --cov=crawlo

# Run tests in parallel
pytest -n auto
```

### Running Specific Tests

```bash
# Run tests for a specific module
pytest tests/test_engine.py

# Run tests matching a pattern
pytest -k "test_redis"

# Run tests with specific markers
pytest -m "slow"
```

### Test Categories

Crawlo tests are organized into categories:

- **Unit tests**: Test individual components in isolation
- **Integration tests**: Test how components work together
- **Functional tests**: Test complete crawling scenarios
- **Performance tests**: Test performance characteristics

## Code Style and Quality

### Code Formatting

Crawlo uses Black for code formatting:

```bash
# Format all Python files
black .

# Format specific files
black crawlo/core/engine.py
```

### Import Sorting

Crawlo uses isort for import sorting:

```bash
# Sort imports in all Python files
isort .

# Sort imports in specific files
isort crawlo/core/engine.py
```

### Linting

Crawlo uses flake8 for linting:

```bash
# Lint all Python files
flake8 .

# Lint specific files
flake8 crawlo/core/engine.py
```

### Type Checking

Crawlo uses mypy for type checking:

```bash
# Type check all Python files
mypy crawlo

# Type check specific modules
mypy crawlo/core/engine.py
```

## Pre-commit Hooks

Crawlo uses pre-commit hooks to ensure code quality. The hooks automatically run:

- Black (code formatting)
- isort (import sorting)
- flake8 (linting)
- mypy (type checking)

To run all hooks manually:

```bash
pre-commit run --all-files
```

## Documentation Development

### Building Documentation

Crawlo uses MkDocs for documentation:

```bash
# Install documentation dependencies
pip install mkdocs-material

# Serve documentation locally
mkdocs serve

# Build documentation
mkdocs build
```

### Writing Documentation

Documentation should follow these guidelines:

1. Use clear, concise language
2. Include code examples where appropriate
3. Follow the existing documentation structure
4. Update documentation when making code changes
5. Use proper Markdown formatting

## Making Changes

### 1. Create a Branch

Create a new branch for your changes:

```bash
git checkout -b feature/your-feature-name
```

### 2. Make Your Changes

Implement your feature or fix the bug. Remember to:

- Follow the code style guidelines
- Write tests for your changes
- Update documentation if needed
- Run tests to ensure nothing is broken

### 3. Run Tests

Before committing, make sure all tests pass:

```bash
pytest
```

### 4. Commit Your Changes

Commit your changes with a clear, descriptive commit message:

```bash
git add .
git commit -m "Add feature: brief description of your changes"
```

### 5. Push and Create a Pull Request

Push your changes to your fork and create a pull request:

```bash
git push origin feature/your-feature-name
```

## Development Workflow

### 1. Sync with Upstream

Regularly sync your fork with the upstream repository:

```bash
git remote add upstream https://github.com/crawl-coder/Crawlo.git
git fetch upstream
git checkout main
git merge upstream/main
```

### 2. Create Feature Branches

Always create feature branches for your work:

```bash
git checkout -b feature/your-feature-name
```

### 3. Write Tests

For every feature or bug fix, write appropriate tests:

- Unit tests for individual functions
- Integration tests for component interactions
- Functional tests for end-to-end scenarios

### 4. Document Changes

Update or add documentation for your changes:

- Update docstrings in code
- Update relevant documentation files
- Add new documentation for new features

### 5. Follow Code Review Process

- Submit pull requests for review
- Address feedback from reviewers
- Ensure CI checks pass
- Merge after approval

## Debugging Tips

### Using the Python Debugger

You can use pdb to debug Crawlo:

```python
import pdb

def some_function():
    pdb.set_trace()  # Debugger will stop here
    # Your code
```

### Logging for Debugging

Add debug logging to understand code flow:

```python
from crawlo.utils.log import get_logger

logger = get_logger(__name__)

def some_function():
    logger.debug("Entering function")
    # Your code
    logger.debug("Exiting function")
```

### Profiling Code

Use Python's built-in profiling tools:

```python
import cProfile

def profile_function():
    profiler = cProfile.Profile()
    profiler.enable()
    
    # Your code here
    
    profiler.disable()
    profiler.print_stats()
```

## Common Development Tasks

### Adding a New Downloader

1. Create a new downloader class in `crawlo/downloader/`
2. Inherit from the base downloader class
3. Implement the required methods
4. Add tests in `tests/test_downloader/`
5. Update documentation

### Adding a New Pipeline

1. Create a new pipeline class in `crawlo/pipelines/`
2. Inherit from the base pipeline class
3. Implement the required methods
4. Add tests in `tests/test_pipelines/`
5. Update documentation

### Adding a New Middleware

1. Create a new middleware class in `crawlo/middleware/`
2. Inherit from the appropriate base middleware class
3. Implement the required methods
4. Add tests in `tests/test_middleware/`
5. Update documentation

## Getting Help

If you need help with development:

1. Check the existing documentation
2. Look at similar implementations in the codebase
3. Ask questions in GitHub issues
4. Join the community discussion channels

By following this guide, you should be able to set up a productive development environment for contributing to Crawlo.