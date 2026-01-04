#!/usr/bin/env python3
"""
Test IPC Client - For testing the IPC server standalone

Usage:
    1. Start the IPC server: python -m ipc.server
    2. Run this client: python -m ipc.test_client
"""

import sys
import json
import asyncio
import getpass
import tempfile
import os
from pathlib import Path

# Determine pipe path
def get_pipe_path() -> str:
    uid = getpass.getuser()
    if sys.platform == 'win32':
        return f"\\\\.\\pipe\\vidurai-{uid}"
    else:
        return os.path.join(tempfile.gettempdir(), f"vidurai-{uid}.sock")


async def test_client():
    """Test the IPC server with a simple client"""
    pipe_path = get_pipe_path()
    print("=" * 60)
    print("IPC TEST CLIENT")
    print("=" * 60)
    print(f"Connecting to: {pipe_path}")
    print()

    try:
        if sys.platform == 'win32':
            reader, writer = await asyncio.open_connection(path=pipe_path)
        else:
            reader, writer = await asyncio.open_unix_connection(pipe_path)

        print("PASS: Connected!")
        print()

        # Test 1: Ping
        print("TEST 1: Sending ping...")
        msg = json.dumps({"v": 1, "type": "ping", "ts": 1234567890, "id": "test-1"}) + "\n"
        writer.write(msg.encode())
        await writer.drain()

        response_line = await asyncio.wait_for(reader.readline(), timeout=5)
        response = json.loads(response_line.decode().strip())
        if response.get("type") == "pong" and response.get("ok"):
            print(f"PASS: Received pong - {response}")
        else:
            print(f"FAIL: Unexpected response - {response}")
        print()

        # Test 2: Echo (unknown type should return ack)
        print("TEST 2: Sending echo...")
        msg = json.dumps({"v": 1, "type": "echo", "ts": 1234567890, "id": "test-2", "data": {"hello": "world"}}) + "\n"
        writer.write(msg.encode())
        await writer.drain()

        response_line = await asyncio.wait_for(reader.readline(), timeout=5)
        response = json.loads(response_line.decode().strip())
        print(f"RESPONSE: {response}")
        print()

        # Test 3: Wait for heartbeat
        print("TEST 3: Waiting for heartbeat (up to 10s)...")
        try:
            while True:
                line = await asyncio.wait_for(reader.readline(), timeout=10)
                if not line:
                    break
                data = json.loads(line.decode().strip())
                if data.get("type") == "heartbeat":
                    print(f"PASS: Received heartbeat - {data}")
                    break
                else:
                    print(f"OTHER: {data}")
        except asyncio.TimeoutError:
            print("FAIL: No heartbeat within 10s")
        print()

        print("=" * 60)
        print("TESTS COMPLETE")
        print("=" * 60)

    except ConnectionRefusedError:
        print("FAIL: Connection refused")
        print("Make sure the IPC server is running:")
        print("  python -m ipc.server")
    except FileNotFoundError:
        print(f"FAIL: Socket not found: {pipe_path}")
        print("Make sure the IPC server is running")
    except Exception as e:
        print(f"ERROR: {e}")
    finally:
        if 'writer' in locals():
            writer.close()
            await writer.wait_closed()
        print("\nDisconnected.")


if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(test_client())
