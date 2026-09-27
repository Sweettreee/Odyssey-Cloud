# Phase 0: Foundations & Guardrails (working notes)

> Recovery point for this Phase and the source for the STATUS.md report.
> Update at the end of each learning topic, decision, and implementation step. Keep it short; this is not a transcript.

**Phase status:** In progress
**Current step:** 3 Design & decisions (D1–D4 done; D5 next)
**Next action:** Present D5 (account identity structure), including the D5 hand-offs from ADR 0004.
**Last updated:** 2026-09-27

> **Resume point.** Step 3 in progress. D1–D3 decided (ADR 0001–0003). D4 decided (ADR 0004, Accepted). Next: D5, with hand-offs listed in §3.

## Carry-over from previous phase
- None (first Phase).

## 1. Learning Brief

Status: Final (agreed on 2026-09-17). Added topics 7–8 and one "before moving on" item; nothing removed.

### Before starting
- [x] Cloud account structure and the shared responsibility model.
- [x] Identity and access basics: users, roles, policies, least privilege, and MFA.
- [x] How cloud billing works, and budget alerts.
- [x] Git basics and the pull request flow.
- [x] What IaC is, and why it needs state.
- [x] What CI/CD is, and how a pipeline authenticates to a cloud (long-lived keys vs. short-lived credentials).
- [x] Security logging baseline: why an audit trail is needed and which events to record.
- [x] The bootstrap problem: what must exist by hand before IaC can run, and why those exceptions are recorded in an ADR.

### Before moving on (I can explain…)
- [ ] Why the root account should not be used day to day.
- [ ] What happens between opening a pull request and the change reaching real infrastructure.
- [ ] Why state is stored remotely.
- [ ] The account's trust boundaries, drawn on a blank page.
- [ ] Which actions are bootstrap exceptions and how they are controlled.

## 2. Learning notes

### Cloud account structure and the shared responsibility model
- An account is the billing and isolation unit. Root is the one identity that cannot be restricted, so it is sealed and daily work uses restrictable identities.
- The provider secures the cloud itself; access, configuration, data, and logging inside the account are my responsibility.
- Every Phase 0 item sits in the "my responsibility" column.

### Identity and access basics
- Authentication (who) and authorization (allowed?) are separate; policies are what authorization is made of.
- Humans get a user + MFA; machines (pipeline, servers, agent) get a role + temporary credentials. No long-lived keys.
- Least privilege: each identity has only the permissions its job needs.

### Cloud billing and budget alerts
- Billing is hourly, per-usage, or per-request; hourly items (charged while on, even if idle) are the most dangerous.
- Budget alerts lag by hours and come in two kinds: actual spend and forecasted spend.
- Alerts do not prevent overspend; they only surface it early. Prevention is a design job (auto-shutdown, etc.).

### Git basics and the pull request flow
- A commit is a revertible snapshot, a branch is a workspace, `main` is the truth.
- A PR is a "review then merge" request; infrastructure changes enter `main` only through PRs.
- Merging to `main` is the apply approval, so direct pushes to `main` are blocked.

### IaC and state
- IaC = declare desired infrastructure in code -> plan (compare only) -> apply (change). Gives reproducibility, review, and history.
- State maps code resources to real resources; without it the tool duplicates or cannot delete.
- State lives remotely with locking so I and the pipeline see the same state and cannot apply concurrently. It can contain secrets, so it never goes into Git.

### CI/CD and pipeline authentication
- CI = automatic plan on every PR; CD = apply after merge, behind an approval gate. Merging alone never changes infrastructure.
- The pipeline proves "I am this repo's workflow" via OIDC and receives temporary credentials. Zero stored secrets.
- Separate plan (read-only) and apply (write) roles so the PR stage cannot change anything.

### Security logging baseline
- The baseline is an account-wide API audit trail. It only helps if it is on before something goes wrong.
- Logs must be tamper-resistant and retained long-term; the log store gets minimal delete permissions.
- One management-API trail is nearly free. Data-access logs are not needed yet.

### The bootstrap problem
- Some things must exist before IaC can run (account, root MFA, first admin identity, state store, pipeline trust setup). That is the bootstrap problem.
- Rule: any action that cannot be done as code is recorded in an ADR as an exception.
- Open for Step 3: how exceptions are controlled, and how exit criterion 1 ("every resource exists because of code") relates to them.

## 3. Decisions

### Step 3 plan (confirmed 2026-09-21)

Design questions, in dependency order. Each gets problem/constraints, 2–3 options, a 6-Layer check, my decision, and an ADR. Small ones may share an ADR.

| # | Design question | Depends on |
|---|---|---|
| D1 | Stage 1 cloud provider | — |
| D2 | IaC tool | D1 |
| D3 | Remote state storage and bootstrap handling (manual + ADR / import / separate bootstrap code; how exceptions are controlled) | D1, D2 |
| D4 | CI/CD platform and pipeline authentication (approval gate, plan/apply role split) | D1, D2, D3 |
| D5 | Account identity structure (root sealing, daily identity, MFA) | D1 |
| D6 | Budget alert design (thresholds, actual vs. forecast, path to Slack) | D1 |
| D7 | Security logging baseline scope (what, where, how long) | D1 |

Facts confirmed 2026-09-21: no cloud account exists yet (created in Step 4); GitHub account and Slack workspace exist.

| # | Decision | ADR |
|---|---|---|
| D1 | AWS, Seoul region (`ap-northeast-2`) | 0001 |
| D2 | Terraform | 0002 |
| D3 | S3 state with native lock file; separate `bootstrap` root module, state migrated into its own bucket; exceptions E1–E7 | 0003 |
| D4 | GitHub Actions; OIDC plan role (ReadOnlyAccess + lock + read Denies) and apply role (Admin + boundary P4); `production` environment gate; `main`-only enforced by S3 and the OIDC subject (S15); fork PRs fail closed; GitHub settings as exception E8 | 0004 |

### ADRs

| ADR | Title | Status |
|---|---|---|
| [0001](../adr/0001-stage-1-cloud-provider.md) | Stage 1 cloud provider | Accepted |
| [0002](../adr/0002-iac-tool.md) | IaC tool | Accepted |
| [0003](../adr/0003-remote-state-and-bootstrap.md) | Remote state storage and bootstrap | Accepted |
| [0004](../adr/0004-pipeline-auth-and-approval-gate.md) | Pipeline authentication, role split, and approval gate | Accepted |

## 4. Implementation log

| Date | Step | Result |
|---|---|---|
| — | — | — |

## 5. Verification

### Exit criteria
- [ ] Every resource exists because of code.
- [ ] Infrastructure changes reach the cloud only through the pipeline.
- [ ] Test alerts for both budget levels reach Slack.

Interpretation (ADR 0003): criterion 1 excludes resources created by exceptions E1–E6; criterion 2 applies to the `main` module, while `bootstrap` follows E7.

## 6. Open issues
- ~~Bootstrap exceptions must be recorded in an ADR.~~ Resolved: ADR 0003 (E1–E7).
- ~~How exceptions are controlled and how exit criterion 1 relates to them.~~ Resolved: ADR 0003 control rules and exit criteria interpretation.
- D7: decide whether CloudTrail lives in `bootstrap` or `main` (it should be on as early as possible).
  Constraint (ADR 0004 EP-22): CloudTrail, its log bucket, budget alerts, and the Denies that protect them exist no later than E4.
- ~~Vision §5.1 "no ClickOps" had no exception clause.~~ Resolved 2026-09-25: owner approved adding "except for exceptions recorded in an ADR" to vision §5.1 (matches CLAUDE.md §11).

### Hand-offs from ADR 0004
- D5: admin identity type and MFA (EP-13); admin role trust has no service principal (EP-20); AWS human identity vs. the GitHub approval path (EP-24, solo-approval limit); AWS Organizations + RCP (EP-21); whether secrets move to a separate AWS account (ADR 0004 (e)).
- D6: delivery path for the apply-role assumption alert and security alerts.
- D7: protect CloudTrail, its log bucket, and budget alerts, in place no later than E4 (EP-22); external access analyzer; CloudTrail alert on trust/resource-policy changes, including any role other than `pipeline-plan`/`pipeline-apply` whose trust names the GitHub OIDC provider (EP-21); alert on every apply-role assumption (EP-24).

### Step 4 checklist (from ADR 0004)
- GitHub account checklist (2FA passkey/security key, remove unused tokens/keys/grants, check `gh auth status` scopes) before creating AWS resources.
- `.gitignore`: `*.tfstate*`, `.terraform/`, `*.tfplan`, `*.tfvars` before E4.
- E8 ordering: create `production` and verify S1–S4, and set and read back S15, before E4.
- Fork-PR `id-token` test before E4 (one approved test PR from someone else's account).
- `gh` login hygiene: log in only when needed and `gh auth logout` afterwards, or use a short-lived read-only token in `GH_TOKEN`.
- Fill `<OWNER_ID>`/`<REPO_ID>`; verify the exact `sub` strings from a real token, printing only the `sub` claim (never the whole token); confirm `gh api` endpoints for E8 checks.

## 7. Carry-over to next phase
- …
