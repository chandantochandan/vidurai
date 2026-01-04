"""
Pytest configuration for Vidurai tests.

Provides async test support and common fixtures.
"""

import pytest
import asyncio


@pytest.fixture(scope="session")
def event_loop():
    """
    Create an event loop for async tests.
    
    This fixture ensures that async tests have a proper event loop
    and handles cleanup automatically.
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_db_path(tmp_path):
    """
    Provide a temporary database path for tests.
    
    Args:
        tmp_path: pytest's temporary directory fixture
        
    Returns:
        Path: Temporary database file path
    """
    return tmp_path / "test_vidurai.db"


@pytest.fixture
def temp_project_path(tmp_path):
    """
    Provide a temporary project directory for tests.
    
    Args:
        tmp_path: pytest's temporary directory fixture
        
    Returns:
        Path: Temporary project directory path
    """
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()
    return project_dir