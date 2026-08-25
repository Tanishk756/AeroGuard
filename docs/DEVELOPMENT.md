# Development guide

This document defines the development workflow for AeroGuard. Stage B backend
commands below are implemented and verified; later subsystem workflows remain
planned.

## Maintainer

Project maintainer: Tanishk Singhal
Email: tanishksinghal6285@gmail.com
GitHub: Tanishk756

## Local Python virtual environment

AeroGuard backend dependencies must be installed into a project-local virtual environment named .venv. This prevents contamination of the system Python environment and keeps the project Windows-friendly.

PowerShell commands:

```powershell
./scripts/setup-venv.ps1
./scripts/activate-venv.ps1
```

Once the environment is active, backend commands should use the virtual environment Python explicitly:

```powershell
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -m pip install -r .\backend\requirements.txt
```

Do not install backend packages into the global Python installation.

## Stage B backend commands

From the repository root (`C:\AeroGuard`), install and migrate with the local
environment:

```powershell
.\.venv\Scripts\python.exe -m pip install -r .\backend\requirements.txt
.\.venv\Scripts\python.exe -m alembic -c .\backend\alembic.ini upgrade head
```

Run the backend tests and start the development server:

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir .\backend --reload
```

Verify `http://127.0.0.1:8000/api/v1/health` and
`http://127.0.0.1:8000/api/v1/system/info` while the server is running.

Tauri/native packaging is temporarily deferred because Windows Application
Control is blocking `cargo.exe`. Do not disable or modify Smart App Control,
Defender, or Code Integrity, and do not reinstall Rust to work around it.

## 1. Windows-first development requirements

The project is designed primarily for Windows-based development workflows. This means the repo should be maintainable and runnable without requiring Linux-first tooling or mandatory container dependencies.

Development expectations include:

- Windows as the primary local environment
- portable, clearly documented tooling choices
- no mandatory Linux-only dependencies
- no assumption that a Unix shell is required for primary development tasks

## 2. Engineering standards

### 2.1 Language and platform direction

- Frontend: React + TypeScript
- Desktop shell: Tauri 2
- Visualization: WebGPU, MapLibre, Three.js/WebGPU where justified
- Backend: Python + FastAPI + Pydantic
- Performance layer: Rust first
- C++ only when profiling demonstrates a genuine and documented need

### 2.2 Safety and design standards

- do not implement autonomous weapon engagement
- do not add offensive or destructive countermeasure logic
- keep simulation data distinct from real sensor data
- preserve auditability for sensitive changes
- favor typed contracts and explicit boundary design

## 3. Testing standards

Every major subsystem should eventually include the appropriate level of automated validation:

- unit tests
- integration tests
- API tests
- regression tests
- UI tests where applicable
- performance benchmarks for throughput-sensitive components

Testing should be introduced as part of subsystem development, not added as an afterthought.

## 4. Formatting, linting, and type checking

The project will eventually adopt a consistent code quality workflow using standard tooling appropriate to the stack. Planned emphasis includes:

- consistent formatting
- linting rules matched to the language and toolchain
- type checking for TypeScript and Python contracts where used
- validation before merge for substantial changes

## 5. Git workflow

- keep commits small and logically grouped
- avoid unrelated rewrites
- preserve user work and avoid destructive commands
- document significant architectural decisions in the project docs

Prohibited destructive commands include the repository-level prohibitions described in [AGENTS.md](../AGENTS.md).

## 6. AI-agent workflow

AI-assisted work should:

- inspect existing architecture before modifying the repository
- explain important architectural changes
- avoid unnecessary rewrites
- preserve working functionality
- run lightweight validation for changed areas
- report ambiguity and known limitations honestly

## 7. Documentation expectations

When a major subsystem is introduced or significantly changed, the project documentation should be updated to match the new design boundaries and intended responsibilities.

## 8. Planned non-goals for later phases

This document defines the engineering workflow and operating principles for the project. Stage B's backend test and run commands are configured; authentication, frontend integration, and native packaging remain outside this phase.
