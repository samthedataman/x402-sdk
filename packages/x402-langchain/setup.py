"""Setup script for x402-langchain"""

from setuptools import setup, find_packages

# Read the README file
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# Read requirements
def read_requirements(filename):
    with open(filename, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]

setup(
    name="x402-langchain",
    version="1.1.0",
    author="x402 Team",
    author_email="support@x402.org",
    description="x402 payment integration for LangChain - Enable autonomous AI agent payments",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/x402/x402-langchain",
    project_urls={
        "Bug Tracker": "https://github.com/x402/x402-langchain/issues",
        "Documentation": "https://docs.x402.org/x402-langchain",
        "Source Code": "https://github.com/x402/x402-langchain",
    },
    packages=find_packages(exclude=["tests", "tests.*", "examples", "examples.*"]),
    include_package_data=True,
    package_data={
        "x402_langchain": ["shared/*.py", "shared/**/*.py"],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Office/Business :: Financial",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.9",
    install_requires=[
        "langchain>=0.1.0",
        "langchain-core>=0.1.0",
        "eth-account>=0.10.0",
        "web3>=6.11.0",
        "httpx>=0.25.0",
        "pydantic>=2.0.0",
        "aiohttp>=3.8.0",
        "mnemonic>=0.20",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.1.0",
            "black>=23.7.0",
            "ruff>=0.0.286",
            "mypy>=1.5.0",
            "langchain-openai>=0.0.5",
        ],
    },
    keywords=[
        "x402",
        "langchain",
        "ai-agents",
        "payments",
        "micropayments",
        "blockchain",
        "autonomous-agents",
        "llm",
    ],
)