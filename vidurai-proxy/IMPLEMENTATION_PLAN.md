# Vidurai Proxy Implementation Plan

**Step-by-step guide to building the transparent AI proxy server**

---

## Phase 1: Foundation (Core Infrastructure)

### Step 1.1: Config Loader
**File**: `src/utils/config_loader.py`

**Purpose**: Load and validate configuration from YAML + .env

**Implementation**:
```python
class Config:
    - Load config.yaml
    - Override with environment variables
    - Validate all required fields
    - Provide typed access to settings
```

**Key Functions**:
- `load_config() -> Config`
- `get(key: str) -> Any`
- `validate() -> bool`

**Dependencies**: PyYAML, pydantic, python-dotenv

---

### Step 1.2: Logging Setup
**File**: `src/utils/logger.py`

**Purpose**: Unified logging with terminal UI support

**Implementation**:
```python
- Setup loguru with custom formats
- Terminal output (rich formatting)
- File output (rotating logs)
- Audit logging
```

**Key Functions**:
- `setup_logger(config: Config)`
- `log_request(request, response, metrics)`
- `log_audit(session_id, action, data)`

**Dependencies**: loguru, rich

---

### Step 1.3: Provider Detector
**File**: `src/utils/provider_detector.py`

**Purpose**: Auto-detect AI provider from request

**Implementation**:
```python
def detect_provider(request: Request) -> str:
    # Check URL path
    if "/v1/messages" in request.url.path:
        return "anthropic"
    elif "/v1/chat/completions" in request.url.path:
        return "openai"
    # Check headers
    # Check request body structure
```

**Key Functions**:
- `detect_provider(request: Request) -> str`
- `extract_api_key(request: Request, provider: str) -> str`
- `get_provider_config(provider: str) -> dict`

---

## Phase 2: Session Management

### Step 2.1: Session Manager
**File**: `src/middleware/session_manager.py`

**Purpose**: Auto-create and manage sessions from API key hashes

**Implementation**:
```python
class SessionManager:
    def __init__(self):
        self.sessions = {}  # session_id -> Session

    def get_or_create_session(self, api_key: str) -> Session:
        session_id = hashlib.sha256(api_key.encode()).hexdigest()[:16]
        if session_id not in self.sessions:
            self.sessions[session_id] = Session(
                session_id=session_id,
                vidurai_memory=ViduraiMemory(...),
                created_at=datetime.now(),
                last_activity=datetime.now()
            )
        return self.sessions[session_id]

    def cleanup_expired(self):
        # Remove sessions older than timeout
```

**Key Classes**:
- `Session` (dataclass with Vidurai instance)
- `SessionManager` (manages all sessions)

**Key Functions**:
- `get_or_create_session(api_key: str) -> Session`
- `get_session(session_id: str) -> Optional[Session]`
- `cleanup_expired_sessions()`
- `save_session_to_disk(session: Session)`
- `load_session_from_disk(session_id: str) -> Session`

---

### Step 2.2: Session Persistence
**File**: `src/utils/session_persistence.py`

**Purpose**: Save/load Vidurai memory to disk

**Implementation**:
```python
def save_session(session: Session, memory_dir: str):
    # Serialize Vidurai memory state
    # Save to .vidurai_sessions/{session_id}.json

def load_session(session_id: str, memory_dir: str) -> Session:
    # Load from disk
    # Reconstruct Vidurai memory
```

**Storage Format**: JSON (Vidurai memory state)

---

## Phase 3: Vidurai Integration

### Step 3.1: Vidurai Proxy Middleware
**File**: `src/middleware/vidurai_proxy.py`

**Purpose**: Core Vidurai compression logic

**Implementation**:
```python
class ViduriMiddleware:
    async def process_request(
        self,
        request: Request,
        session: Session
    ) -> Request:
        # 1. Extract messages from request
        messages = extract_messages(request)

        # 2. Add to Vidurai memory
        for msg in messages:
            session.vidurai_memory.remember(
                content=msg.content,
                metadata={"role": msg.role}
            )

        # 3. Check if compression threshold reached
        if session.message_count >= config.compression_threshold:
            # 4. Compress context via Vidurai
            compressed = session.vidurai_memory.recall(
                query=messages[-1].content,
                limit=config.max_memories_returned,
                min_importance=config.min_importance
            )

            # 5. Replace messages with compressed context
            request = replace_messages(request, compressed)

        return request
```

**Key Functions**:
- `extract_messages(request: Request) -> List[Message]`
- `compress_context(session: Session, messages: List[Message]) -> List[Message]`
- `replace_messages(request: Request, messages: List[Message]) -> Request`
- `calculate_tokens(messages: List[Message]) -> int`

---

### Step 3.2: Message Extraction
**File**: `src/utils/message_extractor.py`

**Purpose**: Extract messages from provider-specific request formats

**Implementation**:
```python
def extract_anthropic_messages(body: dict) -> List[Message]:
    return [Message(role=m["role"], content=m["content"])
            for m in body.get("messages", [])]

def extract_openai_messages(body: dict) -> List[Message]:
    return [Message(role=m["role"], content=m["content"])
            for m in body.get("messages", [])]
```

---

## Phase 4: Metrics & Tracking

### Step 4.1: Metrics Manager
**File**: `src/middleware/metrics.py`

**Purpose**: Track token savings and costs

**Implementation**:
```python
class MetricsManager:
    def __init__(self):
        self.total_requests = 0
        self.total_tokens_saved = 0
        self.total_cost_saved = 0.0
        self.session_metrics = {}

    def record_request(
        self,
        session_id: str,
        provider: str,
        model: str,
        tokens_before: int,
        tokens_after: int
    ):
        tokens_saved = tokens_before - tokens_after
        cost_saved = self.calculate_cost(provider, model, tokens_saved)

        self.total_requests += 1
        self.total_tokens_saved += tokens_saved
        self.total_cost_saved += cost_saved

        if session_id not in self.session_metrics:
            self.session_metrics[session_id] = SessionMetrics()
        self.session_metrics[session_id].add(tokens_saved, cost_saved)

    def calculate_cost(self, provider: str, model: str, tokens: int) -> float:
        pricing = config.metrics.pricing[provider][model]
        return (tokens / 1_000_000) * pricing["input"]
```

**Key Functions**:
- `record_request(...)`
- `get_session_metrics(session_id: str) -> SessionMetrics`
- `get_total_metrics() -> TotalMetrics`
- `export_metrics(format: str)`

---

### Step 4.2: Terminal UI
**File**: `src/utils/terminal_ui.py`

**Purpose**: Real-time display of proxy stats

**Implementation** (using rich):
```python
class TerminalUI:
    def __init__(self):
        self.live = Live()

    def render(self, metrics: TotalMetrics, sessions: Dict):
        table = Table()
        # Render sessions table
        # Render total stats
        # Render recent requests
        return Panel(table, title="Vidurai Proxy")

    def start(self):
        with self.live:
            while True:
                self.live.update(self.render(...))
                time.sleep(1)
```

---

## Phase 5: Request Routing

### Step 5.1: Anthropic Route
**File**: `src/routes/anthropic.py`

**Purpose**: Handle Anthropic API requests

**Implementation**:
```python
@router.post("/v1/messages")
async def proxy_anthropic_messages(
    request: Request,
    session_manager: SessionManager = Depends(get_session_manager),
    vidurai_middleware: ViduriMiddleware = Depends(get_vidurai_middleware),
    metrics_manager: MetricsManager = Depends(get_metrics_manager)
):
    # 1. Extract API key
    api_key = request.headers.get("x-api-key")

    # 2. Get or create session
    session = session_manager.get_or_create_session(api_key)

    # 3. Get original request body
    body = await request.json()
    original_messages = body["messages"]
    tokens_before = estimate_tokens(original_messages)

    # 4. Process through Vidurai
    modified_request = await vidurai_middleware.process_request(request, session)
    modified_body = await modified_request.json()
    tokens_after = estimate_tokens(modified_body["messages"])

    # 5. Forward to Anthropic API
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{config.anthropic.base_url}/v1/messages",
            headers={
                "x-api-key": api_key,  # Pass-through
                "anthropic-version": request.headers.get("anthropic-version"),
                "content-type": "application/json"
            },
            json=modified_body
        )

    # 6. Record metrics
    metrics_manager.record_request(
        session_id=session.session_id,
        provider="anthropic",
        model=body["model"],
        tokens_before=tokens_before,
        tokens_after=tokens_after
    )

    # 7. Return response (transparent)
    return JSONResponse(
        content=response.json(),
        status_code=response.status_code,
        headers={"X-Vidurai-Stats": f"saved={tokens_before - tokens_after}"}
    )
```

---

### Step 5.2: OpenAI Route
**File**: `src/routes/openai.py`

**Purpose**: Handle OpenAI API requests

**Implementation**: Similar to Anthropic route but for `/v1/chat/completions`

---

### Step 5.3: Health Check Route
**File**: `src/routes/health.py`

**Purpose**: Server health and stats endpoint

**Implementation**:
```python
@router.get("/health")
async def health_check(
    metrics_manager: MetricsManager = Depends(get_metrics_manager)
):
    return {
        "status": "healthy",
        "server": "Vidurai Proxy",
        "version": "1.0.0",
        "uptime_seconds": get_uptime(),
        "stats": {
            "total_requests": metrics_manager.total_requests,
            "active_sessions": len(session_manager.sessions),
            "total_tokens_saved": metrics_manager.total_tokens_saved,
            "total_cost_saved": f"${metrics_manager.total_cost_saved:.4f}"
        }
    }
```

---

## Phase 6: Main Server

### Step 6.1: FastAPI Application
**File**: `src/main.py`

**Purpose**: Server entry point

**Implementation**:
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Load configuration
config = load_config()

# Setup logging
setup_logger(config)

# Create FastAPI app
app = FastAPI(title="Vidurai Proxy", version="1.0.0")

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.server.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize managers (singletons)
session_manager = SessionManager(config)
metrics_manager = MetricsManager(config)
vidurai_middleware = ViduriMiddleware(config)

# Include routes
app.include_router(anthropic_router)
app.include_router(openai_router)
app.include_router(health_router)

# Background tasks
@app.on_event("startup")
async def startup():
    # Start terminal UI
    terminal_ui.start()
    # Start session cleanup task
    asyncio.create_task(session_cleanup_loop())

@app.on_event("shutdown")
async def shutdown():
    # Save all sessions
    session_manager.save_all()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=config.server.host,
        port=config.server.port,
        log_config=None  # We handle logging
    )
```

---

## Implementation Order

### Week 1: Foundation
1. ✅ Config loader (`config_loader.py`)
2. ✅ Logger setup (`logger.py`)
3. ✅ Provider detector (`provider_detector.py`)
4. ✅ Message extractor (`message_extractor.py`)

### Week 2: Core Logic
5. ✅ Session manager (`session_manager.py`)
6. ✅ Session persistence (`session_persistence.py`)
7. ✅ Vidurai middleware (`vidurai_proxy.py`)
8. ✅ Metrics manager (`metrics.py`)

### Week 3: Routes & UI
9. ✅ Health check route (`health.py`)
10. ✅ Anthropic route (`anthropic.py`)
11. ✅ OpenAI route (`openai.py`)
12. ✅ Terminal UI (`terminal_ui.py`)

### Week 4: Integration & Testing
13. ✅ Main server (`main.py`)
14. ✅ Integration tests
15. ✅ End-to-end testing with real APIs
16. ✅ Documentation finalization

---

## Testing Strategy

### Unit Tests
- Test each utility function independently
- Mock external dependencies (Vidurai, API calls)

### Integration Tests
- Test full request flow (request → Vidurai → forward → response)
- Test session creation and persistence
- Test metrics tracking

### End-to-End Tests
- Test with real Anthropic/OpenAI APIs
- Verify compression actually reduces tokens
- Verify responses match provider format exactly

---

## Success Criteria

✅ **Transparent Operation**
- Clients require zero code changes
- Only change: `ANTHROPIC_BASE_URL=http://localhost:8080`

✅ **Compression Works**
- After 10+ messages, token reduction observed
- Compression ratio > 20% on average

✅ **Session Persistence**
- Sessions survive server restart
- Memory restored correctly

✅ **Metrics Accuracy**
- Token counts match actual usage
- Cost calculations correct per provider pricing

✅ **Terminal UI**
- Real-time stats display
- Clear visualization of savings

✅ **Zero Configuration**
- Works out-of-the-box with defaults
- Only required: `OPENAI_API_KEY` in .env

---

## Next Steps After MVP

1. Streaming response support
2. Redis session store (for horizontal scaling)
3. Web dashboard (React)
4. Multi-tenant support
5. Custom compression models
6. Rate limiting & quotas
7. Vercel serverless deployment
8. Docker container
9. Helm chart for Kubernetes

---

## Development Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Install Vidurai locally
pip install -e ../../vidurai/

# Run server
python src/main.py

# Run tests
pytest tests/ -v

# Run with debug logging
LOG_LEVEL=DEBUG python src/main.py

# Format code
black src/ tests/

# Lint code
ruff src/ tests/

# Type check
mypy src/
```

---

**Ready to start implementation!**

Next prompt should begin Phase 1, Step 1.1 (Config Loader).
