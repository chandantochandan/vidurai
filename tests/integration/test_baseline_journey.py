import os
import sys
import uuid
import time
import json
import socket
import sqlite3
import subprocess
import pytest
import shutil
import tempfile
import urllib.request
import urllib.error

# We want to ensure we're testing the isolated environment
# The test runner should ideally invoke CLI via subprocess with manipulated HOME/TMPDIR
# to guarantee perfect isolation, similar to the verified manual journey.

class TestBaselineJourney:
    @pytest.fixture(autouse=True)
    def isolated_env(self):
        # Stage A - Isolated setup
        self.temp_dir = tempfile.mkdtemp(prefix="vidurai-wp00-baseline-")
        self.env = os.environ.copy()
        self.env["HOME"] = self.temp_dir
        self.env["TMPDIR"] = self.temp_dir
        
        self.vidurai_dir = os.path.join(self.temp_dir, ".vidurai")
        self.socket_path = os.path.join(self.vidurai_dir, "vidurai-tester.sock")
        # In reality, daemon creates vidurai-<username>.sock. We'll find it dynamically.
        
        # Create a synthetic git repo
        self.project_dir = os.path.join(self.temp_dir, "synthetic_project")
        os.makedirs(self.project_dir)
        subprocess.run(["git", "init"], cwd=self.project_dir, check=True, capture_output=True)
        self.test_file = os.path.join(self.project_dir, "example.txt")
        with open(self.test_file, "w") as f:
            f.write("Initial state\n")
        subprocess.run(["git", "add", "example.txt"], cwd=self.project_dir, check=True)
        subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=self.project_dir, check=True)
        
        self.mcp_port = self._find_free_port()
        self.marker = f"WP00_MARKER_{uuid.uuid4().hex}"
        
        yield
        
        # Stage G - Cleanup and isolation confirmation
        
        # Record daemon PID
        daemon_pid = None
        pid_file = os.path.join(self.vidurai_dir, "daemon.pid")
        if os.path.exists(pid_file):
            with open(pid_file) as f:
                daemon_pid = int(f.read().strip())
                
        # Stop processes
        subprocess.run([sys.executable, "-m", "vidurai.cli", "stop"], env=self.env, capture_output=True)
        if hasattr(self, "mcp_process") and self.mcp_process.poll() is None:
            self.mcp_process.terminate()
            self.mcp_process.wait(timeout=5)
            
        import psutil
        errors = []
        if daemon_pid and psutil.pid_exists(daemon_pid):
            errors.append(f"Daemon process {daemon_pid} leaked")
        if hasattr(self, "mcp_process") and self.mcp_process.poll() is None:
            errors.append(f"MCP process {self.mcp_process.pid} leaked")
            
        # Dump logs if any
        log_path = os.path.join(self.vidurai_dir, "vidurai.log")
        log_content = ""
        if os.path.exists(log_path):
            log_content = open(log_path).read()
            print(f"\\n--- Daemon Log ---\\n{log_content}\\n------------------\\n", file=sys.stderr)
            
        # Verify socket and PID files are absent
        socks = [f for f in os.listdir(self.temp_dir) if f.endswith(".sock")] if os.path.exists(self.temp_dir) else []
        if socks:
            errors.append(f"Socket files leaked: {socks}")
        if os.path.exists(pid_file):
            errors.append("PID file leaked")
            
        try:
            if errors:
                pytest.fail(f"Cleanup errors: {errors}\\nLog:\\n{log_content}")
        finally:
            shutil.rmtree(self.temp_dir, ignore_errors=True)
            assert not os.path.exists(self.temp_dir)
        
    def _find_free_port(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            return s.getsockname()[1]
            
    def _get_socket_path(self):
        # Wait for socket to be created and return its path
        for _ in range(50):
            if os.path.exists(self.temp_dir):
                for f in os.listdir(self.temp_dir):
                    if f.endswith(".sock"):
                        return os.path.join(self.temp_dir, f)
            time.sleep(0.1)
        log_path = os.path.join(self.vidurai_dir, "vidurai.log")
        log_content = open(log_path).read() if os.path.exists(log_path) else "No log file"
        raise TimeoutError(f"Daemon socket not found. Log:\\n{log_content}")

    def test_core_regression_journey(self):
        # Stage B - Daemon startup
        start_res = subprocess.run([sys.executable, "-m", "vidurai.cli", "start"], env=self.env, capture_output=True, text=True)
        assert start_res.returncode == 0, f"Daemon failed to start: {start_res.stderr}"
        
        sock_path = self._get_socket_path()
        assert os.path.exists(sock_path)
        
        pid_file = os.path.join(self.vidurai_dir, "daemon.pid")
        assert os.path.exists(pid_file)
        
        # Stage C - Real IPC event
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.connect(sock_path)
            
            # 1. Handshake
            handshake = {
                "v": 1,
                "type": "handshake",
                "ts": int(time.time()*1000),
                "id": "init",
                "data": {"client_name": "vidurai-wp00-tester", "version": "1.0.0"}
            }
            sock.sendall((json.dumps(handshake) + "\n").encode('utf-8'))
            resp_line = ""
            while "\n" not in resp_line:
                resp_line += sock.recv(4096).decode('utf-8')
            ack = json.loads(resp_line.strip())
            assert ack.get("type") == "handshake_ack"
            assert ack.get("ok") is True
            
            # 2. Valid file_edit
            file_edit = {
                "v": 1,
                "type": "file_edit",
                "ts": int(time.time()*1000),
                "data": {
                    "project_path": self.project_dir,
                    "file": self.test_file,
                    "gist": f"User added the marker {self.marker}",
                    "change": "modify"
                }
            }
            sock.sendall((json.dumps(file_edit) + "\n").encode('utf-8'))
            resp_line = ""
            while "\n" not in resp_line:
                resp_line += sock.recv(4096).decode('utf-8')
            edit_ack = json.loads(resp_line.strip())
            assert edit_ack.get("type") == "ack"
            
            # 3. Malformed event
            bad_event = {
                "v": 1,
                "type": "bad_event_type",
                "ts": int(time.time()*1000),
                "id": "evt2",
                "data": {}
            }
            sock.sendall((json.dumps(bad_event) + "\n").encode('utf-8'))
            resp_line = ""
            while "\n" not in resp_line:
                resp_line += sock.recv(4096).decode('utf-8')
            bad_ack = json.loads(resp_line.strip())
            assert bad_ack.get("type") == "error"

        # Wait a moment for async DB insertion
        time.sleep(1)

        # Stage D - SQLite proof
        db_path = os.path.join(self.vidurai_dir, "memory.db")
        assert os.path.exists(db_path)
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM memories")
        count = cursor.fetchone()[0]
        assert count > 0
        
        cursor.execute("SELECT verbatim FROM memories")
        rows = cursor.fetchall()
        found = False
        for row in rows:
            if self.marker in row[0]:
                found = True
                break
        assert found, "Valid memory not found in DB"
        
        # Verify malformed event is not persisted
        cursor.execute("SELECT COUNT(*) FROM memories WHERE event_type = 'bad_event_type'")
        bad_count = cursor.fetchone()[0]
        assert bad_count == 0
        conn.close()

        # Stage E - Restart persistence
        subprocess.run([sys.executable, "-m", "vidurai.cli", "stop"], env=self.env, check=True)
        assert not os.path.exists(pid_file)
        assert not os.path.exists(sock_path)
        
        subprocess.run([sys.executable, "-m", "vidurai.cli", "start"], env=self.env, check=True)
        sock_path = self._get_socket_path()
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM memories")
        post_restart_count = cursor.fetchone()[0]
        conn.close()
        
        assert post_restart_count == count, "Restart duplicated or lost memories"

        # Stage F - Real MCP invocation
        self.mcp_process = subprocess.Popen(
            [sys.executable, "-m", "vidurai.cli", "server", "--port", str(self.mcp_port)],
            env=self.env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait for MCP to start
        time.sleep(2)
        
        # Retrieve tools
        try:
            req = urllib.request.Request(f"http://localhost:{self.mcp_port}/capabilities")
            with urllib.request.urlopen(req) as response:
                caps = json.loads(response.read().decode())
                tool_names = [t.get("name") for t in caps.get("tools", [])]
                assert "search_memories" in tool_names
        except urllib.error.URLError as e:
            pytest.fail(f"MCP server unreachable: {e}")
            
        # Search for marker
        search_req = {
            "tool": "search_memories",
            "params": {
                "query": self.marker,
                "project": self.project_dir
            }
        }
        req = urllib.request.Request(
            f"http://localhost:{self.mcp_port}/",
            data=json.dumps(search_req).encode(),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req) as response:
            res = json.loads(response.read().decode())
            assert res.get("count", 0) > 0
            assert self.marker in res.get("result", [{}])[0].get("verbatim", "")
            
        # Search for nonexistent marker
        search_req["params"]["query"] = "NONEXISTENT_MARKER_12345"
        req = urllib.request.Request(
            f"http://localhost:{self.mcp_port}/",
            data=json.dumps(search_req).encode(),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req) as response:
            res = json.loads(response.read().decode())
            assert res.get("count", 0) == 0

