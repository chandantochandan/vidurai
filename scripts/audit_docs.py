#!/usr/bin/env python3
"""
The Forensic Auditor - Documentation Health Scanner

Scans the repository for documentation files and identifies:
- Exact duplicates (same content hash)
- Potential obsolete files (v1, phase, draft, temp in name)
- Similar filenames that may be redundant
- Files not in the official documentation manifest

Usage:
    python scripts/audit_docs.py

@version 2.2.0
"""

import hashlib
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from collections import defaultdict


@dataclass
class DocFile:
    """Represents a documentation file."""
    path: Path
    title: str = ""
    content_hash: str = ""
    size_bytes: int = 0
    status: str = "UNKNOWN"
    similarity_note: str = ""

    @property
    def relative_path(self) -> str:
        """Get path relative to project root."""
        try:
            return str(self.path.relative_to(PROJECT_ROOT))
        except ValueError:
            return str(self.path)


# Project root
PROJECT_ROOT = Path(__file__).parent.parent

# Official documentation manifest (Ground Truth)
OFFICIAL_DOCS = {
    "README.md",
    "CONTRIBUTING.md",
    "CHANGELOG.md",
    "LICENSE",
    "BRAND.md",
    "AGENTS.md",
    "docs/CLI.md",
    "docs/SECURITY.md",
    "docs/TROUBLESHOOTING.md",
    "docs/MCP_SERVER.md",
    "docs/MAINTENANCE_MODE.md",
    "docs/PHASE_1.5_MANIFEST.md",
    "docs/PHASE_2_MANIFEST.md",
    "docs/PHASE_3_MANIFEST.md",
    "docs/PHASE_4_MANIFEST.md",
}

# Patterns indicating obsolete files
OBSOLETE_PATTERNS = [
    r'_v1[._]',
    r'_v0[._]',
    r'_draft',
    r'_temp',
    r'_old',
    r'_backup',
    r'\.bak$',
    r'_WIP',
    r'DEPRECATED',
]

# Directories to skip
SKIP_DIRS = {
    '.git',
    '.venv',
    'venv',
    '__pycache__',
    'node_modules',
    '.mypy_cache',
    '.pytest_cache',
    'dist',
    'build',
    '*.egg-info',
}


def should_skip_dir(dir_path: Path) -> bool:
    """Check if directory should be skipped."""
    name = dir_path.name
    for pattern in SKIP_DIRS:
        if pattern.startswith('*'):
            if name.endswith(pattern[1:]):
                return True
        elif name == pattern:
            return True
    return False


def compute_hash(content: str) -> str:
    """Compute MD5 hash of content."""
    return hashlib.md5(content.encode('utf-8', errors='replace')).hexdigest()


def extract_title(content: str) -> str:
    """Extract the first non-empty line as title."""
    for line in content.split('\n'):
        line = line.strip()
        if line:
            # Remove markdown headers
            line = re.sub(r'^#+\s*', '', line)
            # Truncate long titles
            if len(line) > 60:
                line = line[:57] + '...'
            return line
    return "(Empty file)"


def is_obsolete(filename: str) -> bool:
    """Check if filename matches obsolete patterns."""
    for pattern in OBSOLETE_PATTERNS:
        if re.search(pattern, filename, re.IGNORECASE):
            return True
    return False


def find_doc_files(root: Path) -> List[DocFile]:
    """Find all documentation files in the project."""
    doc_files = []
    extensions = {'.md', '.txt', '.rst'}

    for path in root.rglob('*'):
        # Skip directories
        if path.is_dir():
            continue

        # Skip files in excluded directories
        skip = False
        for parent in path.parents:
            if should_skip_dir(parent):
                skip = True
                break
        if skip:
            continue

        # Check extension
        if path.suffix.lower() not in extensions:
            continue

        # Skip archive directory (already archived)
        if 'archive' in str(path).lower():
            continue

        doc_files.append(DocFile(path=path))

    return doc_files


def analyze_file(doc: DocFile) -> None:
    """Analyze a single documentation file."""
    try:
        content = doc.path.read_text(encoding='utf-8', errors='replace')
        doc.content_hash = compute_hash(content)
        doc.title = extract_title(content)
        doc.size_bytes = doc.path.stat().st_size
    except Exception as e:
        doc.title = f"(Error: {e})"
        doc.content_hash = ""


def find_duplicates(docs: List[DocFile]) -> Dict[str, List[DocFile]]:
    """Find files with identical content."""
    hash_groups = defaultdict(list)
    for doc in docs:
        if doc.content_hash:
            hash_groups[doc.content_hash].append(doc)

    # Return only groups with duplicates
    return {h: files for h, files in hash_groups.items() if len(files) > 1}


def find_similar_names(docs: List[DocFile]) -> List[Tuple[DocFile, DocFile, float]]:
    """Find files with similar names."""
    similar = []

    for i, doc1 in enumerate(docs):
        name1 = doc1.path.stem.lower().replace('_', '').replace('-', '')
        for doc2 in docs[i+1:]:
            name2 = doc2.path.stem.lower().replace('_', '').replace('-', '')

            # Check if one name contains the other
            if name1 in name2 or name2 in name1:
                # Calculate similarity score
                longer = max(len(name1), len(name2))
                shorter = min(len(name1), len(name2))
                score = shorter / longer if longer > 0 else 0

                if score > 0.5:  # More than 50% overlap
                    similar.append((doc1, doc2, score))

    return similar


def classify_docs(docs: List[DocFile], duplicates: Dict[str, List[DocFile]],
                  similar: List[Tuple[DocFile, DocFile, float]]) -> None:
    """Classify each document's status."""

    # Build similarity notes
    similarity_notes = {}
    for doc1, doc2, score in similar:
        if doc1.relative_path not in similarity_notes:
            similarity_notes[doc1.relative_path] = f"Similar to {doc2.relative_path}"
        if doc2.relative_path not in similarity_notes:
            similarity_notes[doc2.relative_path] = f"Similar to {doc1.relative_path}"

    # Build duplicate notes
    duplicate_files = set()
    duplicate_notes = {}
    for hash_val, files in duplicates.items():
        for i, f in enumerate(files):
            duplicate_files.add(f.relative_path)
            if i == 0:
                duplicate_notes[f.relative_path] = f"Master (has {len(files)-1} duplicates)"
            else:
                duplicate_notes[f.relative_path] = f"Identical to {files[0].relative_path}"

    for doc in docs:
        rel_path = doc.relative_path

        # Check for duplicates first
        if rel_path in duplicate_files:
            if "Master" in duplicate_notes.get(rel_path, ""):
                doc.status = "VALID"
            else:
                doc.status = "DUPLICATE"
            doc.similarity_note = duplicate_notes.get(rel_path, "")
            continue

        # Check for obsolete patterns
        if is_obsolete(doc.path.name):
            doc.status = "OBSOLETE"
            doc.similarity_note = "Matches obsolete pattern"
            continue

        # Check if in official manifest
        if rel_path in OFFICIAL_DOCS:
            doc.status = "VALID"
            doc.similarity_note = "Official documentation"
            continue

        # Check for similar names
        if rel_path in similarity_notes:
            doc.status = "REVIEW"
            doc.similarity_note = similarity_notes[rel_path]
            continue

        # Default: needs review
        doc.status = "REVIEW"
        doc.similarity_note = "Not in official manifest"


def generate_report(docs: List[DocFile]) -> str:
    """Generate the documentation health report."""
    lines = [
        "# DOCUMENTATION HEALTH REPORT",
        "",
        f"**Scan Date:** December 2024",
        f"**Project:** Vidurai v2.2.0",
        f"**Files Scanned:** {len(docs)}",
        "",
        "## Status Legend",
        "- VALID: Official documentation, ship it",
        "- DUPLICATE: Exact content match with another file",
        "- OBSOLETE: Matches obsolete naming patterns",
        "- REVIEW: Needs manual review",
        "",
        "---",
        "",
        "## File Inventory",
        "",
        "| Status | File Path | Title | Notes |",
        "| :---: | :--- | :--- | :--- |",
    ]

    # Sort by status priority, then path
    status_order = {"DUPLICATE": 0, "OBSOLETE": 1, "REVIEW": 2, "VALID": 3}
    sorted_docs = sorted(docs, key=lambda d: (status_order.get(d.status, 4), d.relative_path))

    for doc in sorted_docs:
        status_icon = {
            "VALID": "VALID",
            "DUPLICATE": "DUPLICATE",
            "OBSOLETE": "OBSOLETE",
            "REVIEW": "REVIEW",
        }.get(doc.status, "?")

        # Escape pipe characters in title
        safe_title = doc.title.replace('|', '\\|')
        safe_note = doc.similarity_note.replace('|', '\\|')

        lines.append(f"| {status_icon} | `{doc.relative_path}` | {safe_title} | {safe_note} |")

    # Summary section
    by_status = defaultdict(int)
    for doc in docs:
        by_status[doc.status] += 1

    lines.extend([
        "",
        "---",
        "",
        "## Summary",
        "",
        f"| Status | Count |",
        f"| :--- | ---: |",
        f"| VALID | {by_status['VALID']} |",
        f"| REVIEW | {by_status['REVIEW']} |",
        f"| DUPLICATE | {by_status['DUPLICATE']} |",
        f"| OBSOLETE | {by_status['OBSOLETE']} |",
        f"| **Total** | **{len(docs)}** |",
        "",
        "---",
        "",
        "## Recommendations",
        "",
    ])

    # Add recommendations
    if by_status['DUPLICATE'] > 0:
        lines.append(f"1. **Delete {by_status['DUPLICATE']} duplicate file(s)** - Content already exists elsewhere.")
    if by_status['OBSOLETE'] > 0:
        lines.append(f"2. **Archive {by_status['OBSOLETE']} obsolete file(s)** - Move to `docs/archive/`.")
    if by_status['REVIEW'] > 0:
        lines.append(f"3. **Review {by_status['REVIEW']} file(s)** - Decide: keep, archive, or delete.")

    if by_status['DUPLICATE'] == 0 and by_status['OBSOLETE'] == 0 and by_status['REVIEW'] == 0:
        lines.append("Documentation is clean. No action required.")

    lines.extend([
        "",
        "---",
        "",
        "*Generated by `scripts/audit_docs.py` - The Forensic Auditor*",
    ])

    return '\n'.join(lines)


def main():
    """Main entry point."""
    print("Scanning documentation files...")

    # Find all doc files
    docs = find_doc_files(PROJECT_ROOT)
    print(f"Found {len(docs)} documentation files.")

    # Analyze each file
    print("Analyzing content...")
    for doc in docs:
        analyze_file(doc)

    # Find duplicates
    print("Finding duplicates...")
    duplicates = find_duplicates(docs)

    # Find similar names
    print("Finding similar filenames...")
    similar = find_similar_names(docs)

    # Classify all documents
    print("Classifying documents...")
    classify_docs(docs, duplicates, similar)

    # Generate report
    report = generate_report(docs)
    print(report)


if __name__ == "__main__":
    main()
