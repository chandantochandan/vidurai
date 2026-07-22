# WP-01 Implementation Report: Packaging and Dependency Separation

## Objective
Convert Vidurai into a standard, reproducibly installable Python package while explicitly decoupling the lightweight daemon core from heavyweight AI frameworks.

## State 
**COMPLETE**

## Changes Made
- Modernized packaging by introducing `pyproject.toml`, deprecating the `setup.py` format.
- Moved heavy AI models (`openai`, `sentence-transformers`, `torch`, `langchain`, `llama-index`, `pandas`, `duckdb`) out of core dependencies and into `[project.optional-dependencies]`.
- Retained a legacy `requirements.txt` proxy for `-e .[all]` to preserve CI compatibility without misleading new users.
- Added strict explicit `ImportError` guards to optional subsystems (`vismriti_memory.py`, `gist_extractor.py`, `semantic_compressor_v2.py`, `vector_brain.py`, `cli.py` ingestion) to degrade gracefully and suggest appropriate install commands if features are accessed missing their deps.
- Fixed a known WP-00 bug where `vidurai ingest` raised a crash `NameError` due to undefined variables when dependencies were missing.
- Refactored `[all]` extra to be a true explicit union of optional packages, avoiding self-referential resolver bugs.
- Generated `requirements-dev.lock` for deterministic Python 3.12 CI.
- Stripped generated packaging items like `*.egg-info` from git tracking.

## Limitations
- Only Python 3.12 is fully supported at this time due to testing constraints.
- The `requirements-dev.lock` file is strictly tested against a single platform/Python version (macOS/Python 3.12), so cross-platform lock universality is not guaranteed.
- Further work on Cross-platform distribution (like Homebrew, single-binaries) is deferred to future work packages.
