# Contributing to AeroGuard

This repository is currently in the bootstrap and architecture-definition stage. Contributions should support the long-term platform architecture described in the project documentation, without inventing production features before the design is agreed.

## Maintainer

The project maintainer is Tanishk Singhal.

Project-level architectural decisions are maintained by the project maintainer and should be aligned with the repository architecture, safety boundaries, and documentation before major changes are implemented.

## Scope

The project is intentionally limited to defensive, research-oriented, and situational-awareness work. Contributors should not introduce autonomous weapons, destructive response mechanisms, or offensive countermeasure logic.

## Before proposing a major change

1. Read [AGENTS.md](AGENTS.md).
2. Review the relevant architecture and planning documents in [docs/](docs/).
3. Confirm whether the change is a documentation update, a bootstrap change, or a future subsystem design task.
4. Keep changes small and architecture-aware.

## Project expectations

- Do not silently alter APIs or data contracts.
- Keep frontend and backend concerns separated.
- Preserve the documented Windows-first and open-source posture.
- Prefer minimal, maintainable changes.
- Document any non-obvious design tradeoff.
- Follow the project safety and authorization requirements.

## Documentation-first workflow

Because implementation is intentionally not yet broad, most new work should begin with:

- a design note or ADR update
- a roadmap alignment check
- a clear statement of what is planned versus implemented

## Commit and PR expectations

- Keep commits small and logically grouped.
- Explain the rationale for significant architecture decisions.
- Avoid unrelated refactors.
- Ensure new work aligns with the repo's defensive scope and security posture.

## Security and safety

Do not share secrets, credentials, or sensitive operational examples. Follow the guidance in [SECURITY.md](SECURITY.md). If you suspect a vulnerability or unsafe scope drift, report it privately according to the disclosure process in that document.
