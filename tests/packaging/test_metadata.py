import pytest
try:
    import tomllib
except ImportError:
    import tomli as tomllib
from pathlib import Path

def test_pyproject_toml_valid():
    path = Path(__file__).parent.parent.parent / "pyproject.toml"
    with open(path, "rb") as f:
        data = tomllib.load(f)
        
    assert "project" in data
    assert "name" in data["project"]
    assert data["project"]["name"] == "vidurai"
    
def test_all_extra_no_self_reference():
    path = Path(__file__).parent.parent.parent / "pyproject.toml"
    with open(path, "rb") as f:
        data = tomllib.load(f)
        
    extras = data.get("project", {}).get("optional-dependencies", {})
    all_extra = extras.get("all", [])
    
    # Must not contain vidurai[ai...]
    for dep in all_extra:
        assert not dep.startswith("vidurai")

def test_heavy_deps_not_in_core():
    path = Path(__file__).parent.parent.parent / "pyproject.toml"
    with open(path, "rb") as f:
        data = tomllib.load(f)
        
    core_deps = data.get("project", {}).get("dependencies", [])
    core_deps_str = " ".join(core_deps).lower()
    
    heavy = ["torch", "transformers", "openai", "sentence-transformers", "llama-index", "langchain", "pandas", "ijson"]
    for h in heavy:
        assert h not in core_deps_str, f"{h} must not be in core dependencies!"
