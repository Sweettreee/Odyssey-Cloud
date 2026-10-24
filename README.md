# Autonomous Personal Cloud Platform

**A self-managed personal cloud, operated through Slack by an AI agent under human control, and built entirely as code.**

> 🚧 Early stage: design and learning in progress. Live progress is tracked in [STATUS.md](STATUS.md).

---

## What it is

A long-term personal cloud platform with four parts:

- **Secure access.** Reachable from anywhere, but only by me. Nothing is exposed that is not meant to be.
- **On-demand compute.** Self-service Linux containers and Windows environments (CLI and full desktop). They start when needed and stop automatically.
- **Personal Web UI.** One place to upload, download, and search files, and to browse everything the platform collects.
- **AI agent on Slack**, with two roles:
  - **SysAdmin:** monitors and operates the infrastructure.
  - **Productivity Assistant:** carries out assigned tasks and automates recurring work, such as schedule and notice collection, morning briefings, deadline alerts, and natural-language search.

## Why

One goal, reached through one means:

- **Goal: become a production-minded Cloud Engineer.** Learn by making real decisions and operating a real system, not by following tutorials.
- **Means: build and operate my own private cloud service.** It is designed against real problems and real constraints, not to decorate a résumé. The long-term destination is a private cloud running on my own hardware.

## Roadmap

| Stage | Phase | Focus |
|---|---|---|
| **1. Public cloud (interim)** | 0 | Foundations & guardrails: account security, budget alerts, IaC, CI/CD |
| | 1 | Secure access & Linux compute |
| | 2 | Personal Web UI & storage, application CI/CD |
| | 3 | Data collection & delivery: building the agent's tools |
| | 4 | Observability & recovery tools |
| | 5 | AI agent, read-only |
| | 6 | AI agent actions & delegated tasks, with human-in-the-loop |
| | 7 | Windows on demand |
| **2. Own hardware** | 8 | Private cloud (design starts after Stage 1) |

The phases are ordered by dependency and risk, not by fixed dates.

## Principles

- **Infrastructure as Code.** Every resource is created through code and deployed through CI/CD. Any exception is recorded in an ADR.
- **Human-in-the-loop.** The AI can read freely. Every infrastructure change it proposes, including creating, starting, and stopping a resource, is applied through the pipeline only after my approval. Externally visible actions also require confirmation. Both are enforced by permissions rather than prompts.
- **Fixed budgets.** AWS: target under USD 20/month, ceiling USD 25/month. AI API: under USD 10/month. Subscriptions are not included.
- **Security logging.** Access and actions are logged across the whole platform.
- **Self-run by default, then simplicity.** Parts run on software I operate myself or on basic provider building blocks. A managed service is used only when an ADR shows that running it myself is not workable or takes more effort than I accept. Among the remaining options, the simplest wins. No resume-driven technology choices.
- **Rule-based first, AI second.** Deterministic components are built first. They become the agent's tools and remain as fallbacks.
- **Decisions are documented.** Every significant choice records the alternatives considered and the trade-offs.

## Architecture

_To be added as decisions are made in each phase._
Diagrams and the reasoning behind them will be linked from the [ADRs](docs/adr/README.md).

## Documentation

| Document | Purpose |
|---|---|
| [docs/vision.md](docs/vision.md) | Full idea and learning vision: goals, scope, constraints, roadmap |
| [STATUS.md](STATUS.md) | Progress table and end-of-phase reports |
| [docs/adr/](docs/adr/README.md) | Architecture Decision Records |
| [docs/phases/](docs/phases/) | Working notes for each phase |
| [CLAUDE.md](CLAUDE.md) | Working rules for the AI coding assistant used in this project |

## Repository layout

```
.
├── README.md          # This file
├── CLAUDE.md          # AI assistant working rules
├── STATUS.md          # Progress and phase reports
└── docs/
    ├── vision.md      # Idea & learning vision
    ├── phases/        # Per-phase working notes
    ├── adr/           # Architecture Decision Records
    └── templates/     # Templates for notes, reports, ADRs
```

Infrastructure and service code directories will be added as the phases progress.

## License

_To be decided._
