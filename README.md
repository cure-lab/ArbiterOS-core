# ArbiterOS-Core

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)


<p>
  <a href="README.en.md"><b>English Documentation</b></a>
  &nbsp;|&nbsp;
  <a href="README.zh.md"><b>中文文档</b></a>
</p>

> This is the primary English README. Click “中文文档” above to read the Chinese version.

## Overview

ArbiterOS-Core is a lightweight Python library that implements a neuro-symbolic operating system paradigm for reliable AI agents. It wraps LangGraph with a governance kernel (ArbiterGraph), a declarative policy engine, and a Flight Data Recorder for observability.

- Full English docs: [README.en.md](README.en.md)
- 中文文档: [README.zh.md](README.zh.md)

## Quick Start

- Calculator (runnable):
```bash
python -m arbiteros.examples.simple_agent_calc --expr "(2 + 3) * 4 - 5/2"
```
- Walkthrough (web search + summary -> report):
```bash
python -m arbiteros.examples.walkthrough_demo_real --query "NVIDIA Q2 earnings"
```

For full usage, features, and architecture, see [README.en.md](README.en.md).
