# Dependency Map

This document outlines the explicitly declared dependencies of Vidurai, clarifying their role, location, and import sites to ensure absolute separation between lightweight core and heavyweight AI modules.

## Overview

| Package | Import sites | Core/extra/dev | Final group | Evidence |
|---------|-------------------|------------------|------------------|----------|
| `click` | `vidurai/cli.py` | Core | `dependencies` | Required for CLI |
| `fastapi` | `vidurai/daemon/server.py` | Core | `dependencies` | Required for API |
| `uvicorn` | `vidurai/daemon/__main__.py` | Core | `dependencies` | Required for Daemon |
| `pydantic` | Project-wide models | Core | `dependencies` | Core Data schemas |
| `requests` | Core clients | Core | `dependencies` | Core API usage |
| `prompt_toolkit` | `vidurai/repl.py` | Core | `dependencies` | Repl loop |
| `watchdog` | `vidurai/daemon/smart_file_watcher.py` | Core | `dependencies` | File syncing |
| `loguru` | Project-wide | Core | `dependencies` | Daemon logging |
| `pygments` | `vidurai/repl.py` | Core | `dependencies` | Syntax highlighting |
| `psutil` | `vidurai/cli.py` | Core | `dependencies` | Daemon lifecycle |
| `sqlite-vec` | `vector_brain.py` (lazy) | Extra | `local-embeddings` | Used dynamically |
| `sentence-transformers`| `vector_brain.py` (lazy) | Extra | `local-embeddings`| Used dynamically |
| `torch` | Transitive | Extra | `local-embeddings`| Needed by sentence-transformers |
| `openai` | `gist_extractor.py`, `semantic_compressor_v2.py` | Extra | `ai` | Cloud AI API |
| `tiktoken` | `semantic_compressor_v2.py` | Extra | `ai` | Tokenization |
| `langchain` | `integrations/langchain.py` | Extra | `ai` | Used dynamically |
| `llama-index` | `ingestion`, etc. | Extra | `ai` | Used dynamically |
| `duckdb` | `analytics/engine.py` (lazy) | Extra | `archival` | Used dynamically |
| `pandas` | `analytics/engine.py` | Extra | `archival` | Used dynamically |
| `pyarrow` | Transitive | Extra | `archival` | Used dynamically |
| `ijson` | `ingestion/adapters.py` (lazy) | Extra | `ingestion` | Used dynamically |
| `pytest`, `pytest-cov`, `black`, `ruff`, `build`, `twine`, `pip-tools` | Tests & CI | Dev | `dev` | Dev tasks only |

## Transitive Exceptions
Packages such as `transformers` or `orjson` are implicitly brought in by our explicitly declared dependencies. They are not direct imports in the core path and thus correctly left undeclared in `pyproject.toml`.

## Removed Dependencies
`faiss-cpu` was entirely removed from the requirements as it's no longer used in `vector_brain.py` following the adoption of `sqlite-vec`.
