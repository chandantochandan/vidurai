# Vidurai Shell Integration Scripts

This directory contains shell scripts for integrating Vidurai with Claude Code.

## 📋 Contents

- **`vidurai-claude`** - Shell wrapper for Claude Code with automatic context injection
- **`install.sh`** - Installation script for shell integration

---

## 🚀 Quick Start

### 1. Install Shell Integration

```bash
cd /path/to/vidurai
./scripts/install.sh
```

This will:
- Copy `vidurai-claude` to `~/.vidurai/bin/`
- Add `~/.vidurai/bin/` to your PATH
- Create `vclaude` alias

### 2. Activate

```bash
source ~/.bashrc  # or ~/.zshrc
```

### 3. Use It!

```bash
# Full command
vidurai-claude "What bugs did I fix today?"

# Short alias
vclaude "How does authentication work in this project?"
```

---

## 📖 Usage

### vidurai-claude

**Purpose:** Wrapper around Claude Code that automatically injects project context from Vidurai's memory database.

**Syntax:**
```bash
vidurai-claude "your question here"
```

**What It Does:**
1. Checks if `claude` command is installed
2. Retrieves project context from Vidurai database
3. Combines context with your question
4. Calls Claude Code with enhanced prompt

**Example:**
```bash
$ vidurai-claude "What are the recent changes in auth.py?"
🧠 Vidurai: Retrieving project context...
✓ Retrieved 12 lines of project context

[Claude Code responds with context-aware answer]
```

**Requirements:**
- Claude Code installed (`claude` command available)
- Vidurai SDK installed (`pip install vidurai`)
- VS Code extension running (to populate memories)

---

## 🔧 Advanced Usage

### Custom Query

The wrapper uses your question as a query to filter relevant memories:

```bash
# Get context about authentication
vclaude "How does user authentication work?"

# Get context about recent bugs
vclaude "What bugs did I fix in the last week?"

# Get context about a specific file
vclaude "Explain the changes in database.py"
```

### No Context Available

If Vidurai hasn't captured any relevant memories yet:

```
ℹ️  No project context found. Running Claude without Vidurai...
```

Claude Code will still work, just without project-specific context.

---

## 🛠️ Troubleshooting

### Error: 'claude' command not found

**Problem:** Claude Code is not installed.

**Solution:**
```bash
# Visit: https://docs.claude.com/claude-code
# Install Claude Code, then try again
```

### Error: Vidurai SDK not found

**Problem:** Vidurai Python package is not installed.

**Solution:**
```bash
pip install vidurai
```

The script will also attempt to auto-install if missing.

### No Context Retrieved

**Problem:** VS Code extension hasn't captured any memories yet.

**Solutions:**
1. Make sure the Vidurai VS Code extension is running
2. Edit some files, run some commands
3. Wait a few minutes for memories to be captured
4. Check the TreeView in VS Code sidebar

### Shell Not Supported

**Problem:** Using Fish or another shell not auto-detected.

**Solution:** Add manually to your config:
```fish
# Fish shell (~/.config/fish/config.fish)
set -gx PATH $HOME/.vidurai/bin $PATH
alias vclaude='vidurai-claude'
```

---

## 📝 How It Works

### Context Injection Flow

```
1. User runs: vclaude "question"
   ↓
2. Wrapper calls: memory.get_context_for_ai(query="question")
   ↓
3. Database returns formatted markdown:
   # VIDURAI PROJECT CONTEXT

   Project: my-project

   ## CRITICAL Priority Memories
   - **Fixed auth bug in login.py**
     - File: `auth/login.py`
     - Age: 2 days ago
   ↓
4. Wrapper combines: CONTEXT + "---" + USER QUESTION
   ↓
5. Calls: claude "FULL_PROMPT"
```

### Context Format

The injected context is formatted as markdown:

```markdown
# VIDURAI PROJECT CONTEXT

Project: my-project

## CRITICAL Priority Memories
- **Memory 1 gist**
  - File: `path/to/file.py`
  - Age: 2 days ago

- **Memory 2 gist**
  - File: `path/to/other.py`
  - Age: 5 days ago

## HIGH Priority Memories
- **Memory 3 gist**
  - File: `path/to/file.js`
  - Age: 1 day ago

---

USER QUESTION:
[Your question here]
```

---

## 🎯 Use Cases

### 1. Understanding Recent Changes
```bash
vclaude "What changed in the authentication system this week?"
```

### 2. Debugging
```bash
vclaude "What errors did I see in the terminal today?"
```

### 3. Code Review
```bash
vclaude "Review the changes I made to the API endpoints"
```

### 4. Documentation
```bash
vclaude "Write documentation for the new user registration flow"
```

### 5. Refactoring Guidance
```bash
vclaude "How should I refactor the database connection logic?"
```

---

## 🔐 Privacy & Security

- **Local Only:** All context is stored in `~/.vidurai/memory.db` on your machine
- **No Cloud:** Nothing is sent to external services except Claude Code
- **Selective:** Only relevant memories are included (max ~2000 tokens)
- **Transparent:** You can inspect memories in VS Code TreeView

---

## 🤝 Contributing

Found a bug or want to improve the wrapper?

1. Edit `scripts/vidurai-claude`
2. Test your changes
3. Submit a PR to the main repo

---

## 📄 License

MIT License - See main repo LICENSE file

---

**जय विदुराई! 🕉️**
