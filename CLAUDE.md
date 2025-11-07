# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Portfolio Manager Pro is a Python-based portfolio management system designed to run on a Hetzner server (64GB RAM, 12C/24T). The project is in early stages of development.

## Language and Localization

**Project Language: Polish (Polski)**

- All communication with the user should be in Polish
- Code comments should be in Polish
- User-facing messages, logs, and outputs should be in Polish
- Documentation can remain in English for technical compatibility, but explanations to the user should be in Polish
- The application uses Polish as the default language (configured in `config.py`)

## Development Environment

### Virtual Environment Setup
The project uses a Python virtual environment located in `venv/`.

**Activate virtual environment:**
- Windows: `.\venv\Scripts\Activate.ps1` (PowerShell) or `.\venv\Scripts\activate.bat` (Command Prompt)
- Linux/Mac: `source venv/bin/activate`

**Install dependencies:**
```bash
pip install -r requirements.txt
```

### Running the Application
```bash
python main.py
```

## Core Dependencies

The project uses the following key Python libraries:
- **pandas** (2.3.3) - Data manipulation and analysis
- **numpy** (2.3.4) - Numerical computing
- **matplotlib** (3.10.7) - Data visualization
- **requests** (2.32.5) - HTTP library for API calls

## Architecture

This is currently a greenfield project with minimal structure. The main entry point is `main.py`. As the application evolves, consider organizing code into:
- Data models for portfolios, assets, and transactions
- Services for data fetching, analysis, and portfolio calculations
- Utilities for financial computations and metrics
- API/CLI interfaces for user interaction

## Server Environment

The target deployment environment is a Hetzner server with:
- 64GB RAM
- 12 cores / 24 threads

This high-performance server suggests the application may handle:
- Large-scale data processing
- Complex portfolio calculations
- Database operations (strategy-based, as mentioned in README)
- Potentially concurrent portfolio analysis

When developing features, keep this server capacity in mind for optimization opportunities.
