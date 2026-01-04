# Phase 2 Manifest: The Constitution (Safety & Retention)

**Version:** 2.1.0-Guardian
**Date:** 2024-12-15
**Status:** IMPLEMENTED

---

## 1. Overview

Phase 2 implements "The Constitution" - the laws governing memory safety and retention:
- **CodeAuditor:** Static analysis for security risks
- **RetentionJudge:** Utility-based memory decay decisions
- **Hygiene Command:** User interface for the Purgatory Protocol

---

## 2. The Auditor (Static Safety)

### File Location
`vidurai/core/verification/auditor.py`

### Denylist (Python)

#### Banned Imports
```
commands    # Deprecated shell commands
ctypes      # C interface (memory manipulation)
marshal     # Code serialization
os          # Operating system interface
pickle      # Arbitrary code execution
pty         # Pseudo-terminal
shutil      # File operations
socket      # Network access
subprocess  # Process spawning
sys         # System interface
```

#### Banned Function Calls
```
os.exec*          # All exec variants
os.popen
os.remove
os.rmdir
os.spawn*         # All spawn variants
os.system
os.unlink
shutil.copy
shutil.copy2
shutil.move
shutil.rmtree
subprocess.call
subprocess.check_call
subprocess.check_output
subprocess.Popen
subprocess.run
```

#### Banned Builtins
```
__import__
compile
eval
exec
input
open          # File operations (write context)
```

### Glass Box Protocol: Safe Parsing

```python
# ALWAYS wrap ast.parse in try/except
try:
    tree = ast.parse(code)
except SyntaxError as e:
    return [f"Syntax Error: {e.msg} (line {e.lineno})"]
except Exception as e:
    return [f"Parse Error: {str(e)}"]
```

**Why:** `ast.parse()` crashes on invalid syntax. Crashing the daemon is unacceptable.

---

## 3. The Constitution (RetentionJudge)

### File Location
`vidurai/core/constitution/retention.py`

### The Laws

#### Law 1: Immunity Clause (Absolute Veto)
```python
if memory_row.get('pinned') == 1:
    return 'ACTIVE'  # NEVER decay pinned memories
```

#### Law 2: Utility Score Formula

```
Utility Score = (0.4 * access_score) + (0.4 * recency_score) + (0.2 * outcome_score)

Where:
  access_score  = log(access_count + 1)     # Diminishing returns
  recency_score = 1 / (days_since_creation + 1)  # Newer = higher
  outcome_score = outcome                    # -1, 0, or 1 (RL signal)
```

**Weight Justification:**
- **Access (40%):** Frequently accessed memories are valuable
- **Recency (40%):** Recent context is more relevant
- **Outcome (20%):** RL signal influences but doesn't dominate

#### Law 3: Decay Threshold

```python
DECAY_THRESHOLD = 0.15

if total_score < DECAY_THRESHOLD:
    return 'PENDING_DECAY'
else:
    return 'ACTIVE'
```

### Math Clarity (Division by Zero Protection)

```python
# access_count + 1 prevents log(0)
access_score = math.log(access_count + 1)

# days_since_creation + 1 prevents division by zero
recency_score = 1.0 / (days_since_creation + 1)
```

---

## 4. The Hygiene Interface

### CLI Command
```bash
vidurai hygiene [--project PATH] [--force]
```

### User Flow (Purgatory Protocol)

1. **Evaluate:** Calculate utility scores for all ACTIVE memories
2. **Mark:** Set status='PENDING_DECAY' for low-utility memories
3. **Review:** User sees count and chooses action
4. **Execute:**
   - **Archive [y]:** `UPDATE SET status='ARCHIVED'`
   - **Mercy [n]:** `UPDATE SET status='ACTIVE', access_count=access_count+1`
   - **Quit [q]:** Leave as PENDING_DECAY for later

### Example Output
```
🧹 Running memory hygiene check...

📊 Evaluation Results:
   Active:        42
   Immune (📌):   5
   Pending Decay: 8

🗑️  Found 8 memories marked for decay (Low Utility).

What would you like to do?
  [y] Archive these memories (remove from active context)
  [n] Grant mercy (bump access count, keep active)
  [q] Quit (leave as PENDING_DECAY for later)
Your choice [q]:
```

---

## 5. Verification Commands

### Test CodeAuditor
```bash
# Run test cases
python -m vidurai.core.verification.auditor --test

# Show denylist
python -m vidurai.core.verification.auditor --denylist

# Audit a file
python -m vidurai.core.verification.auditor --file /path/to/script.py
```

### Test RetentionJudge
```bash
# Run test cases
python -m vidurai.core.constitution.retention --test

# Show statistics
python -m vidurai.core.constitution.retention --stats

# Evaluate all memories
python -m vidurai.core.constitution.retention --evaluate
```

### CLI Commands
```bash
# Run hygiene check
vidurai hygiene

# Audit code
vidurai audit "import os; os.system('ls')"
vidurai audit -f /path/to/script.py
```

---

## 6. Database Schema (Updated)

### Status Values
| Status | Meaning |
|--------|---------|
| `ACTIVE` | Normal, in active context |
| `PENDING_DECAY` | Marked for decay, awaiting user review |
| `ARCHIVED` | Removed from active context |
| `DECAYED` | Permanently removed |

### Memory Lifecycle
```
CREATE → ACTIVE → [low utility] → PENDING_DECAY → ARCHIVED
                                               ↓
                                         [user mercy] → ACTIVE (access_count++)
```

---

## 7. Architecture

### File Structure
```
vidurai/
├── core/
│   ├── verification/
│   │   ├── __init__.py
│   │   └── auditor.py        # CodeAuditor
│   │
│   └── constitution/
│       ├── __init__.py
│       └── retention.py      # RetentionJudge
│
└── cli.py                    # hygiene, audit commands
```

### Dependencies
- **ast:** Python standard library (no external deps)
- **math:** Python standard library
- **sqlite3:** Python standard library

---

## 8. Caveats & Limitations

### CodeAuditor
1. **Python only:** Other languages return `[]` (skipped)
2. **Static analysis:** Cannot detect runtime-constructed dangerous calls
3. **Denylist-based:** May miss new dangerous patterns

### RetentionJudge
1. **Requires user consent:** Purgatory Protocol requires user review
2. **Immunity is absolute:** Pinned memories cannot be decayed even if score is low
3. **Formula may need tuning:** Weights (0.4/0.4/0.2) are configurable constants

### Hygiene Command
1. **Non-destructive default:** Quit leaves memories unchanged
2. **Mercy bumps access_count:** May artificially inflate access scores
3. **Project filter not yet wired:** Currently evaluates all memories

---

## 9. Next Steps (Phase 3)

1. **State Linker:** Connect VS Code/Beacon signals to file paths
2. **Build Runner:** Execute builds in Shadow Sandbox
3. **RL Dream Cycle:** Offline batch training on Parquet archives

---

*Generated by Vidurai Guardian v2.1.0*
