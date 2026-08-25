# Architecture decision records

This document captures the initial architecture decision record set for AeroGuard. It is intended as a lightweight ADR-style record to preserve the reasoning behind key design choices.

Project maintainer and architectural decision owner: Tanishk Singhal
Email: tanishksinghal6285@gmail.com
GitHub: Tanishk756

## ADR-001: Keep the project in a defensive, research-only scope

Status: accepted

Context:

AeroGuard is described as a counter-UAS research, simulation, and situational-awareness platform. The project must not implement autonomous engagement, weapon targeting, destructive countermeasure behavior, or offensive actions.

Decision:

The repository and all future subsystem work will remain explicitly defensive, research-oriented, and non-destructive.

Consequences:

- the product scope excludes autonomous engagement controls
- threat analysis and detection workflows remain analytical and review-oriented
- admin and operator interfaces will emphasize awareness and risk understanding

## ADR-002: Use a Windows-first engineering baseline

Status: accepted

Context:

The project direction calls for a Windows-first environment with no mandatory Linux dependency.

Decision:

The project will prefer Windows-centric tooling and workflows, while avoiding Linux-only assumptions in the repository foundation.

Consequences:

- the repo remains open to Windows-based day-to-day development
- future tooling choices must not force Linux-only developer dependencies
- cross-platform compatibility is a benefit, not a mandatory dependency model

## ADR-003: Keep frontend and backend responsibilities separated

Status: accepted

Context:

AeroGuard includes operator, admin, and developer consoles alongside backend APIs and analytics services.

Decision:

Frontend concerns will stay focused on UI, experience, and presentation; backend concerns will own domain logic, validation, authorization, persistence, and orchestration.

Consequences:

- clear API contracts are required between UI and service layers
- domain logic is not embedded in UI code
- future subsystem teams can evolve each layer with fewer cross-coupling risks

## ADR-004: Favor Rust-first native performance boundaries

Status: accepted

Context:

The project is performance-sensitive, but native complexity must be justified and kept bounded.

Decision:

The platform will prefer Rust for performance-sensitive native work and only consider C++ when profiling demonstrates a genuine requirement.

Consequences:

- performance work stays explicit and measurable
- the repo avoids unnecessary native complexity
- any direct native implementation will be justified by evidence

## ADR-005: Use Python, FastAPI, and Pydantic for backend services

Status: accepted

Context:

The project intends a backend service architecture that supports API workflows, validation, and integration cleanly and predictably.

Decision:

The intended backend technology direction is Python with FastAPI and Pydantic.

Consequences:

- service contracts gain strong validation and typed modeling
- backend APIs remain aligned with modern Python service patterns
- future API and schema work can evolve consistently

## ADR-006: Use WebGPU selectively for performance-sensitive visualization

Status: accepted

Context:

The platform needs rich visual experiences for map layers, 3D analysis, and operator workflows but should not over-engineer rendering layers without evidence.

Decision:

WebGPU and related visualization technologies will be used selectively where they materially improve performance or capability.

Consequences:

- the project can support high-density visualization without forcing a broad GPU-first architecture
- MapLibre and Three.js/WebGPU remain viable visual foundations
- rendering complexity will be justified by actual workload needs

## ADR-007: Maintain a clear event-driven architecture

Status: accepted

Context:

AeroGuard requires realtime updates, operational state synchronization, and the ability to review significant system changes.

Decision:

The platform will use typed, versioned, and auditable events to connect subsystems and deliver realtime updates.

Consequences:

- decoupled subsystem interaction becomes easier
- event replay and auditability are better supported
- operational data flow remains traceable and testable

## ADR-008: Preserve simulation and real data separation

Status: accepted

Context:

The project includes simulation, training, and research workflows, but must not confuse synthetic data with authentic sensor data.

Decision:

Simulation data will be clearly labeled and structurally distinct from real sensor and operational data.

Consequences:

- provenance and classification metadata become mandatory for synthetic feeds
- evaluation and testing environments remain well-defined
- operational trust and auditability are stronger

## ADR-009: Keep architecture documentation and subsystem boundaries explicit

Status: accepted

Context:

The repository is intentionally in a bootstrap phase and must remain aligned to clear architectural planning.

Decision:

Subsequent implementation work must use the architecture and roadmap documents as authoritative references for subsystem boundaries and planned responsibilities.

Consequences:

- major changes are anchored in documented design intent
- the repo stays consistent with the stated architecture direction
- future work is less likely to drift into incompatible or unreviewed designs
