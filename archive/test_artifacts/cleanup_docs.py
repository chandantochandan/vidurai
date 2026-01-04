import os
import re

# Target Directories
TARGET_DIRS = [
    "docs",
    "vidurai",
    "vidurai-daemon",
    "vidurai-vscode-extension",
    "vidurai-browser-extension"
]

# Regex for Emojis (Simple Range)
EMOJI_PATTERN = re.compile(r'[^\x00-\x7F]+')

# Replacements for specific marketing phrases
REPLACEMENTS = {
    "biological hippocampus": "context store",
    "conscience engine": "policy engine",
    "ghost daemon": "daemon service",
    "Real-Time Conscience": "Real-Time Policy",
    "Transform how you work": "Optimize context workflows",
    "magic": "automation",
    "🚀": "", "✅": "", "❌": "", "✨": "", "🧠": "", "🔒": "", "📦": "", "📉": ""
}

def clean_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    original_content = content

    # 1. Remove Emojis
    # We carefully replace only known emojis or common non-ascii used as decoration
    # to avoid breaking legitimate unicode in code comments if any.
    # For safety, we will just use the REPLACEMENTS dict for the emojis found in the audit.

    for key, value in REPLACEMENTS.items():
        content = content.replace(key, value)

    # 2. Fix Double Spaces caused by deletion
    content = re.sub(r'  +', ' ', content)

    if content != original_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Cleaned: {filepath}")

def main():
    for root_dir in TARGET_DIRS:
        for root, dirs, files in os.walk(root_dir):
            for file in files:
                if file.endswith(".md") or file.endswith(".txt"):
                    # Skip the main BRAND and AGENTS files we just hand-wrote
                    if file in ["AGENTS.md", "BRAND.md"]:
                        continue
                    clean_file(os.path.join(root, file))

if __name__ == "__main__":
    main()
