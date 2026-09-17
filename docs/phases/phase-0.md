# Phase 0: Foundations & Guardrails (working notes)

> Recovery point for this Phase and the source for the STATUS.md report.
> Update at the end of each learning topic, decision, and implementation step. Keep it short; this is not a transcript.

**Phase status:** Not started
**Current step:** 1 Learning Brief review
**Next action:** Review and refine the draft Learning Brief below.
**Last updated:** —

## Carry-over from previous phase
- None (first Phase).

## 1. Learning Brief

Status: Draft (from `docs/vision.md`). Review before learning starts.

### Before starting
- [ ] Cloud account structure and the shared responsibility model.
- [ ] Identity and access basics: users, roles, policies, least privilege, and MFA.
- [ ] How cloud billing works, and budget alerts.
- [ ] Git basics and the pull request flow.
- [ ] What IaC is, and why it needs state.
- [ ] What CI/CD is, and how a pipeline authenticates to a cloud (long-lived keys vs. short-lived credentials).

### Before moving on (I can explain…)
- [ ] Why the root account should not be used day to day.
- [ ] What happens between opening a pull request and the change reaching real infrastructure.
- [ ] Why state is stored remotely.
- [ ] The account's trust boundaries, drawn on a blank page.

## 2. Learning notes

_None yet._

## 3. Decisions

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

## 7. Carry-over to next phase
- …
