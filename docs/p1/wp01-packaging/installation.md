# Vidurai Installation Guide

Vidurai is designed as a modular, local-first AI memory layer. To maintain system performance and stability, we decoupled heavy AI frameworks from our lightweight core daemon.

## Standard Installation (Recommended)

Normal users should install the lightweight core package. This installs the minimal dependencies needed for Vidurai to provide API, IPC, and SQLite persistence.

```bash
pip install vidurai
```

### Installing via pipx

If you intend to run Vidurai globally on your machine without polluting global Python packages, you can install via `pipx`:

```bash
pipx install vidurai
```

## Optional Features

Vidurai's advanced functionalities require optional AI dependencies. You can install these on top of the base package:

- **AI (`ai`)**: Includes OpenAI API clients, LangChain, LlamaIndex, and tokenizers for semantic compression.
  ```bash
  pip install "vidurai[ai]"
  ```
- **Local Embeddings (`local-embeddings`)**: Installs SentenceTransformers and sqlite-vec for privacy-preserving local vector search.
  ```bash
  pip install "vidurai[local-embeddings]"
  ```
- **Ingestion (`ingestion`)**: Installs fast JSON parsing dependencies (ijson) for ingesting bulk chat exports.
  ```bash
  pip install "vidurai[ingestion]"
  ```
- **Archival (`archival`)**: Installs data manipulation tools like Pandas and DuckDB for archiving.
  ```bash
  pip install "vidurai[archival]"
  ```

## Legacy / Full-Feature Installation

If you are maintaining a legacy script or simply want the complete kitchen sink of Vidurai features:

```bash
pip install "vidurai[all]"
```
**Note**: The root `requirements.txt` is retained as a legacy full-feature/all-optional-runtime installation for backward-compatible development workflows. Running `pip install -r requirements.txt` installs `-e .[all]`.

## Contributor Setup

Contributors should use the `dev` extra for a complete development environment including test suites, linting, and formatting tools:

```bash
pip install -e ".[all]"
```

## Supported Python Versions

- ✅ Python 3.12

**Unsupported Python Versions**:
- ❌ Python <=3.11 (Currently unverified)
- ❌ Python 3.13 (Currently unverified)
- ❌ Python 3.14 (Unsupported)

## Upgrade Expectations

Upgrading Vidurai via `pip install --upgrade vidurai` will safely preserve your local SQLite memory and event contracts. The schema is immutable across minor WP-01 upgrades. No automatic user-data deletion happens.

## Uninstall Behavior

Uninstalling Vidurai will correctly remove the Python binaries and package metadata. It will **not** automatically purge your local user memory or daemon configuration stored in `~/.vidurai/`.
