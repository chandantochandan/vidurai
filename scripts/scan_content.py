#!/usr/bin/env python3
"""
The X-Ray - Deep Content Health Scanner

Scans documentation files for:
1. ROT (things to remove): Hardcoded dates, old versions, stale references
2. GAPS (things missing): Personas, integrations, use cases not mentioned

Usage:
    python scripts/scan_content.py

@version 2.2.0
"""

import re
from pathlib import Path
from typing import Dict, List, Tuple
from dataclasses import dataclass, field


@dataclass
class Finding:
    """Represents a content finding."""
    file_path: str
    line_num: int
    category: str  # ROT or GAP
    subcategory: str  # date, version, persona, integration
    match: str
    context: str


# Project root
PROJECT_ROOT = Path(__file__).parent.parent

# Files to scan
TARGET_FILES = [
    "README.md",
    "CONTRIBUTING.md",
    "pyproject.toml",
    "CHANGELOG.md",
    "BRAND.md",
    "AGENTS.md",
]

TARGET_DIRS = [
    "docs/",
]

# ROT patterns (things that should be reviewed/removed)
ROT_PATTERNS = {
    "hardcoded_year": r'\b202[3-4]\b',  # Years 2023-2024 (not current)
    "hardcoded_month": r'\b(January|February|March|April|May|June|July|August|September|October|November)\s+202\d',
    "old_version_v0": r'(?<!\d\.)v?0\.\d+\.\d+(?!\.\d)',  # v0.x.x but not IP addresses
    "old_version_v1": r'(?<!\d\.)v?1\.\d+\.\d+(?!\.\d)',  # v1.x.x but not IP addresses
    "old_version_v2_0": r'\bv?2\.0\.\d+',  # v2.0.x is outdated
    "old_version_v2_1": r'\bv?2\.1\.\d+',  # v2.1.x is outdated
    "todo_comment": r'\b(TODO|FIXME|XXX|HACK)\b',
}

# GAP patterns (things that should be present)
GAP_KEYWORDS = {
    "persona_data_scientist": ["data scientist", "data science", "ml engineer"],
    "persona_researcher": ["researcher", "academic", "scientist"],
    "persona_analyst": ["analyst", "data analyst", "business analyst"],
    "integration_jupyter": ["jupyter", "notebook", "ipynb", "ipython"],
    "integration_neovim": ["neovim", "nvim", "vim"],
    "integration_warp": ["warp", "terminal"],
    "usecase_debugging": ["debug", "debugging", "troubleshoot"],
    "usecase_code_review": ["code review", "pull request", "pr review"],
}

# Exclusion patterns (don't flag these as rot)
EXCLUSION_PATTERNS = [
    r'Last\s+Updated:',  # Intentional date headers
    r'@version',  # Version tags in code
    r'changelog',  # Changelog entries are expected to have dates
    r'CHANGELOG',
]


def should_exclude(line: str, pattern_name: str, file_path: str) -> bool:
    """Check if a line should be excluded from rot detection."""
    line_lower = line.lower()
    file_name = Path(file_path).name.lower()

    # Don't flag changelog entries at all
    if file_name == 'changelog.md':
        return True

    # Don't flag version specifications in pyproject.toml
    if pattern_name.startswith('old_version') and ('requires' in line_lower or '>=' in line or '<=' in line):
        return True

    # Don't flag manifest files (historical records)
    if 'manifest' in file_name or 'phase' in file_name:
        return True

    for excl in EXCLUSION_PATTERNS:
        if re.search(excl, line, re.IGNORECASE):
            return True

    return False


def find_target_files() -> List[Path]:
    """Find all files to scan."""
    files = []

    # Add root-level files
    for fname in TARGET_FILES:
        fpath = PROJECT_ROOT / fname
        if fpath.exists():
            files.append(fpath)

    # Add files from target directories
    for dirname in TARGET_DIRS:
        dirpath = PROJECT_ROOT / dirname
        if dirpath.exists():
            for fpath in dirpath.glob("*.md"):
                # Skip archived files
                if 'archive' not in str(fpath).lower():
                    files.append(fpath)

    return files


def scan_for_rot(content: str, file_path: str) -> List[Finding]:
    """Scan content for rot patterns."""
    findings = []
    lines = content.split('\n')

    for line_num, line in enumerate(lines, 1):
        for pattern_name, pattern in ROT_PATTERNS.items():
            # Skip exclusions
            if should_exclude(line, pattern_name, file_path):
                continue

            matches = re.finditer(pattern, line, re.IGNORECASE)
            for match in matches:
                matched_text = match.group()

                findings.append(Finding(
                    file_path=str(Path(file_path).relative_to(PROJECT_ROOT)),
                    line_num=line_num,
                    category="ROT",
                    subcategory=pattern_name,
                    match=matched_text,
                    context=line.strip()[:80]
                ))

    return findings


def scan_for_gaps(content: str, file_path: str) -> Dict[str, bool]:
    """Scan content for gap keywords (missing concepts)."""
    content_lower = content.lower()
    results = {}

    for gap_name, keywords in GAP_KEYWORDS.items():
        found = any(kw.lower() in content_lower for kw in keywords)
        results[gap_name] = found

    return results


def generate_report(rot_findings: List[Finding], gap_analysis: Dict[str, Dict[str, bool]]) -> str:
    """Generate the Content Health Matrix report."""
    lines = [
        "# CONTENT HEALTH MATRIX",
        "",
        "**Scanner:** The X-Ray v2.2.0",
        "**Scan Date:** Auto-generated",
        "",
        "---",
        "",
        "## Section 1: ROT Detection (Review/Remove)",
        "",
    ]

    if rot_findings:
        # Group by category
        by_category = {}
        for f in rot_findings:
            if f.subcategory not in by_category:
                by_category[f.subcategory] = []
            by_category[f.subcategory].append(f)

        lines.extend([
            "| Category | File | Line | Match | Context |",
            "| :--- | :--- | ---: | :--- | :--- |",
        ])

        for category in sorted(by_category.keys()):
            for f in by_category[category]:
                safe_context = f.context.replace('|', '\\|')[:60]
                lines.append(f"| {category} | `{f.file_path}` | {f.line_num} | `{f.match}` | {safe_context} |")

        lines.extend([
            "",
            f"**Total ROT findings:** {len(rot_findings)}",
        ])
    else:
        lines.append("No rot detected. Documentation is fresh.")

    lines.extend([
        "",
        "---",
        "",
        "## Section 2: GAP Analysis (Missing Content)",
        "",
        "### Coverage Matrix",
        "",
        "| Concept | Status | Files Mentioning |",
        "| :--- | :---: | :--- |",
    ])

    # Aggregate gap analysis across all files
    concept_files = {}
    for file_path, gaps in gap_analysis.items():
        for concept, found in gaps.items():
            if concept not in concept_files:
                concept_files[concept] = []
            if found:
                concept_files[concept].append(file_path)

    missing_concepts = []
    for concept in sorted(concept_files.keys()):
        files = concept_files[concept]
        if files:
            status = "COVERED"
            files_str = ", ".join(f"`{f}`" for f in files[:3])
            if len(files) > 3:
                files_str += f" +{len(files)-3} more"
        else:
            status = "MISSING"
            files_str = "-"
            missing_concepts.append(concept)

        # Format concept name
        display_name = concept.replace('_', ' ').title()
        lines.append(f"| {display_name} | {status} | {files_str} |")

    lines.extend([
        "",
        "---",
        "",
        "## Section 3: Recommendations",
        "",
    ])

    recommendations = []

    # ROT recommendations
    rot_categories = set(f.subcategory for f in rot_findings)
    if 'hardcoded_year' in rot_categories or 'hardcoded_month' in rot_categories:
        recommendations.append("1. **Scrub hardcoded dates** - Replace with 'Auto-generated' or remove entirely.")
    if 'old_version_v0' in rot_categories or 'old_version_v1' in rot_categories:
        recommendations.append("2. **Update version references** - Ensure all references point to v2.x.")
    if 'deprecated_ref' in rot_categories:
        recommendations.append("3. **Remove deprecated references** - Clean up legacy terminology.")
    if 'todo_comment' in rot_categories:
        recommendations.append("4. **Resolve TODO comments** - Complete or remove stale tasks.")

    # GAP recommendations
    if missing_concepts:
        missing_str = ', '.join(c.replace('_', ' ').title() for c in missing_concepts[:5])
        recommendations.append(f"5. **Add missing content** - Document: {missing_str}")

    if recommendations:
        lines.extend(recommendations)
    else:
        lines.append("Documentation is healthy. No action required.")

    lines.extend([
        "",
        "---",
        "",
        "*Generated by `scripts/scan_content.py` - The X-Ray*",
    ])

    return '\n'.join(lines)


def main():
    """Main entry point."""
    print("Scanning documentation content...")

    # Find files
    files = find_target_files()
    print(f"Found {len(files)} files to scan.")

    all_rot_findings = []
    all_gap_analysis = {}

    for fpath in files:
        print(f"  Scanning: {fpath.relative_to(PROJECT_ROOT)}")
        try:
            content = fpath.read_text(encoding='utf-8', errors='replace')
        except Exception as e:
            print(f"    Error reading: {e}")
            continue

        # Scan for rot
        rot = scan_for_rot(content, str(fpath))
        all_rot_findings.extend(rot)

        # Scan for gaps
        rel_path = str(fpath.relative_to(PROJECT_ROOT))
        gaps = scan_for_gaps(content, str(fpath))
        all_gap_analysis[rel_path] = gaps

    # Generate report
    print("\nGenerating report...\n")
    report = generate_report(all_rot_findings, all_gap_analysis)
    print(report)


if __name__ == "__main__":
    main()
