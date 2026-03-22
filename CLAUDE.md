# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

mockserial is a Python library (published to PyPI as `pyserial-mock`) that provides a mock implementation of the Serial class (as implemented by pySerial). It allows testing code that communicates over serial connections without real hardware.

## Development Commands

```bash
# Install in dev mode
uv sync --group dev

# Run all tests (includes coverage reporting)
uv run pytest

# Run a single test
uv run pytest tests/test_mock_serial.py::test_read_write

# Lint
uv run ruff check .

# Format
uv run ruff format .

# Format check (CI mode)
uv run ruff format --check .

# Pre-commit hooks (run manually)
uv run pre-commit run --all-files
```

## Architecture

The entire library is in a single module: `src/mockserial/mock_serial.py`.

- **`MockSerial`** — Drop-in replacement for pySerial's `Serial`. Two `MockSerial` instances are linked as peers; `write()` on one pushes data into the other's read buffer. Thread-safe via `threading.Lock` on the read buffer. Supports `read`, `readline`, `in_waiting`, `flush`, `reset_input_buffer`, and `close`.
- **`create_serial_connection(timeout=None)`** — Factory that returns a connected `(s1, s2)` pair.

## Code Style

- Line length: 79 (enforced by ruff)
- Linting and formatting: ruff (configured in pyproject.toml)
- `__init__.py` re-exports `MockSerial` and `create_serial_connection` (F401 suppressed)

## Release Process

Releases are automated via release-please. Merging conventional commits to `main` triggers a release PR. Merging that PR creates a GitHub release and publishes to PyPI via trusted publishing.
