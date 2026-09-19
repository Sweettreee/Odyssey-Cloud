# Phase 0: Foundations & Guardrails (working notes)

> Recovery point for this Phase and the source for the STATUS.md report.
> Update at the end of each learning topic, decision, and implementation step. Keep it short; this is not a transcript.

**Phase status:** In progress
**Current step:** 3 Design & decisions (not started; Step 2 completed 2026-09-19)
**Next action:** Confirm the Step 3 design-question list in §3 and answer the two open facts, then start D1.
**Last updated:** 2026-09-19

> **Resume point.** Steps 1–2 are done in a previous session. A new session starts here: read §3 "Step 3 plan", get confirmation on the list and the two open facts, then present D1 (problem, 2–3 options, 6-Layer check) and wait for the decision.

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

### Step 3 plan (proposed 2026-09-19, awaiting confirmation)

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

Open facts to confirm before D1:
1. Does a cloud account already exist? Which provider?
2. Do a GitHub account and a Slack workspace already exist? (needed for D4, D6)

### ADRs

| ADR | Title | Status |
|---|---|---|
| — | — | — |

## 4. Implementation log

| Date | Step | Result |
|---|---|---|
| — | — | — |

## 5. Verification

### Exit criteria
- [ ] Every resource exists because of code.
- [ ] Infrastructure changes reach the cloud only through the pipeline.
- [ ] Test alerts for both budget levels reach Slack.

## 6. Open issues
- Bootstrap exceptions (account creation, root MFA, and the first credentials) cannot be done as code. Record them in an ADR.
- Decide in Step 3: how bootstrap exceptions are controlled, and how exit criterion 1 relates to them.

## 7. Carry-over to next phase
- …
