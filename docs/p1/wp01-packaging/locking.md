# Lockfile Strategy

Vidurai uses standard `pip-tools` (`pip-compile`) to ensure deterministic installations for our core developers, CI runners, and test environments.

## Tooling
- **Tool**: `pip-tools`
- **Command**: `pip-compile`
- **Python Version**: `3.12`

## Regeneration Command

To regenerate the lockfile after modifying dependencies in `pyproject.toml`, run the following in a Python 3.12 environment:

```bash
pip install pip-tools
pip-compile pyproject.toml --extra all --extra dev --output-file requirements-dev.lock
```

## Platform Limitations

This lock captures the verified Python 3.12 contributor environment generated on macOS. CI resolves supported dependencies from `pyproject.toml`; broader lock portability remains unverified.

## Update Policy
- Developers are required to run `pip-compile` and commit the updated `requirements-dev.lock` when modifying `pyproject.toml` dependencies.
- CI relies on this lockfile to install test dependencies identically on PR branches.
