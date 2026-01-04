# Vidurai v2.1.0-Guardian: Architecture & Operations Guide

**Version:** 2.1.0-Guardian
**Date:** 2024-12-15
**Status:** Production Ready

---

## Table of Contents

1. [Overview](#1-overview)
2. [Architecture](#2-architecture)
3. [Installation](#3-installation)
4. [Core Components](#4-core-components)
5. [CLI Commands](#5-cli-commands)
6. [The Memory Lifecycle](#6-the-memory-lifecycle)
7. [VS Code Extension](#7-vs-code-extension)
8. [Verification](#8-verification)
9. [Troubleshooting](#9-troubleshooting)

---

## 1. Overview

Vidurai is a **Local-First Context Infrastructure & Semantic Compression Engine** that provides intelligent memory management for AI-assisted development workflows.

### Philosophy
> "What you focus on persists. What you ignore fades. What fails is forgotten."

### Key Features
- **Three-Kosha Memory Architecture**: Working Memory (hot) → Episodic Memory (warm) → Archived (cold)
- **Smart Forgetting (SF-V2)**: Entropy-aware compression with RL-guided retention
- **Reality Grounding**: Real-time focus tracking and build verification
- **Glass Box Protocol**: Transparent, auditable memory operations

---

## 2. Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         VIDURAI v2.1.0-GUARDIAN                          │
└─────────────────────────────────────────────────────────────────────────┘

                    ┌──────────────────┐
                    │   VS Code Ext    │ ◄── Focus, Terminal, Diagnostics
                    │   (TypeScript)   │
                    └────────┬─────────┘
                             │ IPC (Named Pipe / Unix Socket)
                             ▼
                    ┌──────────────────┐
                    │     Daemon       │ ◄── Event Processing, Oracle API
                    │    (Python)      │
                    └────────┬─────────┘
                             │
        ┌────────────────────┼────────────────────┐
        ▼                    ▼                    ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│ HOT STORAGE   │   │ COLD STORAGE  │   │  RL AGENT     │
│   SQLite      │──▶│   Parquet     │──▶│  Q-Learning   │
│  (Working)    │   │  (Archive)    │   │ (DreamCycle)  │
└───────────────┘   └───────────────┘   └───────────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │     DuckDB       │ ◄── Analytics & Recall
                    │   (RepoAnalyst)  │
                    └──────────────────┘
```

### File Structure

```
vidurai/
├── vidurai/
│   ├── core/
│   │   ├── archival/
│   │   │   └── archiver.py        # MemoryArchiver (SQLite → Parquet)
│   │   ├── analytics/
│   │   │   └── engine.py          # RepoAnalyst (DuckDB queries)
│   │   ├── rl/
│   │   │   └── dreamer.py         # DreamCycle (Offline RL training)
│   │   ├── rl_agent_v2.py         # VismritiRLAgent (Q-Learning)
│   │   ├── state_linker.py        # StateLinker (Focus tracking)
│   │   ├── zombie_killer.py       # ZombieKiller (Error decay)
│   │   ├── code_auditor.py        # CodeAuditor (Build verification)
│   │   ├── retention_judge.py     # RetentionJudge (Access-based decay)
│   │   └── oracle.py              # Oracle API (Context serving)
│   ├── storage/
│   │   └── database.py            # MemoryDatabase (Thread-safe SQLite)
│   ├── retriever/
│   │   └── vidurai_retriever.py   # ViduraiRetriever (LangChain bridge)
│   └── cli.py                     # CLI commands
│
├── vidurai-daemon/
│   ├── daemon.py                  # Main daemon process
│   └── ipc/
│       └── server.py              # IPC server (Named Pipe)
│
├── vidurai-vscode-extension/
│   └── src/
│       ├── extension.ts           # Extension entry point
│       ├── focusWatcher.ts        # Focus event tracking
│       ├── terminalWatcher.ts     # Terminal command tracking
│       ├── diagnosticWatcher.ts   # Error/warning tracking
│       ├── fileWatcher.ts         # File edit tracking
│       └── security/
│           └── Gatekeeper.ts      # PII redaction
│
├── scripts/
│   └── verify_lifecycle.py        # End-to-end verification
│
└── docs/
    ├── PHASE_0_MANIFEST.md        # SearchController, ZombieKiller
    ├── PHASE_1_MANIFEST.md        # Guardian Schema Migration
    ├── PHASE_2_MANIFEST.md        # CodeAuditor, RetentionJudge
    ├── PHASE_3_MANIFEST.md        # StateLinker, ViduraiRetriever
    └── PHASE_4_MANIFEST.md        # Archiver, Analyst, DreamCycle
```

---

## 3. Installation

### Prerequisites

- Python 3.9+
- Node.js 18+ (for VS Code extension)
- VS Code 1.93+ (for shell integration)

### Install Dependencies

```bash
# Clone repository
git clone https://github.com/chandantochandan/vidurai.git
cd vidurai

# Install Python dependencies
pip install -r requirements.txt

# Or install as package
pip install -e .
```

### Required Dependencies (v2.1.0)

| Package | Version | Purpose |
|---------|---------|---------|
| `pandas` | >=2.0.0 | DataFrame operations |
| `pyarrow` | >=14.0.0 | Parquet read/write |
| `duckdb` | >=0.9.0 | Archive analytics |
| `sqlite-vec` | >=0.1.0 | Vector similarity search |
| `sentence-transformers` | >=2.2.0 | Embeddings |
| `loguru` | >=0.7.0 | Structured logging |
| `pydantic` | >=2.0.0 | Data validation |

### Initialize Database

```bash
vidurai init
```

---

## 4. Core Components

### Phase 0: Foundation

| Component | File | Purpose |
|-----------|------|---------|
| **SearchController** | `core/search.py` | Memory retrieval with semantic search |
| **ZombieKiller** | `core/zombie_killer.py` | Decay memories linked to resolved errors |
| **FlightRecorder** | `core/flight_recorder.py` | Audit logging for Glass Box |

### Phase 1: Guardian Schema

Database columns added:
- `status` (ACTIVE, PENDING_DECAY, ARCHIVED)
- `decay_reason` (zombie_killed, retention_failed, etc.)
- `outcome` (-1, 0, 1 for RL signal)
- `pinned` (boolean for user-pinned memories)

### Phase 2: Hygiene System

| Component | File | Purpose |
|-----------|------|---------|
| **CodeAuditor** | `core/code_auditor.py` | Run builds, track success/failure |
| **RetentionJudge** | `core/retention_judge.py` | Decay unaccessed memories |

### Phase 3: Reality Grounding

| Component | File | Purpose |
|-----------|------|---------|
| **StateLinker** | `core/state_linker.py` | Track user focus (file, line, selection) |
| **ViduraiRetriever** | `retriever/vidurai_retriever.py` | LangChain integration |

### Phase 4: The Awakening

| Component | File | Purpose |
|-----------|------|---------|
| **MemoryArchiver** | `core/archival/archiver.py` | SQLite → Parquet migration |
| **RepoAnalyst** | `core/analytics/engine.py` | DuckDB queries on archive |
| **DreamCycle** | `core/rl/dreamer.py` | Offline RL training |

---

## 5. CLI Commands

### Memory Hygiene

```bash
# Run full hygiene cycle (ZombieKiller + RetentionJudge)
vidurai hygiene

# With retention threshold (days)
vidurai hygiene --retention-days 7

# Dry run (no changes)
vidurai hygiene --dry-run
```

### Code Audit

```bash
# Run build and mark memories based on result
vidurai audit

# Custom build command
vidurai audit --command "npm test"

# Specify project path
vidurai audit --path /path/to/project
```

### Archive Operations

```bash
# Flush archived memories to Parquet
python -m vidurai.core.archival.archiver --flush

# Show archive statistics
python -m vidurai.core.archival.archiver --stats

# Query archive via DuckDB
python -m vidurai.core.analytics.engine --query "SELECT COUNT(*) FROM history"
```

### Dream Cycle (RL Training)

```bash
# Run offline training
python -m vidurai.core.rl.dreamer --run

# Test without modifying
python -m vidurai.core.rl.dreamer --test
```

---

## 6. The Memory Lifecycle

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          MEMORY LIFECYCLE                                │
└─────────────────────────────────────────────────────────────────────────┘

    CREATE ──▶ ACTIVE ──▶ [triggers] ──▶ PENDING_DECAY ──▶ ARCHIVED
                │                              │
                │ (ZombieKiller)               │ (MemoryArchiver)
                │ (RetentionJudge)             │
                │ (CodeAuditor)                ▼
                │                    ┌──────────────────┐
                └────────────────────│  SQLite (Hot)    │
                                     │  status='ARCHIVED'│
                                     └────────┬─────────┘
                                              │ 24h interval
                                              ▼
                                     ┌──────────────────┐
                                     │  Parquet (Cold)  │
                                     │  year=YYYY/      │
                                     │  month=MM/       │
                                     └────────┬─────────┘
                                              │
                                              ▼
                                     ┌──────────────────┐
                                     │  DreamCycle      │
                                     │  (RL Training)   │
                                     └──────────────────┘
```

### Decay Triggers

| Trigger | Component | Condition |
|---------|-----------|-----------|
| Error Resolved | ZombieKiller | Linked error no longer in diagnostics |
| Build Success | CodeAuditor | Error memory + build passes |
| Unused | RetentionJudge | No access in N days |
| Low Salience | RetentionJudge | Below threshold + low access |

---

## 7. VS Code Extension

### Features

- **File Watcher**: Tracks file edits with debouncing
- **Focus Watcher**: Tracks cursor position (500ms debounce)
- **Terminal Watcher**: Tracks commands via shell integration
- **Diagnostic Watcher**: Tracks errors/warnings
- **Pin Decorator**: Visual indicator for pinned files
- **Context Panel**: Glass Box dashboard

### Security (Gatekeeper)

All data is sanitized before leaving the extension:
- API keys (OpenAI, Anthropic, AWS, GitHub, etc.)
- Private keys (RSA, SSH, PGP)
- Database URLs
- PII (email, phone, SSN, IP addresses)

### Commands

| Command | Description |
|---------|-------------|
| `Vidurai: Copy Context` | Copy memories to clipboard |
| `Vidurai: Pin File` | Pin current file to context |
| `Vidurai: Unpin File` | Unpin current file |
| `Vidurai: Generate Standup` | Generate manager report |
| `Vidurai: Reconnect` | Reconnect to daemon |

---

## 8. Verification

### The First Breath Test

Run the end-to-end lifecycle verification:

```bash
python scripts/verify_lifecycle.py
```

This tests:
1. **Birth**: Insert test memory into SQLite
2. **Purgatory**: Archive via MemoryArchiver
3. **Recall**: Query via RepoAnalyst (DuckDB)
4. **Dreaming**: Train via DreamCycle
5. **Cleanup**: Remove test data (Leave No Trace)

Expected output:
```
============================================================
  VERIFICATION RESULTS
============================================================
  ✅ PASS: Birth
  ✅ PASS: Purgatory
  ✅ PASS: Recall
  ✅ PASS: Dreaming
  ✅ PASS: Cleanup
============================================================

  🚀 VIDURAI 2.1.0 GUARDIAN IS OPERATIONAL 🚀
```

### IPC Protocol Test

Test daemon communication:

```bash
python -m tests.test_phase5_ipc
```

---

## 9. Troubleshooting

### Common Issues

**Database not found**
```bash
vidurai init
```

**DuckDB not installed**
```bash
pip install duckdb>=0.9.0
```

**Daemon not running**
```bash
python vidurai-daemon/daemon.py
```

**VS Code extension not connecting**
- Check daemon is running
- Check socket path: `~/.vidurai/vidurai-{user}.sock` (Unix) or `\\.\pipe\vidurai-{user}` (Windows)

### Log Locations

| Component | Log Path |
|-----------|----------|
| Daemon | stdout (use `loguru` format) |
| VS Code | Output Panel → "Vidurai" |
| Database | `~/.vidurai/vidurai.db` |
| Archive | `~/.vidurai/archive/` |

### Glass Box Protocol

All operations are auditable:
- Every memory state change is logged
- Every decay has a `decay_reason`
- Every RL decision has an `outcome` signal

---

## Appendix: Phase Manifests

For detailed implementation notes, see:
- `docs/PHASE_0_MANIFEST.md` - SearchController, ZombieKiller, FlightRecorder
- `docs/PHASE_1_MANIFEST.md` - Guardian Schema Migration
- `docs/PHASE_2_MANIFEST.md` - CodeAuditor, RetentionJudge
- `docs/PHASE_3_MANIFEST.md` - StateLinker, ViduraiRetriever
- `docs/PHASE_4_MANIFEST.md` - MemoryArchiver, RepoAnalyst, DreamCycle

---

*Generated by Vidurai Guardian v2.1.0*
