# Contributing to Vidurai

First off, thank you for considering contributing to Vidurai! 🙏

**विस्मृति भी विद्या है** — *"Forgetting too is knowledge"*

This document provides guidelines for contributing to the Vidurai project. Following these guidelines helps maintain code quality and makes the contribution process smooth for everyone.

---

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How Can I Contribute?](#how-can-i-contribute)
- [Development Setup](#development-setup)
- [Pull Request Process](#pull-request-process)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)
- [Documentation](#documentation)
- [Community](#community)

---

## 📜 Code of Conduct

### Our Pledge

We are committed to providing a welcoming and inclusive environment for all contributors, regardless of:
- Experience level
- Gender identity and expression
- Sexual orientation
- Disability
- Personal appearance
- Body size
- Race or ethnicity
- Age
- Religion or lack thereof
- Nationality

### Expected Behavior

- Be respectful and constructive
- Use welcoming and inclusive language
- Accept constructive criticism gracefully
- Focus on what's best for the community
- Show empathy towards others

### Unacceptable Behavior

- Harassment or discriminatory language
- Trolling or insulting comments
- Personal or political attacks
- Public or private harassment
- Publishing others' private information

**Violations:** Report to contact@vidurai.ai

---

## 🤝 How Can I Contribute?

### 1. Reporting Bugs

**Before submitting:**
- Check [existing issues](https://github.com/chandantochandan/vidurai-vscode-extension/issues)
- Verify bug in latest version
- Collect relevant information

**Bug Report Should Include:**
- Clear, descriptive title
- Exact steps to reproduce
- Expected vs actual behavior
- Screenshots/logs (if applicable)
- Environment details:
 - OS and version
 - VS Code version
 - Python version
 - Vidurai version

**Template:**
```markdown
**Description:**
Brief description of the bug

**Steps to Reproduce:**
1. Open VS Code
2. Install Vidurai
3. [Specific actions]
4. Observe error

**Expected Behavior:**
What should happen

**Actual Behavior:**
What actually happens

**Environment:**
- OS: Windows 11
- VS Code: 1.84.0
- Python: 3.11.0
- Vidurai: 0.1.0

**Logs:**
[Paste from Output panel]
```

### 2. Suggesting Features

**Feature Request Should Include:**
- Clear use case (why is this needed?)
- Proposed implementation (optional)
- Alternative solutions considered
- Impact on existing features

**Template:**
```markdown
**Use Case:**
As a [user type], I want [feature] so that [benefit].

**Proposed Solution:**
[Your idea for implementing this]

**Alternatives Considered:**
[Other approaches you thought about]

**Additional Context:**
[Any other relevant information]
```

### 3. Code Contributions

We welcome contributions in these areas:

**High Priority:**
- 🐛 Bug fixes
- 📊 Performance optimizations
- Security improvements
- 📝 Documentation improvements
- Test coverage

**Medium Priority:**
- Feature implementations (from roadmap)
- 🎨 UI/UX improvements
- 🌐 Internationalization (i18n)

**Low Priority:**
- 🧹 Code cleanup/refactoring
- 🔬 Experimental features

---

## 🛠️ Development Setup

### Prerequisites

**Required:**
- Git
- Node.js 18+ and npm
- Python 3.8+
- VS Code 1.80.0+

**Recommended:**
- VS Code Extensions:
 - ESLint
 - Prettier
 - Python
 - EditorConfig

### Fork and Clone

```bash
# 1. Fork repository on GitHub

# 2. Clone your fork
git clone https://github.com/YOUR_USERNAME/vidurai-vscode-extension.git
cd vidurai-vscode-extension

# 3. Add upstream remote
git remote add upstream https://github.com/chandantochandan/vidurai-vscode-extension.git

# 4. Create feature branch
git checkout -b feature/your-feature-name
```

### Setup VS Code Extension

```bash
cd vidurai-vscode-extension

# Install dependencies
npm install

# Install Python bridge dependencies
cd python-bridge
python -m venv .venv
source .venv/bin/activate # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install pytest # For testing

# Return to extension root
cd ..
```

### Setup Vidurai SDK (if contributing to core)

```bash
cd vidurai # Main SDK directory

# Install in editable mode
pip install -e .

# Install development dependencies
pip install pytest pytest-cov black flake8 mypy
```

### Run Extension in Development Mode

```bash
# In VS Code:
# 1. Open vidurai-vscode-extension/ folder
# 2. Press F5 (or Run > Start Debugging)
# 3. Extension Development Host window opens
# 4. Test your changes
```

### Run Tests

**TypeScript Tests:**
```bash
cd vidurai-vscode-extension
npm test
```

**Python Bridge Tests:**
```bash
cd vidurai-vscode-extension/python-bridge
pytest test_bridge.py -v
```

**Vidurai SDK Tests:**
```bash
cd vidurai
pytest tests/ -v --cov=vidurai
```

---

## 🔄 Pull Request Process

### 1. Before You Start

- **Check roadmap:** Is your feature planned?
- **Open an issue first:** Discuss large changes
- **One feature per PR:** Keep PRs focused

### 2. Development Workflow

```bash
# 1. Sync with upstream
git fetch upstream
git rebase upstream/main

# 2. Make your changes
# [Write code, tests, docs]

# 3. Run tests
npm test # TypeScript
pytest # Python

# 4. Format code
npm run format # TypeScript
black . # Python

# 5. Commit with meaningful message
git commit -m "feat: add memory ledger UI component"

# 6. Push to your fork
git push origin feature/your-feature-name
```

### 3. Commit Message Convention

We follow [Conventional Commits](https://www.conventionalcommits.org/):

**Format:**
```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation only
- `style:` Code style (formatting, no logic change)
- `refactor:` Code restructuring (no feature/bug change)
- `perf:` Performance improvement
- `test:` Adding tests
- `chore:` Build/tooling changes

**Examples:**
```
feat(bridge): add automatic secrets detection

Implements regex patterns for API keys, passwords, and tokens.
Automatically redacts sensitive data before storing in memory.

Closes #42

---

fix(extension): resolve bridge timeout on slow machines

Increases timeout from 10s to 30s to accommodate slower Python initialization.

Fixes #38

---

docs(readme): update installation instructions

Adds troubleshooting section for common Python path issues.
```

### 4. Create Pull Request

**PR Title:** Same as commit message (if single commit) or summary

**PR Description Template:**
```markdown
## Description
Brief description of changes

## Motivation
Why is this change needed?

## Changes Made
- Change 1
- Change 2
- Change 3

## Testing
- [ ] Unit tests added/updated
- [ ] Manual testing completed
- [ ] All tests passing

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-reviewed code
- [ ] Commented complex sections
- [ ] Updated documentation
- [ ] No breaking changes (or documented)
- [ ] Added tests (if applicable)

## Related Issues
Closes #123
Fixes #456
```

### 5. Review Process

**What to Expect:**
- Initial review within 48-72 hours
- Feedback or requested changes
- Approval once all concerns addressed
- Merge by maintainer

**During Review:**
- Be patient and respectful
- Respond to feedback promptly
- Make requested changes
- Push updates to same branch

### 6. After Merge

```bash
# 1. Delete feature branch
git branch -d feature/your-feature-name
git push origin --delete feature/your-feature-name

# 2. Sync with upstream
git checkout main
git pull upstream main

# 3. Celebrate! 🎉
```

---

## 💻 Coding Standards

### TypeScript (VS Code Extension)

**Style Guide:**
- Use Prettier (config in `.prettierrc`)
- Use ESLint (config in `.eslintrc`)
- 2-space indentation
- Single quotes for strings
- Semicolons required

**Best Practices:**
```typescript
// Good: Explicit types
function processEvent(event: CodeEvent): Promise<Response> {
 // ...
}

// Bad: Implicit any
function processEvent(event) {
 // ...
}

// Good: Async/await
async function fetchData() {
 const result = await api.call();
 return result;
}

// Bad: Promise chains
function fetchData() {
 return api.call().then(result => result);
}
```

### Python (Bridge & SDK)

**Style Guide:**
- PEP 8 compliance
- Use Black formatter (line length: 100)
- Type hints required
- Docstrings for public functions

**Best Practices:**
```python
# Good: Type hints and docstring
def classify_event(event: dict) -> SalienceLevel:
 """
 Classify event by salience level.

 Args:
 event: Event dictionary with type and metadata

 Returns:
 SalienceLevel enum (CRITICAL, HIGH, MEDIUM, LOW, NOISE)
 """
 # ...

# Bad: No types or documentation
def classify_event(event):
 # ...

# Good: Specific exception handling
try:
 result = process_data(data)
except ValueError as e:
 logger.error(f"Invalid data: {e}")

# Bad: Bare except
try:
 result = process_data(data)
except:
 pass
```

### Naming Conventions

**TypeScript:**
- Classes: `PascalCase` (e.g., `MemoryManager`)
- Functions/variables: `camelCase` (e.g., `getUserData`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `MAX_RETRIES`)
- Interfaces: `PascalCase` with `I` prefix (e.g., `IConfig`)

**Python:**
- Classes: `PascalCase` (e.g., `VismritiMemory`)
- Functions/variables: `snake_case` (e.g., `get_user_data`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `MAX_RETRIES`)
- Private: `_leading_underscore` (e.g., `_internal_method`)

---

## Testing Guidelines

### Test Coverage Requirements

- **Minimum:** 80% code coverage
- **Target:** 90% code coverage
- **Critical paths:** 100% coverage

### Writing Tests

**TypeScript (Jest):**
```typescript
describe('PythonBridge', () => {
 test('spawns bridge successfully', async () => {
 const bridge = await spawnBridge();
 expect(bridge.pid).toBeDefined();
 bridge.kill();
 });

 test('handles bridge timeout', async () => {
 await expect(sendToBridge({...}, 100))
 .rejects
 .toThrow('Timeout');
 });
});
```

**Python (pytest):**
```python
def test_salience_classification():
 """Test salience rules for different event types"""
 # Error diagnostic should be CRITICAL
 event = {'type': 'diagnostic', 'severity': 'error'}
 assert classify_event(event) == SalienceLevel.CRITICAL

 # Test file edit should be HIGH
 event = {'type': 'file_edit', 'file': 'test_main.py'}
 assert classify_event(event) == SalienceLevel.HIGH
```

### Running Tests Locally

```bash
# Run all tests
npm test && pytest

# Run with coverage
npm test -- --coverage
pytest --cov=vidurai --cov-report=html

# Run specific test file
npm test -- extension.test.ts
pytest test_bridge.py

# Watch mode (auto-rerun on change)
npm test -- --watch
pytest-watch
```

---

## 📝 Documentation

### Code Documentation

**TypeScript:**
- JSDoc comments for public functions
- Inline comments for complex logic
- README for each major module

**Python:**
- Docstrings (Google style) for all public functions
- Type hints required
- Module-level docstrings

**Example:**
```python
def extract_gist(event: dict, use_llm: bool = False) -> str:
 """
 Extract semantic gist from code event.

 Uses rule-based patterns by default, optionally uses LLM
 for more accurate extraction.

 Args:
 event: Event dictionary containing type, file, content
 use_llm: Whether to use LLM-based extraction

 Returns:
 String gist summarizing the event semantically

 Raises:
 ValueError: If event type is unsupported

 Examples:
 >>> event = {'type': 'file_edit', 'file': 'test.py'}
 >>> extract_gist(event)
 'Modified test file: test.py'
 """
 # Implementation
```

### User Documentation

**When to Update:**
- New features → Update README.md
- Changed behavior → Update docs/ folder
- Bug fixes → Update CHANGELOG.md
- Breaking changes → Migration guide

**Documentation Structure:**
```
docs/
├── installation.md # Setup instructions
├── quick-start.md # 5-minute tutorial
├── configuration.md # All settings explained
├── architecture.md # System design
├── api-reference.md # Public API docs
├── troubleshooting.md # Common issues
└── case-studies/ # Real-world examples
```

---

## 🌍 Community

### Communication Channels

**GitHub:**
- [Issues](https://github.com/chandantochandan/vidurai-vscode-extension/issues) - Bug reports, feature requests
- [Discussions](https://github.com/chandantochandan/vidurai-vscode-extension/discussions) - Q&A, ideas
- [Pull Requests](https://github.com/chandantochandan/vidurai-vscode-extension/pulls) - Code contributions

**Discord** (coming soon):
- `#general` - Community chat
- `#support` - Help requests
- `#contributors` - Development discussions
- `#announcements` - Release updates

**Social:**
- Twitter: [@yvidurai](https://x.com/yvidurai)
- Website: [vidurai.ai](https://vidurai.ai) (coming soon)

### Getting Help

**For Users:**
- Check [documentation](https://github.com/chandantochandan/vidurai-vscode-extension#readme)
- Search [existing issues](https://github.com/chandantochandan/vidurai-vscode-extension/issues)
- Ask in [Discussions](https://github.com/chandantochandan/vidurai-vscode-extension/discussions)

**For Contributors:**
- Read this guide thoroughly
- Join Discord `#contributors` channel
- Tag maintainers in PR comments

### Recognition

**Contributors will be:**
- Listed in README.md
- Mentioned in release notes
- Added to CONTRIBUTORS.md (if significant contribution)
- Given credit in related blog posts/talks

**Significant Contributions:**
- 3+ merged PRs
- Major feature implementation
- Substantial documentation improvements
- Active community support

---

## 🏆 Types of Contributors We Value

### Code Contributors
- Bug fixes
- Feature implementations
- Performance optimizations
- Test coverage improvements

### Documentation Contributors
- README improvements
- Tutorial creation
- API documentation
- Translation (future)

### Community Contributors
- Answering questions in Discussions
- Triaging issues
- Creating examples/templates
- Evangelizing Vidurai

### Design Contributors
- UI/UX improvements
- Icon/logo design
- Demo videos/GIFs
- Screenshot creation

**All contributions are valued equally!** 🙏

---

## ❓ FAQ

**Q: I'm new to open source. Can I contribute?**
A: Absolutely! Look for issues labeled `good first issue` or `help wanted`.

**Q: How long until my PR is reviewed?**
A: Usually 48-72 hours. Large PRs may take longer.

**Q: Can I work on an issue that's assigned?**
A: Please ask first. It may be actively worked on.

**Q: My PR was rejected. Why?**
A: Check feedback comments. Common reasons: doesn't align with roadmap, needs tests, code quality issues.

**Q: Can I get paid for contributions?**
A: Not currently. This is a community-driven open source project.

**Q: I have a great feature idea!**
A: Open a Discussion first to gauge interest before implementing.

---

## 📄 License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

## 🙏 Thank You!

Every contribution, no matter how small, makes Vidurai better for everyone.

**विस्मृति भी विद्या है** — *"Forgetting too is knowledge"*

**जय विदुराई!** 🕉️

---

**Questions?** Open a [Discussion](https://github.com/chandantochandan/vidurai-vscode-extension/discussions) or email contact@vidurai.ai
