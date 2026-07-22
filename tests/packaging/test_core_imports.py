import pytest
import sys
import importlib
from unittest.mock import patch
from click.testing import CliRunner

def test_core_imports_work_without_ai():
    """Verify that importing core modules does not trigger AI optional dependencies."""
    
    # We mock missing optional dependencies
    # If the core modules try to import them eagerly, an ImportError will be raised.
    # By mocking them to raise ImportError, we simulate them not being installed.
    # This proves decoupling!
    import_orig = __import__
    
    def mocked_import(name, *args, **kwargs):
        if name in ('openai', 'langchain', 'llama_index', 'sentence_transformers', 'torch', 'faiss', 'pandas', 'pyarrow', 'duckdb', 'ijson'):
            raise ImportError(f"No module named '{name}'")
        return import_orig(name, *args, **kwargs)
    
    with patch('builtins.__import__', side_effect=mocked_import):
        try:
            # Import core entry points
            import vidurai
            import vidurai.cli
            import vidurai.storage.database
            import vidurai.daemon.server
            import vidurai.mcp_server
            import vidurai.vismriti_memory
        except ImportError as e:
            pytest.fail(f"Core import failed due to eager optional dependency: {e}")

def test_optional_import_error_message():
    """Verify that using optional features raises an actionable error."""
    import_orig = __import__
    
    def mocked_import(name, *args, **kwargs):
        if name == 'openai':
            raise ImportError("No module named 'openai'")
        return import_orig(name, *args, **kwargs)
        
    with patch('builtins.__import__', side_effect=mocked_import):
        # We know semantic compressor requires openai
        from vidurai.core.semantic_compressor_v2 import LLMClient
        
        client = LLMClient(provider="openai")
        with pytest.raises(ImportError) as exc:
            client._get_client()
            
        assert "This feature requires optional AI dependencies" in str(exc.value)
        assert "vidurai[ai]" in str(exc.value)

def test_vector_brain_import_error_message():
    import_orig = __import__
    
    def mocked_import(name, *args, **kwargs):
        if name == 'sentence_transformers':
            raise ImportError("No module named 'sentence_transformers'")
        return import_orig(name, *args, **kwargs)
        
    with patch('builtins.__import__', side_effect=mocked_import):
        from vidurai.core.intelligence.vector_brain import VectorEngine
        engine = VectorEngine()
        with pytest.raises(ImportError) as exc:
            engine.model()
            
        assert "This feature requires optional AI dependencies" in str(exc.value)
        assert "vidurai[local-embeddings]" in str(exc.value)

def test_ingestion_cli_error_message():
    import_orig = __import__
    
    def mocked_import(name, *args, **kwargs):
        if 'ijson' in name or 'vidurai.core.ingestion.manager' in name:
            raise ImportError("No module named 'ijson'")
        return import_orig(name, *args, **kwargs)
        
    with patch('builtins.__import__', side_effect=mocked_import):
        from vidurai.cli import ingest
        runner = CliRunner()
        # Pass a fake file to bypass click's path validation
        with runner.isolated_filesystem():
            with open("fake.json", "w") as f:
                f.write("{}")
            result = runner.invoke(ingest, ["fake.json"])
            
            assert result.exit_code == 1
            assert "This feature requires optional ingestion dependencies" in result.output
            assert "vidurai[ingestion]" in result.output
