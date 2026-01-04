# Vidurai System Architecture (v2.0.0)

Vidurai is a **Distributed Context Management System** running entirely on localhost. It decouples **Context Collection** (Sensors) from **Context Reasoning** (Engine).

## 1. System Topology

The system implements a **Hub-and-Spoke** topology:

* **Hub:** Vidurai Daemon (Python/FastAPI)
* **Spokes:** VS Code Extension, Chrome Extension, Terminal, LLM Proxy
* **Protocol:** Asynchronous Event Streaming via WebSockets (sensors) and HTTP/JSON-RPC (consumers)

```text
┌─────────────────────────────────────────────────────────────────┐
│                        LOCALHOST BOUNDARY                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐    │
│   │ VS Code  │   │ Browser  │   │ Terminal │   │   CLI    │    │
│   │Extension │   │Extension │   │  Agent   │   │  Tools   │    │
│   └────┬─────┘   └────┬─────┘   └────┬─────┘   └────┬─────┘    │
│        │WS            │WS            │StdOut        │HTTP      │
│        ▼              ▼              ▼              ▼          │
│   ┌─────────────────────────────────────────────────────────┐  │
│   │                   VIDURAI DAEMON                         │  │
│   │  ┌─────────────────────────────────────────────────┐    │  │
│   │  │              EVENT INGESTION LAYER              │    │  │
│   │  │  [Schema Validator] → [Entity Extractor] → [Q]  │    │  │
│   │  └──────────────────────────┬──────────────────────┘    │  │
│   │                             ▼                            │  │
│   │  ┌─────────────────────────────────────────────────┐    │  │
│   │  │              SF-V2 COMPRESSION ENGINE           │    │  │
│   │  │  [Role Classifier] → [Scorer] → [Consolidator]  │    │  │
│   │  └──────────────────────────┬──────────────────────┘    │  │
│   │                             ▼                            │  │
│   │  ┌─────────────────────────────────────────────────┐    │  │
│   │  │              STORAGE LAYER (SQLite/WAL)         │    │  │
│   │  │  [Events] [Entities] [Episodes] [Ledger]        │    │  │
│   │  └─────────────────────────────────────────────────┘    │  │
│   └─────────────────────────────────────────────────────────┘  │
│        │HTTP/JSON-RPC                                          │
│        ▼                                                        │
│   ┌──────────┐                    ┌──────────────────────┐     │
│   │   SDK    │◄───────────────────│     LLM PROXY        │     │
│   │  Client  │                    │ (OpenAI-compatible)  │     │
│   └──────────┘                    └──────────────────────┘     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## 2. Core Subsystems

### 2.1 Event Ingestion Pipeline

**Responsibilities:** Normalize heterogeneous telemetry into unified schema.

**Pipeline Stages:**

| Stage | Input | Output | Latency |
| :--- | :--- | :--- | :--- |
| Schema Validation | Raw JSON/WebSocket msg | ViduraiEvent (Pydantic) | <1ms |
| Entity Extraction | Event payload | Extracted entities list | <2ms |
| Queue Write | Validated event | WAL entry | <1ms |

**Entity Types Extracted (15+):**

* **Code References:** Function signatures, class names, import statements.
* **Error Artifacts:** Stack traces, error codes, exception types.
* **Infrastructure:** IPv4/IPv6, ports, URLs, file paths.
* **Identifiers:** UUIDs, commit hashes, timestamps (ISO 8601).
* **Secrets (Redacted):** API keys, Bearer tokens, connection strings.

**Regex Performance:** Compiled patterns, O(n) scan per event.

### 2.2 SF-V2 (Semantic Compression Engine)

This is the core intelligence layer responsible for **Entropy Reduction**.

**Algorithm Overview:**

1. **INPUT:** Raw event stream $E = [e_1, e_2, ..., e_n]$
2. **CLASSIFY:** Tag as CAUSE, ATTEMPT, FIX, or NOISE.
3. **SCORE:** Calculate Priority $P_i = w_1 \cdot \text{Recency}(e_i) + w_2 \cdot \text{Salience}(e_i) + w_3 \cdot \text{Frequency}(e_i)$.
4. **CONSOLIDATE:** Merge low-$P$ events; preserve High-$P$ entities.
5. **BUDGET:** Trim to max_tokens.
6. **OUTPUT:** Compressed gist $G$.

**Scoring Weights (Configurable):**

* $w_1$ (Recency): 0.4
* $w_2$ (Salience): 0.4
* $w_3$ (Frequency): 0.2

### 2.3 Storage Layer

**Primary Store:** SQLite with WAL mode for non-blocking concurrency.

**Core Schema:**

```sql
CREATE TABLE events (
    id INTEGER PRIMARY KEY,
    event_type TEXT NOT NULL,
    timestamp DATETIME NOT NULL,
    source TEXT NOT NULL,
    project_id TEXT NOT NULL,
    payload JSONB NOT NULL,
    retention_score REAL DEFAULT 0
);

CREATE TABLE entities (
    id INTEGER PRIMARY KEY,
    event_id INTEGER REFERENCES events(id),
    entity_type TEXT NOT NULL,
    value TEXT NOT NULL,
    confidence REAL DEFAULT 1.0
);
```

**Indexes:**

* `idx_events_project_time`: Optimized for time-range queries.
* `idx_entities_type_value`: Optimized for entity lookup.
* **FTS5:** Full-text search on payloads.

**Audit Layer:** `forgetting_ledger.jsonl` (Append-only log of deletions).

## 3. API Specification

### 3.1 Daemon HTTP Endpoints

* `GET /health`: Liveness probe.
* `GET /metrics`: Prometheus-format metrics.
* `POST /context`: Retrieve compressed context.
* `POST /events`: Ingest new event.

**Context Retrieval Example:**

```bash
curl -X POST http://localhost:7777/context \
  -H "Content-Type: application/json" \
  -d '{"audience": "ai", "max_tokens": 4000}'
```

### 3.2 WebSocket Protocol (Sensors)

* **Endpoint:** `ws://localhost:7777/ws`
* **Format:** ViduraiEvent (JSON)

## 4. Deployment & Security

### 4.1 Deployment Options

* **Docker (Recommended):** `chandantochandan/vidurai-daemon:2.0.0`
* **Systemd:** Standard unit file provided.

### 4.2 Security Model

* **Threat Model:** Local-only storage; no outbound network by default.
* **Secret Exposure:** Regex-based PII redaction at ingestion.
* **Audit Tampering:** Append-only JSONL ledger.

## 5. Roadmap

* **v2.1.0 (Q1 2026):** Multi-project sync.
* **v2.2.0 (Q2 2026):** Team mode (optional server component).
* **v3.0.0 (Q4 2026):** ML-based role classification (optional).
