"""Setup script for fast-x402"""

from setuptools import setup, find_packages
import os

# Read the README file
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# Read requirements
def read_requirements(filename):
    with open(filename, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]

setup(
    name="fast-x402",
    version="1.3.0",
    author="x402 Team",
    author_email="support@x402.org",
    description="Lightning-fast x402 payment integration for FastAPI and modern Python web frameworks",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/x402/fast-x402",
    project_urls={
        "Bug Tracker": "https://github.com/x402/fast-x402/issues",
        "Documentation": "https://docs.x402.org/fast-x402",
        "Source Code": "https://github.com/x402/fast-x402",
    },
    packages=find_packages(exclude=["tests", "tests.*", "examples", "examples.*"]),
    include_package_data=True,
    package_data={
        "fast_x402": ["shared/*.py", "shared/**/*.py"],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Internet :: WWW/HTTP :: HTTP Servers",
        "Topic :: Office/Business :: Financial :: Point-Of-Sale",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Framework :: FastAPI",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.9",
    install_requires=[
        "fastapi>=0.100.0",
        "eth-account>=0.10.0,<0.11.0",
        "web3>=6.11.0",
        "pydantic>=2.0.0",
        "httpx>=0.24.0",
        "redis>=4.5.0",
        "click>=8.0.0",
        "rich>=13.0.0",
        "mnemonic>=0.20",
        "uvicorn>=0.24.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.1.0",
            "black>=23.7.0",
            "ruff>=0.0.286",
            "mypy>=1.5.0",
            "uvicorn>=0.24.0",
        ],
        "cli": [
            "click>=8.0.0",
            "rich>=13.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "x402=fast_x402.cli:cli",
        ],
    },
    keywords=[
        "x402",
        "payments",
        "micropayments",
        "fastapi",
        "http402",
        "blockchain",
        "stablecoin",
        "api-monetization",
    ],
)