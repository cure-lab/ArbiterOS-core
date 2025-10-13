from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="arbiteros-core",
    version="0.1.0",
    author="ArbiterOS Team",
    author_email="team@arbiteros.dev",
    description="A formal operating system paradigm for reliable AI agents",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/arbiteros/arbiteros-core",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.8",
    install_requires=[
        "langgraph>=0.2.0",
        "langchain>=0.3.0",
        "langchain-openai>=0.2.0",
        "pydantic>=2.0.0",
        "instructor>=1.0.0",
        "openai>=1.0.0",
        "opentelemetry-api>=1.20.0",
        "opentelemetry-sdk>=1.20.0",
        "opentelemetry-instrumentation>=0.41b0",
        "opentelemetry-exporter-jaeger>=1.20.0",
        "redis>=5.0.0",
        "langgraph-checkpoint-redis>=0.1.0",
        "click>=8.0.0",
        "rich>=13.0.0",
        "typer>=0.9.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "isort>=5.12.0",
            "mypy>=1.0.0",
        ],
        "examples": [
            "httpx>=0.25.0",
            "aiohttp>=3.8.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "arbiteros-assist=arbiteros.cli.migration:main",
        ],
    },
)
