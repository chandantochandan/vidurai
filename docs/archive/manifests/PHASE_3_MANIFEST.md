# Phase 3 Manifest: The Nervous System (Connection)

**Version:** 2.1.0-Guardian
**Date:** 2024-12-15
**Status:** IMPLEMENTED

---

## 1. Overview

Phase 3 implements "The Nervous System" - the connection layer between user intent and external frameworks:
- **StateLinker:** Focus tracking with Reality Grounding (validates paths exist)
- **ViduraiRetriever:** LangChain Bridge with Inheritance Trap pattern
- **Daemon Wiring:** IPC handlers for focus, get_focus, resolve_path

---

## 2. The StateLinker (Focus Tracking)

### File Location
`vidurai/core/state/linker.py`

### Glass Box Protocol: Reality Grounding

```python
# TRUST NO ONE: Validate ALL paths exist on disk before accepting
def update_focus(self, context: Dict[str, Any]) -> bool:
    file_path_str = context.get('file')

    if file_path_str:
        file_path = Path(file_path_str)

        # Reality Grounding: Verify file exists
        if not file_path.exists():
            logger.warning(f"StateLinker: Rejected update - file not found")
            return False

        if not file_path.is_file():
            logger.warning(f"StateLinker: Rejected update - not a file")
            return False
```

**Why:** Never pollute state with hallucinated/missing paths. Trust No One.

### Core Features

1. **Focus Tracking:** Tracks what file/line/selection the user is working on
2. **Recent Files:** Maintains a list of recently accessed files (up to 10)
3. **Fuzzy Resolution:** Resolves partial paths (e.g., "auth" → "src/core/auth.py")
4. **Thread-Safe:** RLock protects all state mutations

### FocusContext Dataclass

```python
@dataclass
class FocusContext:
    file: Optional[Path] = None
    line: Optional[int] = None
    column: Optional[int] = None
    selection: Optional[str] = None
    project_root: Optional[Path] = None
    timestamp: datetime = field(default_factory=datetime.now)
```

### Fuzzy Path Resolution

```python
def resolve_fuzzy_path(partial_path: str, project_root: Path) -> Optional[Path]:
    # Strategy 1: Direct match (relative from root)
    # Strategy 2: Add .py extension if missing
    # Strategy 3: Recursive glob search (**/{partial}*)
```

---

## 3. The ViduraiRetriever (LangChain Bridge)

### File Location
`vidurai/core/bridge/retriever.py`

### Glass Box Protocol: Inheritance Trap

```python
# TYPE_CHECKING block - imports only during static analysis
if TYPE_CHECKING:
    from langchain_core.documents import Document
    from langchain_core.retrievers import BaseRetriever

# Lazy availability check (cached)
def _check_langchain() -> bool:
    global _LANGCHAIN_AVAILABLE
    if _LANGCHAIN_AVAILABLE is None:
        try:
            import langchain_core
            _LANGCHAIN_AVAILABLE = True
        except ImportError:
            _LANGCHAIN_AVAILABLE = False
    return _LANGCHAIN_AVAILABLE
```

**Why:** LangChain may not be installed. Don't crash the daemon if missing.

### Duck Typing Pattern

```python
class ViduraiRetriever:
    """
    Uses duck typing instead of direct BaseRetriever inheritance.
    - If langchain is available, can be used as a retriever
    - If not, provides standalone functionality
    """

    def get_relevant_documents(self, query: str) -> List[Any]:
        """LangChain BaseRetriever interface"""
        pass

    def invoke(self, input: str, **kwargs) -> List[Any]:
        """LangChain Runnable interface"""
        pass
```

### ViduraiDocument Wrapper

```python
class ViduraiDocument:
    """
    LangChain-compatible Document wrapper.
    Can convert to real Document if langchain is installed.
    """
    page_content: str
    metadata: Dict[str, Any]

    def to_langchain_document(self) -> 'Document':
        from langchain_core.documents import Document
        return Document(page_content=self.page_content, metadata=self.metadata)
```

### Integration Example

```python
# With LangChain
from vidurai.core.bridge import ViduraiRetriever
from langchain.chains import RetrievalQA

retriever = ViduraiRetriever(audience='ai')
qa = RetrievalQA.from_chain_type(llm=llm, retriever=retriever)

# Standalone
retriever = ViduraiRetriever()
docs = retriever.invoke("authentication")
for doc in docs:
    print(doc.page_content)
```

---

## 4. Daemon IPC Handlers

### New Message Types

| Type | Direction | Description |
|------|-----------|-------------|
| `focus` | Client→Daemon | Update user focus (file/line/selection) |
| `get_focus` | Client→Daemon | Get current focus state |
| `resolve_path` | Client→Daemon | Resolve partial path to full path |

### IPC Protocol

#### focus
```json
{
  "type": "focus",
  "data": {
    "file": "/path/to/file.py",
    "line": 42,
    "column": 10,
    "selection": "def login():",
    "project_root": "/path/to/project"
  }
}
```

Response (success):
```json
{
  "type": "ack",
  "ok": true,
  "data": {
    "file": "/path/to/file.py",
    "line": 42,
    "accepted": true
  }
}
```

Response (Reality Grounding rejection):
```json
{
  "type": "ack",
  "ok": false,
  "data": {
    "accepted": false,
    "reason": "file_not_found"
  }
}
```

#### get_focus
```json
{
  "type": "get_focus"
}
```

Response:
```json
{
  "type": "response",
  "ok": true,
  "data": {
    "active_file": "/path/to/file.py",
    "active_line": 42,
    "selection": "def login():",
    "recent_files": ["/path/to/file.py", "/path/to/other.py"],
    "stats": {...}
  }
}
```

#### resolve_path
```json
{
  "type": "resolve_path",
  "data": {
    "path": "auth"
  }
}
```

Response:
```json
{
  "type": "response",
  "ok": true,
  "data": {
    "partial": "auth",
    "resolved": "/path/to/src/core/auth.py",
    "found": true
  }
}
```

---

## 5. Verification Commands

### Test StateLinker
```bash
# Run test cases
python -m vidurai.core.state.linker --test

# Show stats
python -m vidurai.core.state.linker --stats

# Resolve a path
python -m vidurai.core.state.linker --resolve auth
```

### Test ViduraiRetriever
```bash
# Run test cases
python -m vidurai.core.bridge.retriever --test

# Show stats
python -m vidurai.core.bridge.retriever --stats

# Query test
python -m vidurai.core.bridge.retriever --query "authentication"
```

---

## 6. Architecture

### File Structure
```
vidurai/
├── core/
│   ├── state/
│   │   ├── __init__.py
│   │   └── linker.py           # StateLinker
│   │
│   └── bridge/
│       ├── __init__.py
│       └── retriever.py        # ViduraiRetriever
│
vidurai-daemon/
└── daemon.py                   # IPC handlers (focus, get_focus, resolve_path)
```

### Dependencies
- **pathlib:** Python standard library (path operations)
- **threading:** Python standard library (RLock)
- **langchain_core:** Optional (graceful degradation if missing)

---

## 7. Caveats & Limitations

### StateLinker
1. **Reality Grounding:** Rejects updates for non-existent files (by design)
2. **Thread-Safe:** RLock prevents race conditions
3. **Recent Files Limit:** Max 10 recent files tracked

### ViduraiRetriever
1. **LangChain Optional:** Works without langchain installed
2. **Duck Typing:** May not satisfy all BaseRetriever type checks
3. **Synchronous:** Async methods delegate to sync implementation

### Daemon Wiring
1. **StateLinker Singleton:** One instance per daemon
2. **Project Root:** Defaults to daemon's CWD
3. **Lazy Init:** Initialized in background task (non-blocking)

---

## 8. Next Steps (Phase 4)

1. **Build Runner:** Execute builds in Shadow Sandbox
2. **RL Dream Cycle:** Offline batch training on Parquet archives
3. **VS Code Extension:** Wire focus events to StateLinker IPC

---

*Generated by Vidurai Guardian v2.1.0*
