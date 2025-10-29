from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="vidurai",
    version="0.2.0",  # Updated for LangChain integration
    author="Chandan",
    author_email="yvidurai@gmail.com",
    description="Teaching AI the art of memory and forgetting - A Vedantic approach to AI memory management",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/chandantochandan/vidurai",
    project_urls={
        "Homepage": "https://vidurai.ai",
        "Documentation": "https://docs.vidurai.ai",
        "Source Code": "https://github.com/chandantochandan/vidurai",
        "Bug Tracker": "https://github.com/chandantochandan/vidurai/issues",
        "Discord": "https://discord.gg/DHdgS8eA",
    },
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.8",
    install_requires=[
        "sentence-transformers>=2.2.0",
        "nltk>=3.8",
        "faiss-cpu>=1.7.4",
        "loguru>=0.7.0",
        "numpy>=1.24.0",
    ],
    extras_require={
        "langchain": [
            "langchain>=0.1.0",
            "langchain-community>=0.0.1",
        ],
        "llamaindex": [
            "llama-index>=0.9.0",
        ],
        "all": [
            "langchain>=0.1.0",
            "langchain-community>=0.0.1",
            "llama-index>=0.9.0",
        ],
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
        ],
    },
    keywords="ai memory llm langchain llamaindex vedantic forgetting consciousness kosha vismriti viveka",
)