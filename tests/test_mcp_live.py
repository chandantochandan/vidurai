#!/usr/bin/env python3
"""
Vidurai MCP Server Live Test
Tests the HTTP-based MCP server endpoints
"""
import subprocess
import time
import requests
import sys
import os
import signal

# CONFIG - Match mcp_server.py defaults
PORT = 8765
BASE_URL = f"http://localhost:{PORT}"
PROJECT_PATH = os.getcwd()

def log(msg, level="INFO"):
    colors = {"INFO": "\033[96m", "OK": "\033[92m", "FAIL": "\033[91m", "WARN": "\033[93m"}
    print(f"{colors.get(level, '')}{msg}\033[0m")

def test_mcp_server():
    """Test the MCP server lifecycle"""

    # 1. START SERVER
    log("🚀 Starting Vidurai MCP Server...")
    process = subprocess.Popen(
        [sys.executable, "-m", "vidurai.mcp_server", "--allow-all-origins"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={**os.environ, "PYTHONUNBUFFERED": "1"}
    )

    try:
        # Give server time to start
        time.sleep(3)

        # Check if process is still running
        if process.poll() is not None:
            stdout, stderr = process.communicate()
            log(f"❌ Server failed to start: {stderr.decode()}", "FAIL")
            return 1

        # 2. HEALTH CHECK
        log("\n💓 Testing /health endpoint...")
        try:
            resp = requests.get(f"{BASE_URL}/health", timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                log(f"   ✅ Health OK: {data}", "OK")
            else:
                log(f"   ❌ Health check failed: {resp.status_code}", "FAIL")
                return 1
        except Exception as e:
            log(f"   ❌ Connection failed: {e}", "FAIL")
            return 1

        # 3. CAPABILITIES
        log("\n📋 Testing /capabilities endpoint...")
        resp = requests.get(f"{BASE_URL}/capabilities", timeout=5)
        if resp.status_code == 200:
            caps = resp.json()
            tools = [t['name'] for t in caps.get('tools', [])]
            log(f"   ✅ Tools available: {tools}", "OK")
        else:
            log(f"   ❌ Capabilities failed: {resp.status_code}", "FAIL")

        # 4. TEST get_active_project
        log("\n📂 Testing get_active_project tool...")
        resp = requests.post(f"{BASE_URL}/", json={
            "tool": "get_active_project",
            "params": {}
        }, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            log(f"   ✅ Active project: {data.get('result', 'unknown')}", "OK")
        else:
            log(f"   ⚠️ get_active_project: {resp.status_code}", "WARN")

        # 5. TEST search_memories
        log("\n🔍 Testing search_memories tool...")
        resp = requests.post(f"{BASE_URL}/", json={
            "tool": "search_memories",
            "params": {
                "project": PROJECT_PATH,
                "query": "test",
                "limit": 5
            }
        }, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            count = data.get('count', 0)
            log(f"   ✅ Search returned {count} memories", "OK")
        else:
            log(f"   ⚠️ search_memories: {resp.status_code}", "WARN")

        # 6. TEST get_project_context
        log("\n🧠 Testing get_project_context tool...")
        resp = requests.post(f"{BASE_URL}/", json={
            "tool": "get_project_context",
            "params": {
                "project": PROJECT_PATH,
                "query": "architecture",
                "max_tokens": 500
            }
        }, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            result = data.get('result', '')
            log(f"   ✅ Context length: {len(result)} chars", "OK")
            if result and len(result) > 50:
                log(f"   📝 Preview: {result[:100]}...", "INFO")
        else:
            log(f"   ⚠️ get_project_context: {resp.status_code}", "WARN")

        # 7. TEST get_recent_activity
        log("\n⏰ Testing get_recent_activity tool...")
        resp = requests.post(f"{BASE_URL}/", json={
            "tool": "get_recent_activity",
            "params": {
                "project": PROJECT_PATH,
                "hours": 24
            }
        }, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            count = data.get('count', 0)
            log(f"   ✅ Recent activity: {count} events", "OK")
        else:
            log(f"   ⚠️ get_recent_activity: {resp.status_code}", "WARN")

        log("\n" + "="*50)
        log("✅ MCP SERVER TEST PASSED", "OK")
        log("="*50)
        return 0

    except Exception as e:
        log(f"\n❌ FATAL ERROR: {e}", "FAIL")
        import traceback
        traceback.print_exc()
        return 1

    finally:
        # CLEANUP
        log("\n🛑 Stopping MCP Server...")
        try:
            os.kill(process.pid, signal.SIGTERM)
            process.wait(timeout=5)
            log("   Server stopped cleanly", "OK")
        except:
            process.kill()
            log("   Server force-killed", "WARN")

if __name__ == "__main__":
    sys.exit(test_mcp_server())
