# Dependency & Import Audit

## Current Dependency Manifests
- `requirements.txt`: Monolithic file containing core logic, web servers, testing tools, and heavy ML frameworks (Torch, Transformers, Sentence-Transformers, Langchain).
- `pyproject.toml`: Monolithic `dependencies` array under `[project]` which also blindly specifies `sentence-transformers>=2.2.0` ensuring massive ML payloads are downloaded for all users.

## Packages Required by Core Imports
- `pydantic`, `watchdog`, `loguru`, `pandas`, `click`, `pyarrow`, `sqlite-vec`, `duckdb`, `psutil`, `prompt_toolkit`, `requests`, `fastapi`, `uvicorn`.

## Heavy AI Packages
- `torch`, `sentence-transformers`, `transformers`, `huggingface-hub`, `langchain`, `llama-index`, `faiss-cpu`.

## Undeclared / Inconsistently Declared Packages
- `fastapi` and `uvicorn` are required by `vidurai.daemon.server` but omitted from `pyproject.toml` dependencies, causing `vidurai start` or `vidurai server` to instantly crash if installed via `pip install .` without `requirements.txt`.
- `click` is listed in `pyproject.toml` but completely missing from `requirements.txt`.

## Import Chains Triggering AI Dependencies
- `vidurai.daemon.server` imports `vidurai.vismriti_memory`
- `vidurai.vismriti_memory` imports `vidurai.core.intelligence.vector_brain`
- `vidurai.core.intelligence.vector_brain` imports `sentence_transformers.SentenceTransformer`
- This chain forces heavy AI dependencies to load eagerly on daemon startup.

## Python Baseline Result
- Tested in Python 3.12.13. Works successfully when dependencies are resolved.

## Known Python 3.14 Incompatibility
- asyncio and stdlib changes in Python 3.14 cause unverified behaviors. Excluded from P1 baseline.
