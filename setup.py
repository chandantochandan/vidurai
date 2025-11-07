from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="vidurai",
    version="1.6.1",
    author="Chandan",
    author_email="yvidurai@gmail.com",
    description="Self-learning AI memory system with RL-based compression - Intelligence emerges from experience, not rules",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/chandantochandan/vidurai",
    project_urls={
        "Homepage": "https://vidurai.ai",
        "Documentation": "https://docs.vidurai.ai",
        "Source Code": "https://github.com/chandantochandan/vidurai",
        "Bug Tracker": "https://github.com/chandantochandan/vidurai/issues",
        "Discord": "https://discord.gg/DHdgS8eA",
        "Changelog": "https://github.com/chandantochandan/vidurai/blob/main/CHANGELOG.md",
    },
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",  # Upgraded from Alpha
        "Intended Audience :: Developers",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=[
        "loguru>=0.7.0",  # Minimal core dependency
        "pandas>=1.3.0",  # Required for memory ledger (v1.6.0+)
    ],
    extras_require={
        # RL Agent and Semantic Compression (v1.5.0 core features)
        "rl": [
            "sentence-transformers>=2.2.0",  # For semantic relevance
        ],
        # LLM providers for semantic compression
        "openai": [
            "openai>=1.0.0",
        ],
        "anthropic": [
            "anthropic>=0.18.0",
        ],
        # Legacy integrations
        "langchain": [
            "langchain>=0.1.0",
            "langchain-community>=0.0.1",
        ],
        "llamaindex": [
            "llama-index>=0.9.0",
        ],
        # All features
        "all": [
            "pandas>=1.3.0",
            "sentence-transformers>=2.2.0",
            "openai>=1.0.0",
            "anthropic>=0.18.0",
            "langchain>=0.1.0",
            "langchain-community>=0.0.1",
            "llama-index>=0.9.0",
        ],
        # Development tools
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
        ],
    },
    keywords="ai memory reinforcement-learning rl-agent semantic-compression llm langchain llamaindex vedantic forgetting consciousness kosha vismriti q-learning",
)