# AeroGuard — AI Engineering Rules

## Project

AeroGuard is an open-source, Windows-first Counter-UAS research,
simulation, sensor-fusion, threat-intelligence, and defensive
situational-awareness platform.

The project is intended for research, training, simulation,
testing, and defensive analysis.

It must not implement autonomous weapon engagement,
weapon targeting, jamming, destructive actions, or offensive
countermeasure functionality.

## Core Principles

1. Do not redesign the architecture without explicit approval.
2. Do not introduce unnecessary dependencies.
3. Prefer open-source and free technologies.
4. The primary development environment is Windows.
5. Linux must never be a mandatory development dependency.
6. Every major subsystem must have automated tests.
7. Do not silently modify APIs or data contracts.
8. Do not duplicate functionality.
9. Keep frontend and backend concerns separated.
10. Keep domain logic independent from UI code.
11. Use typed interfaces wherever practical.
12. Document non-obvious architectural decisions.
13. Never commit secrets, credentials, API keys, or tokens.
14. Never fabricate sensor data as real-world data.
15. Clearly distinguish simulation data from real sensor data.

## Architecture

The platform consists of:

- Operator Console
- Admin Console
- Developer/API Console
- Backend API
- Authentication and authorization
- Event bus
- Simulation engine
- Sensor simulation
- Sensor fusion
- Track management
- Trajectory prediction
- Behavior analysis
- Anomaly detection
- Threat assessment
- Incident management
- Replay
- Analytics
- Reporting
- AI services
- Database
- Audit logging

## Technology Direction

Frontend:
- React
- TypeScript
- Tauri
- WebGPU where appropriate

Backend:
- Python
- FastAPI
- Pydantic

Native/high-performance components:
- Rust first
- C++ only when profiling demonstrates a real requirement

AI/ML:
- Python
- PyTorch
- NumPy
- SciPy
- OpenCV where appropriate

Database:
- SQLite initially
- DuckDB/Apache Arrow for analytical workloads where justified

Realtime:
- WebSocket
- efficient typed/binary messaging where justified

## Performance

Performance must be measured rather than assumed.

Do not introduce C++ merely because it is theoretically faster.

Prefer:

- efficient algorithms
- batching
- asynchronous processing
- GPU acceleration
- profiling
- caching
- appropriate data structures

## Security

All administrative operations must be authenticated
and authorized.

Important actions must be auditable.

Use:

- RBAC
- permission checks
- secure password handling
- session management
- audit logs
- input validation
- rate limiting where appropriate

Never store plaintext passwords.

## UI/UX

AeroGuard is not a generic SaaS dashboard.

The UI should feel like professional aerospace,
mission-control, simulation, and engineering software.

Priorities:

- information density without clutter
- excellent typography
- keyboard accessibility
- responsive layouts
- smooth transitions
- clear threat hierarchy
- strong visual feedback
- 2D/3D visualization
- dockable/resizable panels
- command palette
- dark tactical theme
- accessibility and high contrast

Avoid:

- excessive gradients
- unnecessary animations
- fake "hacker" aesthetics
- meaningless glowing effects
- dashboard-card overload

## Development Process

Before implementing a major subsystem:

1. Inspect the existing repository.
2. Understand existing architecture.
3. Identify affected modules.
4. Plan the change.
5. Implement incrementally.
6. Run tests.
7. Run lint/type checks.
8. Verify no unrelated files were modified.
9. Update documentation where necessary.

Never rewrite large parts of the project simply to make
a local change easier.

## Testing

Every subsystem should eventually have:

- unit tests
- integration tests
- API tests
- regression tests

UI subsystems should have appropriate component or
end-to-end tests.

Performance-sensitive systems should have benchmarks.

## Git

Use small, logically grouped commits.

Never use:

git reset --hard

git clean -fd

or destructive repository commands unless explicitly
authorized.

Never discard user changes.

## AI Agent Behavior

The AI agent must:

- inspect before modifying
- explain significant architectural changes
- avoid unnecessary rewrites
- preserve working functionality
- run tests after changes
- report failures honestly
- never claim something works without verification

When requirements are ambiguous, identify the ambiguity
rather than silently inventing a major architectural decision.