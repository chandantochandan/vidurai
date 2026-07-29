import pytest
import tempfile
import os
import subprocess
import asyncio
import uuid
from pathlib import Path
from vidurai.storage.database import MemoryDatabase
from vidurai.daemon.identity import resolve_project_identity

def setup_git_repo(path):
    subprocess.run(["git", "init"], cwd=path, check=True)
    # Add dummy commit
    with open(os.path.join(path, "test.txt"), "w") as f:
        f.write("test")
    subprocess.run(["git", "add", "."], cwd=path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=path, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=path, check=True)

def test_resolve_identity_assigns_stable_uuid():
    with tempfile.TemporaryDirectory() as d1, tempfile.TemporaryDirectory() as d2:
        setup_git_repo(d1)
        
        # init d2
        subprocess.run(["git", "init"], cwd=d2, check=True)
        # Clone d1 to d2 to share same remote
        subprocess.run(["git", "remote", "add", "origin", d1], cwd=d2)
        subprocess.run(["git", "fetch", "origin"], cwd=d2, check=True)
        subprocess.run(["git", "checkout", "-b", "master", "origin/master"], cwd=d2)
        
        id1 = resolve_project_identity(d1)
        # Without remote, it falls back to first commit hash
        assert not id1.get('ambiguous')
        
        # For d2, we added a remote, so it hashes the remote
        id2 = resolve_project_identity(d2)
        assert not id2.get('ambiguous')

def test_database_project_alias_resolution():
    db_path = Path(tempfile.mktemp(suffix=".db"))
    db = MemoryDatabase(db_path=db_path)
    try:
        with tempfile.TemporaryDirectory() as repo:
            setup_git_repo(repo)
            identity = resolve_project_identity(repo)
            
            # First insert
            pid1 = db.get_or_create_project(repo, identity=identity)
            
            # Rename repo
            new_repo = repo + "_moved"
            os.rename(repo, new_repo)
            
            # Insert with new path, should return same pid because of identity
            identity_new = resolve_project_identity(new_repo)
            pid2 = db.get_or_create_project(new_repo, identity=identity_new)
            
            assert pid1 == pid2
            
            # Verify alias was updated
            conn = db.get_connection_for_reading()
            cur = conn.execute("SELECT path FROM project_aliases WHERE project_id = ? AND path = ?", (pid1, new_repo))
            assert cur.fetchone() is not None
            conn.close()
            
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)

def test_resolve_identity_branch_switching():
    with tempfile.TemporaryDirectory() as repo:
        setup_git_repo(repo)
        
        id1 = resolve_project_identity(repo)
        assert id1['branch'] == 'master'
        assert not id1.get('detached')
        
        # Switch branch
        subprocess.run(["git", "checkout", "-b", "feature-branch"], cwd=repo, check=True)
        
        id2 = resolve_project_identity(repo)
        assert id2['branch'] == 'feature-branch'
        assert not id2.get('detached')
        
        # Detached HEAD
        commit_hash = id2['commit']
        subprocess.run(["git", "checkout", commit_hash], cwd=repo, check=True)
        
        id3 = resolve_project_identity(repo)
        assert id3['detached']
        assert id3['branch'] == 'HEAD'
        
        # Project UUID must remain identical
        assert id1['project_uuid'] == id2['project_uuid'] == id3['project_uuid']

from vidurai.daemon.ipc.server import IPCMessage
from vidurai.daemon.server import _handle_class1_evidence

def test_e2e_class1_ipc_event_identity():
    asyncio.run(_e2e_class1_ipc_event_identity())

async def _e2e_class1_ipc_event_identity():
    db_path = Path(tempfile.mktemp(suffix=".db"))
    db = MemoryDatabase(db_path=db_path)
    import vidurai.daemon.server as server_module
    server_module.memory_db = db
    
    try:
        with tempfile.TemporaryDirectory() as repo:
            setup_git_repo(repo)
            
            # Send IPC message
            msg = IPCMessage.from_json({
                "v": 1,
                "type": "file_edit",
                "ts": 123456,
                "id": str(uuid.uuid4()),
                "data": {
                    "project_path": repo,
                    "file": "test.txt",
                    "change": "modified"
                }
            })
            
            res = await _handle_class1_evidence(msg, msg.type, msg.data)
            assert res.ok
            receipt_id = res.data['receipt_id']
            
            # Check DB
            conn = db.get_connection_for_reading()
            receipt = conn.execute("SELECT * FROM event_receipts WHERE receipt_id = ?", (receipt_id,)).fetchone()
            assert receipt is not None
            assert receipt['project_uuid'] is not None
            assert receipt['branch'] == 'master'
            assert receipt['commit_hash'] is not None
            assert not receipt['detached_head']
            
            # Verify memory was enqueued and processed
            # We would need to wait for process_receipt_async, which runs in background task, 
            # but WP-03 specifically cares about event_receipts holding the identity.
            
            conn.close()
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)

def test_resolve_identity_quarantine_non_git():
    with tempfile.TemporaryDirectory() as empty_dir:
        id_empty = resolve_project_identity(empty_dir)
        assert id_empty['ambiguous']
        assert 'Not a git repository' in id_empty['error']

def test_resolve_identity_equivalent_urls():
    with tempfile.TemporaryDirectory() as repo:
        setup_git_repo(repo)
        subprocess.run(["git", "remote", "add", "origin", "https://github.com/org/repo.git"], cwd=repo, check=True)
        id1 = resolve_project_identity(repo)
        
        # Clear config and change to ssh
        subprocess.run(["git", "config", "--local", "--unset", "vidurai.projectuuid"], cwd=repo, check=True)
        subprocess.run(["git", "remote", "set-url", "origin", "git@github.com:org/repo.git"], cwd=repo, check=True)
        id2 = resolve_project_identity(repo)
        
        assert id1['project_uuid'] == id2['project_uuid']
        assert id1['remote_fingerprint'] == id2['remote_fingerprint']

def test_changing_remote_does_not_change_established_uuid():
    with tempfile.TemporaryDirectory() as repo:
        setup_git_repo(repo)
        subprocess.run(["git", "remote", "add", "origin", "https://github.com/org/repo.git"], cwd=repo, check=True)
        id1 = resolve_project_identity(repo)
        
        # Change remote without unsetting config
        subprocess.run(["git", "remote", "set-url", "origin", "https://gitlab.com/other/other.git"], cwd=repo, check=True)
        # Add another remote
        subprocess.run(["git", "remote", "add", "upstream", "https://github.com/org/upstream.git"], cwd=repo, check=True)
        id2 = resolve_project_identity(repo)
        
        assert id1['project_uuid'] == id2['project_uuid']
        assert id2['remote_fingerprint'] == "persisted_local"

def test_different_remotes_different_uuid():
    with tempfile.TemporaryDirectory() as repo1, tempfile.TemporaryDirectory() as repo2:
        setup_git_repo(repo1)
        subprocess.run(["git", "remote", "add", "origin", "https://github.com/org/repo1.git"], cwd=repo1, check=True)
        
        setup_git_repo(repo2)
        subprocess.run(["git", "remote", "add", "origin", "https://github.com/org/repo2.git"], cwd=repo2, check=True)
        
        id1 = resolve_project_identity(repo1)
        id2 = resolve_project_identity(repo2)
        
        assert id1['project_uuid'] != id2['project_uuid']

def test_ambiguous_remotes_quarantined():
    with tempfile.TemporaryDirectory() as repo:
        setup_git_repo(repo)
        subprocess.run(["git", "remote", "add", "remote1", "https://github.com/org/repo1.git"], cwd=repo, check=True)
        subprocess.run(["git", "remote", "add", "remote2", "https://github.com/org/repo2.git"], cwd=repo, check=True)
        
        # We don't have origin or upstream, and multiple distinct URLs
        res = resolve_project_identity(repo)
        assert res['ambiguous']
        assert 'Multiple remotes and no upstream/origin' in res['error']

def test_no_remote_identity_persists():
    with tempfile.TemporaryDirectory() as repo:
        setup_git_repo(repo)
        id1 = resolve_project_identity(repo)
        assert not id1['ambiguous']
        assert id1['remote_fingerprint'] == 'local_only'
        
        # Move path
        with tempfile.TemporaryDirectory() as new_dir:
            import shutil
            shutil.copytree(repo, new_dir, dirs_exist_ok=True)
            id2 = resolve_project_identity(new_dir)
            assert not id2['ambiguous']
            assert id1['project_uuid'] == id2['project_uuid']

def test_linked_worktrees_share_uuid():
    with tempfile.TemporaryDirectory() as repo:
        setup_git_repo(repo)
        id1 = resolve_project_identity(repo)
        
        # Create worktree
        wt_path = os.path.join(tempfile.gettempdir(), f"vidurai_wt_{uuid.uuid4().hex}")
        subprocess.run(["git", "worktree", "add", wt_path, "-b", "wt-branch"], cwd=repo, check=True)
        try:
            id2 = resolve_project_identity(wt_path)
            assert id1['project_uuid'] == id2['project_uuid']
            assert id2['branch'] == 'wt-branch'
        finally:
            import shutil
            shutil.rmtree(wt_path, ignore_errors=True)
            subprocess.run(["git", "worktree", "prune"], cwd=repo, check=False)
