# Project Status

> Updated only when a Phase **starts** (Progress table) and when it **closes** (Progress table + report).
> Mid-phase progress lives in `docs/phases/phase-N.md`.

**Last updated:** 2026-10-09

## Progress

| Phase | Name | Status | Started | Completed | Report |
|---|---|---|---|---|---|
| 0 | Foundations & Guardrails | Complete | 2026-09-17 | 2026-10-09 | [Report](#phase-0-foundations--guardrails-2026-09-17--2026-10-09) |
| 1 | Secure Access & Linux Compute | Not started | — | — | — |
| 2 | Personal Web UI & Storage | Not started | — | — | — |
| 3 | Data Collection & Delivery: Building the Agent's Tools | Not started | — | — | — |
| 4 | Observability & Recovery Tools | Not started | — | — | — |
| 5 | AI Agent, Read-Only | Not started | — | — | — |
| 6 | AI Agent, Actions & Delegated Tasks with HITL | Not started | — | — | — |
| 7 | Windows On-Demand (CLI and GUI) | Not started | — | — | — |
| 8 | Private Cloud on My Own Hardware (Stage 2) | Not planned | — | — | — |

Status values: `Not started` · `In progress` · `Complete` · `Not planned`

## Phase Reports

Reports are added below when each Phase closes, oldest first, using `docs/templates/phase-report.md`.

### Phase 0: Foundations & Guardrails (2026-09-17 → 2026-10-09)

**Summary:** A hardened AWS account (Free plan, Seoul) with a `bootstrap` module for the guardrails and a GitHub
Actions pipeline for the `main` module: OIDC roles with no stored keys, a PR plan, an approval-gated apply, security
alerts and budget alerts in Slack, and a protected audit trail.

**Completed**
- Account and identities: root sealed with a passkey (no access keys), IAM user admin with a passkey and `aws login`, no access keys anywhere (E1–E3, E6).
- `bootstrap` module (44 resources at E4, applied by hand under E7): state bucket (versioned, encrypted, public access blocked), account-level S3 Block Public Access, GitHub OIDC provider, `pipeline-plan` (read-only + lock) and `pipeline-apply` (AdministratorAccess within the P4 boundary), multi-Region trail with a delete-protected log bucket, EventBridge alerts G1–G5 and Access Analyzer with forwarders from us-east-1, us-east-2, us-west-2, SNS topic, Amazon Q Developer Slack channel (guardrail `AWSDenyAll`), five budgets (USD 20, one per threshold so the alert names the percent).
- Pipeline: `plan.yml` (fork PRs fail, fmt/validate, plan, job summary) and `apply.yml` (push to `main`, `production` approval, apply role by full ARN); actions pinned to full-length SHAs checked against official tags; Terraform 1.16.5 installed with a pinned SHA256.
- GitHub settings S1–S14 (environment, branch protection, Actions settings), recorded as exception E8.
- Checks kept in the repo: `infra/bootstrap/checks/test_event_patterns.py` (30 pattern cases) and `simulate_policies.py` (57 IAM policy simulator cases, re-run on E7).
- Runbook: `docs/runbooks/root-activity.md` (G1 response, G2 health check, rules while E9 is in place).
- Step 4 findings fixed: the log bucket was reachable through an S3 access point (P4 `DenyAccessPointCreation`); budget alerts did not show the percent and one budget sent one message for five thresholds (one budget per threshold).

**Decisions**

| ADR | Title | Status |
|---|---|---|
| [0001](docs/adr/0001-stage-1-cloud-provider.md) | Stage 1 cloud provider | Accepted |
| [0002](docs/adr/0002-iac-tool.md) | IaC tool | Accepted |
| [0003](docs/adr/0003-remote-state-and-bootstrap.md) | Remote state storage and bootstrap | Accepted |
| [0004](docs/adr/0004-pipeline-auth-and-approval-gate.md) | Pipeline authentication, role split, and approval gate | Accepted |
| [0005](docs/adr/0005-account-identity-structure.md) | Account identity structure | Accepted |
| [0006](docs/adr/0006-budget-alerts-and-delivery-path.md) | AWS budget alerts and alert delivery path | Accepted |
| [0007](docs/adr/0007-security-logging-baseline.md) | Security logging baseline and protection of the logging and alert path | Accepted |

**What I learned**
- Why root stays sealed: it has complete access, a standalone account has no SCP to limit it, and E9 cannot stop it.
- The path from a PR to real infrastructure: plan role on the PR, required check, merge, `production` approval, apply role, G2 alert.
- Why state is remote: one shared state for laptop and pipeline, locking, versioning, and limited access.
- SHA pinning stops moved tags but only checks the format; the chosen SHA still has to be compared with the official tag.
- A Terraform plan only shows the difference; apply changes the cloud; `bootstrap` is applied by hand (E7), `main` only by the pipeline.

**Exit criteria**

| Criterion | Result | Evidence |
|---|---|---|
| Every resource exists because of code | Pass (one item carried over) | Every management write event since 2026-10-06 in all Regions matches an exception, a merged PR, or an AWS-created default or side effect (ADR 0003 interpretation); the AWS User Notifications email contact is carried over to Phase 1. `docs/phases/phase-0.md` §5 |
| Infrastructure changes reach the cloud only through the pipeline | Pass | Every `main` apply ran in the apply workflow (runs 37737103122, 37761298407; the other-Region test 37760564605 was denied); all `main` state access was by the pipeline roles. §5 |
| Test alerts for every AWS budget threshold reach Slack | Pass | One Slack alert per test budget `bootstrap-test-050pct` … `-125pct`. §4 M6 6.4 |

**Before-moving-on check**
- [x] Why the root account should not be used day to day (explained by me; gaps filled).
- [x] What happens between opening a pull request and the change reaching real infrastructure (explained by me; corrected).
- [x] Why state is stored remotely (model answer at my request).
- [x] The account's trust boundaries (drawn by me on 2026-10-05; model answer table at my request).
- [x] Which actions are bootstrap exceptions and how they are controlled (model answer at my request).

**Metrics**
- Monthly cost: AWS USD 0.001 month to date on 2026-10-08 (budget ActualSpend, credits counted); logging estimated at about USD 0.06 a month (target 20 / ceiling 25). AI API: none yet (limit 10).
- Share of resources managed by code: 100% outside the recorded exceptions and AWS-created items, with one item carried over.
- Deployments of `main`: 3 apply runs (2 succeeded, 1 intentional denial test); time to rebuild from zero: not measured.

**Open issues**
- None open in Phase 0; see carry-over.

**Carry-over to next phase**
- (Phase 1) Add an `ec2:InstanceType` allowlist to P4 when compute arrives (ADR 0004 (f)).
- (Phase 1) Decide whether to keep the AWS-created default VPCs or remove them through code.
- (Phase 1) Handle the AWS User Notifications email contact created outside code at the E4 apply (delete, bring into code, or verify and record); I decide when.
- (Phase 1) Decide whether containers on a host follow code, approval, and pipeline, or count as operations.
- (Phase 2) Application CI/CD: compare a new GitHub OIDC role with deploys through the apply pipeline.
- (Phase 4) Decide how to review CloudTrail logs older than the 90-day Event history.
- (Phase 4) Decide which automatic actions need confirmation (first-level recovery, Windows auto-stop).
- (Phase 5) Set a provider-side monthly spend limit for the AI API.
- (Phase 6) Decide how a confirmation for a delegated task with external effects is authenticated.
- (Phase 7) Check how an instance that stops itself fits with power state in code.

**Portfolio notes**
- Built a keyless GitHub Actions to AWS pipeline (OIDC, role split, permissions boundary, approval gate) and proved it with 57 IAM policy simulator checks and a denied cross-Region assumption test.
- Found and fixed an S3 access point bypass of the log bucket protection with the policy simulator before any real misuse.
- Topic: why SHA pinning is necessary but not sufficient for GitHub Actions supply chain security.
