# AeroGuard

AeroGuard is a planned open-source research and simulation platform for counter-UAS operations, sensor fusion, threat intelligence, and defensive situational awareness.

This repository is currently in the bootstrap phase. It establishes the project structure, architecture direction, and engineering guardrails for a Windows-first platform that will eventually include operator tooling, administrative controls, backend APIs, data-integration layers, simulation capabilities, and analytics workflows.

## Purpose

AeroGuard is intended for:

- research and training
- simulation and scenario analysis
- defensive awareness and threat characterization
- sensor fusion and track correlation experiments
- decision support and operator workflow design

It is not intended to provide autonomous weapon engagement, hostile targeting, destructive response, or offensive countermeasure functionality. The project scope is explicitly defensive and research-oriented.

## Current development status

The repository is in a foundation-only stage. The code base does not yet contain production implementations, simulation engines, AI services, or operational interfaces. Planned system components are documented here as architecture intent, not delivered functionality.

## Planned architecture direction

The intended technology direction is:

- Frontend: React, TypeScript, Tauri 2, WebGPU, MapLibre, Three.js/WebGPU when appropriate
- Backend: Python, FastAPI, Pydantic
- Native performance layer: Rust first; C++ only when profiling demonstrates a genuine requirement
- AI and analytics: Python, PyTorch, NumPy, SciPy, OpenCV where appropriate
- Data layer: SQLite initially; DuckDB/Apache Arrow where analytical workloads justify them
- Realtime: WebSocket and typed/binary messaging where justified

## Planned subsystem areas

- Operator Console
- Admin Console
- Developer/API Console
- Backend API
- Authentication and authorization
- Event bus and streaming infrastructure
- Simulation engine
- Sensor simulation and fusion
- Track management and trajectory prediction
- Behavior analysis and anomaly detection
- Threat assessment and incident management
- Replay, analytics, and reporting
- AI services and model workflows
- Database, audit logging, and plugin architecture

## Safety and scope

AeroGuard will remain within defensive, research, and situational-awareness use cases. The project will document and enforce boundaries around safety, authorization, auditability, data provenance, and non-destructive analysis.

## Repository structure

This repository is organized to keep the architecture intent separate from future implementation work:

- docs/ contains system design, roadmap, API intent, and architecture records
- apps/ contains future console applications
- backend/ contains API and service-layer scaffolding in future phases
- engines/ contains native or high-performance execution boundaries
- ai/ contains AI and model workflow boundaries
- packages/ contains shared libraries and client/server contracts
- database/ contains data storage and schema planning
- scripts/ contains repository automation and utility tasks
- tests/ contains future automated test boundaries

## Maintainer / Project Lead

- Maintainer: Tanishk Singhal
- Email: tanishksinghal6285@gmail.com
- GitHub: Tanishk756

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for contributor guidance and repository expectations.

Project-level architectural decisions are maintained by the project maintainer, Tanishk Singhal.

## Security

See [SECURITY.md](SECURITY.md) for security, disclosure, and defensive-scope guidance.

## License

This project is licensed under the Apache License 2.0. See [LICENSE](LICENSE).

## Documentation map

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — high-level architecture
- [docs/ROADMAP.md](docs/ROADMAP.md) — phased delivery plan
- [docs/DATA_MODEL.md](docs/DATA_MODEL.md) — conceptual domain model
- [docs/API.md](docs/API.md) — planned API domains
- [docs/UI_ARCHITECTURE.md](docs/UI_ARCHITECTURE.md) — operator experience and interface design
- [docs/ADMIN_ARCHITECTURE.md](docs/ADMIN_ARCHITECTURE.md) — admin console and governance model
- [docs/EVENT_ARCHITECTURE.md](docs/EVENT_ARCHITECTURE.md) — event-driven architecture
- [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) — engineering workflow and standards
- [docs/DECISIONS.md](docs/DECISIONS.md) — architecture decision records
