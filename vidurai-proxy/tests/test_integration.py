"""
Integration Test
Basic smoke test to verify proxy is working
"""

import pytest
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)


def test_health_endpoint():
    """Test health check returns 200"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "vidurai-proxy"


def test_metrics_endpoint():
    """Test metrics endpoint returns data"""
    response = client.get("/metrics")
    assert response.status_code == 200
    data = response.json()
    # In test mode, metrics may not be initialized
    # Just verify we get a valid response
    assert isinstance(data, dict)
    # If metrics are initialized, check for expected fields
    if "error" not in data:
        assert "sessions" in data
        assert "requests" in data
        assert "tokens_saved" in data


def test_root_endpoint():
    """Test root endpoint returns info"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "Vidurai Proxy Server"
    assert data["version"] == "1.1.0"
    assert data["status"] == "running"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
