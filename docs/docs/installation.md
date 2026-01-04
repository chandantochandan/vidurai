---
sidebar_position: 2
---

# Installation

Install Vidurai in your project with your preferred package manager.

## Prerequisites

- **Python**: 3.8 or later
- **pip**: Latest version recommended

## Installation Methods

### Using pip (Recommended)
```bash
pip install vidurai
```

### Using pip with virtual environment
```bash
# Create virtual environment
python -m venv venv

# Activate it
source venv/bin/activate  # On Linux/Mac
# OR
venv\Scripts\activate  # On Windows

# Install Vidurai
pip install vidurai
```

### From Source (Development)
```bash
# Clone the repository
git clone https://github.com/chandantochandan/vidurai.git
cd vidurai

# Install in editable mode
pip install -e .
```

## Verify Installation

Create a simple test file to verify the installation:
```python
# test_vidurai.py
from vidurai import Vidurai

# Initialize Vidurai
memory = Vidurai()

print("✅ Vidurai installed successfully!")
print(f"Version: {memory.__version__}")
```

Run it:
```bash
python test_vidurai.py
```

If you see "✅ Vidurai installed successfully!" - you're ready to go!

## Dependencies

Vidurai automatically installs these dependencies:

- **numpy**: Numerical operations
- **sentence-transformers**: Semantic embeddings
- **chromadb**: Vector database
- **pydantic**: Data validation

## Troubleshooting

### Import Error

If you get `ModuleNotFoundError: No module named 'vidurai'`:

1. Verify Python version: `python --version`
2. Check pip installation: `pip list | grep vidurai`
3. Reinstall: `pip install --upgrade --force-reinstall vidurai`

### Permission Errors

On Linux/Mac, if you get permission errors:
```bash
pip install --user vidurai
```

Or use a virtual environment (recommended).

## Next Steps

- [Quick Start Guide](./quickstart) - Build your first memory-enabled agent
- [Configuration](./configuration) - Customize Vidurai for your needs
- [API Reference](./api-reference) - Explore all available methods

---

Need help? Join our [Discord community](https://discord.gg/DHdgS8eA)!