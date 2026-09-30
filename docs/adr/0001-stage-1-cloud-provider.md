# ADR 0001: Stage 1 cloud provider

- **Status:** Accepted
- **Date:** 2026-09-21
- **Phase:** 0

## Context
No cloud account exists yet, so the provider is an open choice. It fixes the vocabulary,
tooling, and price list for all of Stage 1. Constraints from `docs/vision.md`:

- Budget: 30,000 KRW/month target, 40,000 KRW/month ceiling, all-in. (Changed on 2026-09-29 to separate USD budgets: AWS target under USD 20, ceiling USD 25; vision v0.7.)
- Windows on demand (Phase 7): hourly Windows instances must be available.
- IaC + CI/CD with short-lived credentials (Phase 0): OIDC login from GitHub Actions.
- Security logging baseline: an account-wide API audit trail.
- Budget alerts must reach Slack.
- Stage 1 must not block a later move to own hardware (Stage 2).
- Career goal: experience that counts in the Korean job market.

## Options considered

| Option | Pros | Cons | Monthly cost impact |
|---|---|---|---|
| A. AWS (Seoul) | Meets every constraint. Largest market share and job demand. Most documentation and references. Finest-grained IAM. | Steepest learning curve (IAM, service sprawl). Public IPv4 is billed hourly. | Small Linux VM + one public IPv4 + management-event audit log expected to fit the target; free tier terms changed in 2025 and must be verified. |
| B. Google Cloud (Seoul) | Meets every constraint. Simpler IAM. Audit logs on by default. | Less Korean job demand. Budget-to-Slack needs one extra hop (Pub/Sub). | Similar to A; free tier/credits to verify. |
| C. Azure (Korea Central) | Meets every constraint. Simplest Windows licensing. Demand in Korean enterprise/public sector. | Identity model (Entra ID) differs from the others. Fewer personal-project resources. | Similar to A; credits to verify. |
| Low-cost providers (Hetzner, Oracle Free Tier) | Cheapest. | At least one of Windows on demand, audit trail, or OIDC is weak or missing. Low job-market value. | Lowest, but rejected on constraints. |

## 6-Layer check (chosen option)

| Layer | Notes |
|---|---|
| Traffic | VPC is free. Public IPv4 is billed per hour; keep to one and revisit IPv6 later. Avoid NAT gateway, managed VPN endpoints, and load balancers (§5.4 cost traps). |
| Compute | Linux and Windows on demand. ARM (Graviton) instances are cheaper for Linux. |
| Data | S3 for remote state; locking mechanism decided in the ADR for D3. |
| Security | IAM with fine-grained policies, MFA, OIDC federation for GitHub Actions, CloudTrail management events at no charge. |
| Cost | Exact numbers verified against the current price list in D5–D7 and Phase 1. Budget alerts: D6 (ADR 0006). |
| Observability | CloudWatch + AWS Budgets; Slack delivery via a notification service (D6). |

## Decision
AWS, Seoul region (`ap-northeast-2`), for three reasons:

1. It meets every constraint above.
2. It has the largest market share, so the experience carries the most weight.
3. It has the richest documentation and references, which favors learning.

The heavier IAM learning curve is accepted; it matches the "production-minded Cloud
Engineer" goal rather than working against it.

This also answers `docs/vision.md` §12 open question 3.

## Consequences
- Easier: abundant documentation, examples, and hiring relevance.
- Harder: IAM and service sprawl require discipline; every new service must pass the
  simplicity and cost checks.
- Portability: stay on primitives (VMs, object storage, IAM, audit logs). Managed services
  are adopted only with an ADR that notes the Stage 2 exit cost.
- Prices are not fixed here; they are verified at each design step.

## Revisit when
- Monthly cost cannot be kept under the ceiling with AWS primitives.
- Stage 2 planning starts and a different provider offers a clearly cheaper bridge.
