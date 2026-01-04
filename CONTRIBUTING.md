# Contributing to Vidurai

**Version:** 2.2.0
**Last Updated:** December 2024

Thank you for your interest in contributing to Vidurai! This document outlines our coding standards and contribution process.

## The Coding Constitution

Vidurai follows strict architectural principles. Please read these carefully before submitting code.

### 1. Lazy Loading is Law

**Never** import heavy modules at the top of a file. All expensive imports (ML models, large libraries) must be deferred.

```python
# BAD - Blocks startup
from sentence_transformers import SentenceTransformer

def get_embeddings():
    model = SentenceTransformer()
    ...

# GOOD - Lazy loaded
def get_embeddings():
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer()
    ...
```

### 2. Path Safety Rule

**Always** use `Path.home() / ".vidurai"` for data storage. Never use `__file__` or relative paths for user data.

```python
# BAD - Breaks when installed as package
DATA_DIR = Path(__file__).parent / "data"

# GOOD - Works everywhere
DATA_DIR = Path.home() / ".vidurai"
```

### 3. PII First Rule

All external data (terminal output, file contents, user input) must pass through the Gatekeeper for PII redaction before storage or transmission.

```python
# from vidurai.core.gatekeeper (removed) import sanitize

# Always sanitize before storing
clean_output = sanitize(terminal_output)
db.store(clean_output)
```

### 4. Explicit Import Rule

Use explicit imports (absolute or relative). Never rely on implicit imports.

```python
# BAD - Implicit
from context_mediator import ContextMediator

# GOOD - Explicit relative
from .context_mediator import ContextMediator

# GOOD - Explicit absolute
from vidurai.daemon.intelligence.context_mediator import ContextMediator
```

### 5. Glass Box Protocol

All operations must be auditable. Every significant action should be logged or recorded in the forgetting ledger.

## Development Setup

```bash
# Clone the repository
git clone https://github.com/chandantochandan/vidurai.git
cd vidurai

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest tests/
```

## Pull Request Process

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **Write tests** for your changes
4. **Ensure** all tests pass (`pytest`)
5. **Update** documentation if needed (README, docstrings)
6. **Submit** a pull request

### PR Checklist

- [ ] Code follows the Coding Constitution
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] No new dependencies without discussion
- [ ] Passes `ruff` linting
- [ ] Passes `black` formatting

## Code Style

We use:
- **Black** for formatting (line length: 88)
- **Ruff** for linting
- **Type hints** for all public functions

```bash
# Format code
black vidurai/

# Lint code
ruff check vidurai/
```

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=vidurai

# Run specific test
pytest tests/test_database.py -v
```

## Architecture Overview

```
vidurai/
├── cli.py              # CLI entry point
├── daemon/             # Background service
│   ├── server.py       # FastAPI + IPC server
│   └── intelligence/   # Context mediation
├── core/               # Business logic
│   ├── gatekeeper.py   # PII redaction
│   ├── retention.py    # Smart forgetting
│   └── oracle.py       # Context generation
└── storage/            # Data layer
    └── database.py     # SQLite operations
```

## Questions?

- Open an issue for bugs or feature requests
- Use Discussions for questions

---

*Vidurai is Infrastructure. Contribute with care.*
