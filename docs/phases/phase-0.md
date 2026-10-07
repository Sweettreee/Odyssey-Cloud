# Phase 0: Foundations & Guardrails (working notes)

> Recovery point for this Phase and the source for the STATUS.md report.
> Update at the end of each learning topic, decision, and implementation step. Keep it short; this is not a transcript.

**Phase status:** In progress
**Current step:** 4 Implementation (Step 3 closed by the owner on 2026-10-04: D1–D7 decided, ADR 0001–0007; two reviews applied)
**Next action:** M4 E5: add the S3 backend (PR, E7), then `terraform init -migrate-state` from merged main.
**Last updated:** 2026-10-06

> **Resume point.** Step 3 closed on 2026-10-04 (ADR 0001–0007, Accepted). Step 4 in progress since 2026-10-05; see Next action, the §4 log, and the §6 checklist.

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
| D3 | S3 state with native lock file; separate `bootstrap` root module, state migrated into its own bucket; exceptions E1–E7; bucket `prevent_destroy` (pipeline cannot delete state; admin and root can, accepted) | 0003 |
| D4 | GitHub Actions; OIDC plan role (ReadOnlyAccess + lock + read Denies) and apply role (Admin + boundary P4); `production` environment gate; `main`-only enforced by S3 and the OIDC `ref` condition key (S15 dropped 2026-10-02, see §6); fork PRs fail closed; GitHub settings as exception E8; CI runs `fmt -check` and `validate` (both modules) before AWS authentication; P1 also requires `actor_id` (2026-10-06, replaces the fork-PR test) | 0004 |
| D5 | One AWS account on the Free plan; root and an IAM user admin, each with one synced passkey; CLI via `aws login`; Organizations, Identity Center, and a sensitive-data account at the Paid-plan transition; E6 made standing; emergency stop E9 | 0005 |
| D6 | AWS cost budget USD 20/month, credit-covered usage counted as cost; actual-spend alerts at 50/75/90/100% and 125% (= USD 25 ceiling); Budgets → unencrypted SNS topic → Amazon Q Developer → private Slack channel, plus email; in `bootstrap`; Slack authorization as exception E10; Slack stays on the Free plan | 0006 |
| D7 | One multi-Region trail and dedicated log bucket in `bootstrap`; alerts G1–G5 via EventBridge (Seoul hub) to the ADR 0006 topic; one external access analyzer in Seoul; seven protection Denies in P4; P3 requires `ap-northeast-2`; S15 dropped in favour of the `ref` key | 0007 |

### D7 progress (ADR 0007, written when D7-a to D7-d are decided)

Final text is ADR 0007 (2026-10-02). Changes made while writing it: every bootstrap rule uses `ENABLED_WITH_ALL_CLOUDTRAIL_MANAGEMENT_EVENTS`; G2 is a Seoul rule only (not forwarded); G3 covers every IAM write; names `bootstrap-trail`, `bootstrap-external-access`, `bootstrap-alerts`, `bootstrap-g1-root` etc., and `/bootstrap/event-forwarder`.

Sub-questions (agreed 2026-10-01): D7-a trail, D7-b alerts, D7-c IAM Access Analyzer, D7-d protection Denies.

- D7-a (2026-10-01): one multi-Region CloudTrail trail in `bootstrap`; management events, read and write;
  no data or Insights events; dedicated S3 log bucket in `ap-northeast-2` (versioning, public access blocked,
  CloudTrail write policy with `aws:SourceArn`); SSE-S3; log file validation on; no expiry; no CloudWatch Logs.
  `AssumeRoleWithWebIdentity` is confirmed read-only (IAM CloudTrail integration doc). Step 4: measure log storage and PUT cost.
- D7-b1 (2026-10-01): alert groups G1 root activity, G2 `pipeline-apply` assumed, G3 IAM identity and trust
  changes (incl. users, access keys, login profiles, identity providers), G4 logging and alert path changes,
  G5 budget changes. Not alerted: plan-role use, IAM user sign-in failures. Exact event names fixed in ADR 0007.
- D7-b2 (2026-10-01): hub in `ap-northeast-2`. Forwarding rules in us-east-1, us-east-2, and us-west-2 send to
  the Seoul default event bus (one IAM role under `/bootstrap/`); Seoul rules for G1–G5 target the ADR 0006 SNS topic.
  Rules that carry read-only events (G2) use `ENABLED_WITH_ALL_CLOUDTRAIL_MANAGEMENT_EVENTS` on both the
  forwarding rule and the Seoul rule.
  - G2 gap fix (2026-10-01, option A): P3 (ADR 0004) adds `aws:RequestedRegion` = `ap-northeast-2`, so every successful
    `pipeline-apply` assumption is logged in Seoul; other Regional endpoints and the global endpoint (`us-east-1`) are
    denied. Rejected: B, forwarding rules in all 17 default Regions (kept as the fallback); C, deactivating STS in unused
    Regions (console-only exception plus a P4 Deny). Trust-policy use of the key is unverified; a failure is fail-closed.
- D7-b3 (2026-10-01): alert message contents.
  - `role-session-name: ${{ github.run_id }}` in the apply and plan jobs; run ID only (unchanged on re-run, and an
    input transformer cannot split strings). The ADR 0004 "Workflow rules" line is added together with ADR 0007.
  - Amazon Q Developer custom notifications (`version` "1.0", `source` "custom", `textType` "client-markdown"),
    built by an EventBridge input transformer from an allowlist of scalar fields. Never map
    `responseElements.credentials`, `<aws.events.event>`, `<aws.events.event.json>`, whole objects, or free-text
    fields such as `errorMessage` (EventBridge does not escape extracted values).
  - G2: Time (UTC), Source IP, Region, Run (`roleSessionName`), Event ID; next steps: open the run link (mine only
    if I approved it and its time matches; UTC = KST - 9h), otherwise run E9 now and follow ADR 0005 "After each
    use", later look up the Event ID. A broken link or a time mismatch is itself an E9 trigger; the session name is
    a clue, not evidence.
  - G1, G3, G4, G5: Event, Who (`userIdentity.type` + `arn`), Time (UTC), Region, Source IP, Result (`errorCode` +
    `responseElements.ConsoleLogin`), Event ID; next step: match to a merged PR (E7) or my E6 task (pipeline changes
    show Who = `.../assumed-role/pipeline-apply/<run ID>`).
  - G2 rule state: see D7-b2. Cost: USD 0/month.
- D7-c (2026-10-01): one IAM Access Analyzer external access analyzer in `ap-northeast-2`, zone of trust = this
  account, in `bootstrap`; free. Seoul resources and all IAM roles only (an analyzer covers its own Region).
  No archive rules: filter keys cannot match the GitHub `sub`, so an archive rule for the two pipeline roles would
  also hide a widened trust. Seoul rule: source `aws.access-analyzer`, detail-type "Access Analyzer Finding",
  `status` ACTIVE, `isDeleted` false; message fields Resource, Resource type, `principal.AWS` or `principal.Federated`,
  Public, Error, Finding ID, Region. G4 also covers analyzer and archive-rule changes. The two pipeline roles produce
  findings at E4 (expected). Creating the analyzer creates `AWSServiceRoleForAccessAnalyzer` (note in ADR 0007).
- D7-d (2026-10-01): seven Deny statements in P4 (exact JSON with ADR 0007). Admin and root are out of scope (as in D3);
  G4 detects their changes.
  - Log bucket: everything except `s3:Get*`/`s3:List*` on the bucket; `s3:*` on its objects. Reason: the pipeline never
    needs the log files (CloudTrail omits `secretAccessKey`, so the session token is not the reason).
  - `cloudtrail:*`, `budgets:*`, `chatbot:*`, `access-analyzer:*` on `*`, reads included (option B-1; same shape as
    `DenyAccountLevelChanges`). Rejected: `NotAction` with `Resource: "*"` (denies every other service); resource-scoped
    Denies (miss actions without a resource type, e.g. `chatbot:DeleteSlackWorkspaceAuthorization`).
  - EventBridge, all Regions: everything except `events:Describe*`/`List*` on `rule/bootstrap-*`; `events:UpdateEventBus`
    on `event-bus/default` (a customer managed key encrypts rule patterns and targets); `events:PutPermission` and
    `RemovePermission` on `*` (no resource type).
  - SNS, all Regions: everything except `sns:Get*`/`List*` on `bootstrap-*` topics (subscription actions use the topic resource type).
  - Naming: every D6/D7 resource name starts with `bootstrap-`; the EventBridge and SNS Denies depend on it.
  - P4 size: 2,827 → about 3,786 of 6,144 characters (whitespace not counted).
  - Revisit when a pipeline-created role must read those four services (expected Phase 4–5): narrow the Deny through E7.

### Phase 0 review (2026-10-04)

Review of D1–D7 against design rules, security risk, and cost. Owner approved eight fixes (edited in place) and fixed
three document inconsistencies; all other findings were set aside.
- ADR 0007 (a): data events for the state bucket only (advanced event selectors); log bucket policy denies object deletes to every principal.
- ADR 0007 (b): G2 health check (no G2 message within 15 minutes of an approved apply = alert path broken).
- ADR 0005 E9: second switch, a Deny-all default version of `pipeline-boundary`, plus a CloudTrail sweep of the incident window.
- ADR 0004 (f): P4 `DenyOutsideSeoul` (AWS SSB ACCT.17 list); account-level S3 Block Public Access in `bootstrap`, `s3:PutAccountPublicAccessBlock` denied. P4 about 4,210 of 6,144 characters. EP-27, EP-28.
- ADR 0004 (e), ADR 0006: alert email and Slack IDs in the ignored `*.tfvars`, variables `sensitive = true`.
- ADR 0004 (e), ADR 0005: Terraform `~> 1.15.0`, AWS provider `~> 6.23`, one exact Terraform version in CI and on the laptop, modules local or exact.
- Fixed: ADR 0004 date 2026-09-25; ADR 0007 "nine rules"; "0 KRW" → "USD 0" in ADR 0004 and 0005.

### Design principles review (2026-10-04)

Review of the vision and ADR 0001–0007 against scalability, availability, latency, cost, security, and complexity. Owner decisions:
- Problem 1 (B): every infrastructure change, including create and start, is code applied through the pipeline after my approval (vision §4.1, §5.1, §6 Phase 6; README; CLAUDE.md §11). Containers on a host: decided in Phase 1.
- Problem 2 (A): AWS budget allocation in vision §5.1; each Phase confirms its line at Step 1 (CLAUDE.md §6).
- Problem 4 (B): each Phase sets availability and latency targets at Step 1 (CLAUDE.md §6, phase note template).
- Problem 6 (A): a provider-side monthly spend limit caps the AI API (vision §5.1); set in Phase 5.
- Problem 7: restructure P4 at 80% of its size limit; consider SCPs at the Paid-plan transition (ADR 0004, ADR 0005).
- Problem 8 (A): revisit triggers for application CI/CD roles and a second state key (ADR 0004).
- Problem 9 (A, B): trust boundaries and a control map before Step 4; simulator checks re-run on E7 changes (ADR 0003).
- Problem 10: ADR 0007 (f) wording fixed; vision §12 Q3 marked answered; README HITL wording updated with problem 1.
- Problems 3 and 5: moved to later Phases (§7).
- Vision §12 Q1 answered: the platform is for me; selected features may be lent to people I authorize, each with an account.

### ADRs

| ADR | Title | Status |
|---|---|---|
| [0001](../adr/0001-stage-1-cloud-provider.md) | Stage 1 cloud provider | Accepted |
| [0002](../adr/0002-iac-tool.md) | IaC tool | Accepted |
| [0003](../adr/0003-remote-state-and-bootstrap.md) | Remote state storage and bootstrap | Accepted |
| [0004](../adr/0004-pipeline-auth-and-approval-gate.md) | Pipeline authentication, role split, and approval gate | Accepted |
| [0005](../adr/0005-account-identity-structure.md) | Account identity structure | Accepted |
| [0006](../adr/0006-budget-alerts-and-delivery-path.md) | AWS budget alerts and alert delivery path | Accepted |
| [0007](../adr/0007-security-logging-baseline.md) | Security logging baseline and protection of the logging and alert path | Accepted |

## 4. Implementation log

| Date | Step | Result |
|---|---|---|
| 2026-10-05 | Trust boundaries | Drawn by the owner (two drafts); gaps checked against ADR 0003–0007; a reference map confirmed the owner's understanding |
| 2026-10-05 | Control map | Option B: the reference map's crossing table (7 crossings) and P4 Deny groups serve as the control map; no separate owner-drawn table |
| 2026-10-05 | GitHub account checklist | Owner done: passkey/security-key 2FA, unused sessions/tokens/keys/app grants removed; gh logged out |
| 2026-10-05 | .gitignore | Terraform patterns added (*.tfstate*, .terraform/, *.tfplan, *.tfvars) |
| 2026-10-06 | E8: production (S1–S4) | Created `production` (a misnamed draft environment was deleted first). GitHub REST GET: reviewer = Sweettreee, prevent_self_review false, branch policy `main` only, can_admins_bypass false (field not in the documented schema but returned) |
| 2026-10-06 | Repository IDs | <OWNER_ID> = 99391603, <REPO_ID> = 1373993467 (GitHub REST `repos/Sweettreee/Odyssey-Cloud`) |
| 2026-10-06 | Fork-PR test | No second account. Option A: P1 adds `actor_id` = my GitHub user ID (ADR 0004 (a)). Docs check: no GitHub sentence on `id-token` for fork PRs, no fork claim; AWS lists `actor_id` as a trust-policy key |
| 2026-10-06 | Real-token claim check | P1 shape (PR #6): sub = repo:Sweettreee@99391603/Odyssey-Cloud@1373993467:pull_request, ref = refs/pull/6/merge, actor_id = 99391603. P3 shape (workflow_dispatch on main, production approved): sub = …:environment:production, ref = refs/heads/main, actor_id = 99391603. All match ADR 0004 |
| 2026-10-06 | E1 | AWS account created (classic sign-up, `request_type=register`) on the Free plan, Basic Support; account name `SweetTree`; account ID 186972156090; USD 100 credits; root email = my existing personal Gmail (ADR 0005) |
| 2026-10-06 | E2 | Root MFA: one passkey (iCloud Keychain), registered in the console; no root access keys (console view). CLI checks for E1 and E2 run after E3 |
| 2026-10-06 | E6 (Activate IAM Access) | Root activated IAM user/role access to billing information (console) |
| 2026-10-06 | E3 | IAM user `odyssey-admin`: console password and one passkey (both iCloud Keychain), no access keys, policies AdministratorAccess and SignInLocalDevelopmentAccess (IAM console view, ADR 0005 6c) |
| 2026-10-06 | CLI checks (E1, E2, E3) and aws login | AWS CLI 2.37.9 (official install script); `aws login` asked for the admin passkey. sts get-caller-identity = 186972156090 / user/odyssey-admin; get-account-summary: AccountMFAEnabled 1, AccountAccessKeysPresent 0; odyssey-admin: 0 access keys, 1 MFA device, 2 attached policies, no inline policies or groups. "Configure AWS skills and the AWS MCP server" prompt declined |
| 2026-10-07 | Free plan service check | Owner: S3, CloudTrail, EventBridge, SNS, Budgets, Amazon Q Developer, IAM Access Analyzer listed on the AWS Free Tier page. Read-only calls all answered (0 resources each). The Amazon Q Developer API has no ap-northeast-2 endpoint; it is managed in us-east-2 (its console runs in us-east-2 only) |
| 2026-10-07 | E6 check | odyssey-admin can open the Billing and Cost Management console (Free plan status shown) |
| 2026-10-07 | E10 | Amazon Q Developer app installed through its console (us-east-2) as odyssey-admin; workspace `odyssey-cloud` State ENABLED; private alert channel created and @Amazon Q invited (channel ID kept for *.tfvars, not in the repo); 0 channel configurations (they are bootstrap code); AWSServiceRoleForAWSChatbot not created by E10 (NoSuchEntity) |
| 2026-10-07 | Terraform | 1.16.5 installed from the official binary (SHA256 OK) to ~/.local/bin |
| 2026-10-07 | M3 3.1 skeleton | `infra/bootstrap/`: versions.tf (`~> 1.16.0`, AWS `~> 6.23`), providers.tf (ap-northeast-2, allowed_account_ids, default_tags ManagedBy/Module), locals.tf (account ID), variables.tf (alert email, Slack IDs, sensitive). init -backend=false locked AWS provider 6.67.0; fmt and validate OK |
| 2026-10-07 | M3 3.2 state bucket | `state.tf`: bucket `odyssey-tfstate-186972156090` (<STATE_BUCKET>), versioning, SSE-S3 and bucket Block Public Access declared so plan shows drift (option B), prevent_destroy; `account.tf`: account-level S3 Block Public Access (ADR 0004 (f)). fmt and validate OK |
| 2026-10-07 | M3 3.3a pipeline roles | Policy JSON as files + templatefile() (option A2). `pipeline.tf`: GitHub OIDC provider (no thumbprint), `pipeline-plan` (P1, ReadOnlyAccess) and `pipeline-apply` (P3, AdministratorAccess; boundary added in 3.3c) under `/bootstrap/`; GitHub IDs in locals.tf. P1 and P3 files identical to ADR 0004 after placeholder substitution; rendered JSON checked; fmt and validate OK |
| 2026-10-07 | M3 3.3b P2 | `policies/p2-plan-inline.json` + `aws_iam_role_policy.pipeline_plan_p2` (name `p2-state-lock-and-read-denies`); bucket name taken from the state bucket resource. Identical to ADR 0004 P2 after substitution; rendered JSON valid; fmt and validate OK |
| 2026-10-07 | M3 3.3c P4 | `policies/p4-boundary.json` + `aws_iam_policy.pipeline_boundary` (`/bootstrap/pipeline-boundary`), attached as the `pipeline-apply` permissions boundary; log bucket name `bootstrap-cloudtrail-186972156090` (<LOG_BUCKET>) in locals.tf. P1–P4 identical to ADR 0004 after substitution; P4 4,214 of 6,144 characters; fmt and validate OK. Pre-apply validate-policy and simulator runs declined (owner, 2026-10-07); the simulator checks stay in M6 |
| 2026-10-07 | M3 3.4 budget alerts | `alerts.tf`: SNS `bootstrap-alerts` (topic policy: Budgets and `rule/bootstrap-*` publish only, option A), budget `bootstrap-monthly-cost` (USD 20, actual 50/75/90/100/125%, `include_credit = false`, email + topic), channel role `bootstrap-chatbot-channel` (no permissions), Q Developer channel `bootstrap-alerts` in us-east-2 with guardrail `AWSDenyAll` (option A; ADR 0006 updated), logging NONE. fmt and validate OK. If the Q Developer subscription fails at M4 because of the topic policy, add a statement then |
| 2026-10-07 | M3 3.5 trail | `trail.tf`: log bucket `bootstrap-cloudtrail-186972156090` (versioning, SSE-S3, Block Public Access, prevent_destroy (option A; ADR 0007 (a) updated)), bucket policy (two CloudTrail statements limited by `aws:SourceArn`, deny object deletes to every principal), trail `bootstrap-trail` (multi-Region, log file validation, advanced selectors: all management events and state bucket object data events). fmt and validate OK |
| 2026-10-07 | M3 3.6a event rules | `events.tf`: Seoul rules G1–G5 and `bootstrap-access-analyzer`, `bootstrap-forward` in us-east-1/us-east-2/us-west-2 (union of G1, G3, G4, G5; G4 as seven parts, no nested `$or`), role `/bootstrap/event-forwarder` (PutEvents to the Seoul default bus), all rules `ENABLED_WITH_ALL_CLOUDTRAIL_MANAGEMENT_EVENTS`. fmt and validate OK. `aws events test-event-pattern` with hand-built CloudTrail-shaped events: 30 cases (match and no-match for every rule and the forwarder), 0 failed; real events are checked in M6 |
| 2026-10-07 | M3 3.6b alert messages | `events.tf`: input transformers for the six Seoul rules to SNS `bootstrap-alerts` (Q Developer custom notifications; allowlisted fields per ADR 0007 (b): 9 for G1/G3/G4/G5, 5 for G2, 8 for Access Analyzer); raw-text templates because jsonencode() escapes `<` as `\u003c` (checked); run link as a plain URL. Local render with sample values: valid JSON, every placeholder defined and used, length limits met. `checks/test_event_patterns.py` kept in the repo for E7 re-runs (delete when no longer useful). Slack rendering is checked in M6 |
| 2026-10-07 | M3 3.7 analyzer | `analyzer.tf`: `bootstrap-external-access`, type ACCOUNT, ap-northeast-2. Creating it adds `AWSServiceRoleForAccessAnalyzer` (record at M4). fmt and validate OK |
| 2026-10-07 | M3 3.8 local plan | Owner ran `AWS_PROFILE=odyssey-admin terraform plan -out=bootstrap.tfplan` in `infra/bootstrap` (local state, empty): Plan: 44 to add, 0 to change, 0 to destroy, matching the 44 resources in the code. `terraform.tfvars` and the plan file are git-ignored. Next: PR with the plan summary (E7), merge, then M4 |
| 2026-10-07 | M3 PR | Bootstrap code merged to `main` through a PR with the plan summary (E7 procedure) |
| 2026-10-07 | M4 E4 apply | Owner applied from merged `main` with local state: 44 added. Checks (read-only): `terraform plan` No changes (E4 check); trail IsLogging true, no delivery error; pipeline-apply boundary = pipeline-boundary; SNS subscription https://global.sns-api.chatbot.amazonaws.com (topic policy option A works); Q Developer channel ENABLED with AWSDenyAll; 6 Seoul rules and 3 forwarders in state ENABLED_WITH_ALL_CLOUDTRAIL_MANAGEMENT_EVENTS; Access Analyzer active findings only for pipeline-plan and pipeline-apply (expected). Service-linked roles created by AWS outside code: AWSServiceRoleForAccessAnalyzer and AWSServiceRoleForAWSChatbot (the latter appeared with the channel configuration, not at E10) |

## 5. Verification

### Exit criteria
- [ ] Every resource exists because of code.
- [ ] Infrastructure changes reach the cloud only through the pipeline.
- [ ] Test alerts for every AWS budget threshold reach Slack.

Interpretation (ADR 0003): criterion 1 excludes resources created by exceptions E1–E6 and E10; criterion 2 applies to the `main` module, while `bootstrap` follows E7.

## 6. Open issues
- ~~Bootstrap exceptions must be recorded in an ADR.~~ Resolved: ADR 0003 (E1–E7).
- ~~How exceptions are controlled and how exit criterion 1 relates to them.~~ Resolved: ADR 0003 control rules and exit criteria interpretation.
- ~~D7: decide whether CloudTrail lives in `bootstrap` or `main`.~~ Resolved 2026-10-01: `bootstrap` (D7-a).
- ~~Vision §5.1 "no ClickOps" had no exception clause.~~ Resolved 2026-09-25: owner approved adding "except for exceptions recorded in an ADR" to vision §5.1 (matches CLAUDE.md §11).
- ~~Accepted ADRs could not be corrected during their Phase.~~ Resolved 2026-09-28: CLAUDE.md §9 and `docs/adr/README.md` allow in-place edits while the ADR's Phase is in progress.
- ~~Budget definition.~~ Resolved 2026-09-29: owner approved separate USD budgets (vision v0.7).
- ~~D7-b3: keep a G2 Subject field only if D7-b2 also matches failed assumption attempts.~~ Resolved 2026-10-02: G2 alerts on successful assumptions only; no Subject field.
- ~~D7-b3: response when root activity is not mine.~~ Resolved 2026-10-02: a Step 4 runbook.
- ~~D7-b2 G2 gap: an assumption through a Region without a forwarding rule raised no G2 alert.~~ Resolved 2026-10-01: option A (§3 D7-b2).
- ~~ADR 0004 [A17] looks outdated.~~ Resolved 2026-10-02 (option B): drop S15. P1 checks the default `sub`
  (`...:pull_request`) plus `token.actions.githubusercontent.com:ref` like `refs/pull/*/merge`; P3 checks the default
  `sub` (`...:environment:production`) plus `ref` = `refs/heads/main`. `sub` stays because IAM requires it for GitHub.
  Fallback if the `ref` key does not match in Step 4: restore S15 (option A).
- Free plan ends on 2027-04-06 or when the USD 100 credits run out, whichever comes first (Billing console, 2026-10-06).
  This is the ADR 0005 trigger for the Paid-plan transition.
- (M3) The Amazon Q Developer API has no ap-northeast-2 endpoint; create the Slack channel configuration with
  `region = "us-east-2"` (AWS provider 6.x Region-aware resources; no provider alias). Seoul SNS topics are supported.
- (M5) The apply workflow must request the role by its full ARN with the path (`arn:aws:iam::186972156090:role/bootstrap/pipeline-apply`): G2 matches `requestParameters.roleArn` exactly (inference: CloudTrail records the ARN as requested).

### Hand-offs from ADR 0004–0006
- ~~D5: admin identity type and MFA (EP-13); admin role trust has no service principal (EP-20); AWS human identity vs. the GitHub approval path (EP-24, solo-approval limit); AWS Organizations + RCP (EP-21); whether secrets move to a separate AWS account (ADR 0004 (e)).~~ Done: ADR 0005.
- ~~D6: delivery path for the apply-role assumption alert (E9 trigger, ADR 0005) and security alerts.~~ Done: ADR 0006.
- ~~D7: protect CloudTrail, its log bucket, and budget alerts; external access analyzer; alerts (EP-21, EP-24, E9, root sign-in); ADR 0006 hand-offs.~~ Done: ADR 0007.

### Step 4 checklist (from ADR 0004–0006)
- Before the first Step 4 change: I draw the trust boundaries and a one-page control map (threat → EP → control → check) on a blank page (vision §7.1). Done 2026-10-05 (option B, see §4).
- GitHub account checklist (2FA passkey/security key, remove unused tokens/keys/grants, check `gh auth status` scopes) before creating AWS resources. Done 2026-10-05 (see §4).
- `.gitignore`: `*.tfstate*`, `.terraform/`, `*.tfplan`, `*.tfvars` before E4. Done 2026-10-05 (see §4).
- E8 ordering: create `production` and verify S1–S4 before E4. Done 2026-10-06 (see §4).
- ~~Fork-PR `id-token` test before E4.~~ Replaced 2026-10-06 by the P1 `actor_id` condition (ADR 0004 (a)); accept path checked in Step 4.
- `gh` login hygiene: log in only when needed and `gh auth logout` afterwards, or use a short-lived read-only token in `GH_TOKEN`.
- Fill `<OWNER_ID>`/`<REPO_ID>`/`<ACTOR_ID>`; verify the exact `sub`, `ref`, and `actor_id` values from a real token, printing only those three claims (never the whole token); confirm `gh api` endpoints for E8 checks. Done 2026-10-06 (see §4); placeholders are filled when the trust policies are written.
- E1 on the Free plan; right after E1, check that the services Phase 0 needs are available on the Free plan. Done 2026-10-07 (see §4).
- E2/E3: root and the admin each register one synced passkey (iCloud Keychain). E6: root runs "Activate IAM Access" once. Done 2026-10-06/07 (see §4).
- Pin Terraform `~> 1.16.0` (1.16.5; one exact version in CI and on the laptop), AWS provider `~> 6.23`, AWS CLI `>= 2.32.0`; modules local or exact; no `source_profile` role chaining with `aws login`.
- Verify that the admin's MFA is asked during `aws login`. Done 2026-10-06 (see §4).
- P4 includes `iam:DeleteLoginProfile`; make sure a `bootstrap` apply does not remove `emergency-deny-all` (E9).
- E10 before E4. Check whether E10 creates the `AWSServiceRoleForAWSChatbot` service-linked role (record it under E10 if so). Verify that budget and custom notifications render with an empty channel role and guardrail. E10 done 2026-10-07 (see §4); the service-linked role did not appear at E10, so recheck after the channel configuration is applied (M4). The render check stays open.
- Confirm how the current Budgets API and AWS provider express `IncludeCredit`. Alert email and Slack workspace and channel IDs go in the ignored `*.tfvars` with `sensitive = true`; check that plans attached to PRs do not show them. IncludeCredit done 2026-10-07: API default `true`; provider `cost_types { include_credit = false }` counts credit-covered usage (see §4).
- Exit criterion 3: a temporary USD 0.01 budget (credits counted, same five notifications and topic), added and removed through E7; every alert arrives in Slack and by email.
- (D7) Alert render test: empty variables, " | " separators, the Slack link containing `<roleSessionName>` (fall back
  to a plain URL if the nested angle brackets conflict), and whether `\n` in the description renders as a line break.
- (D7) On the first real G2 event, check that `awsRegion` is `ap-northeast-2` and
  `additionalEventData.RequestDetails.endpointType` is `regional`; root `ConsoleLogin` is recorded in us-east-1,
  us-east-2, or us-west-2. A working Seoul apply shows that P3 evaluates `aws:RequestedRegion`; prove once that an
  assumption through another Region is denied. If the condition blocks the Seoul apply, switch to option B.
- (D7) IAM policy simulator: each D7-d Deny blocks its target, and normal `main` actions (for example creating EC2 and S3
  resources) stay allowed. Also try the log bucket through an S3 access point (expected: denied).
- (Review) Policy simulator: `DenyOutsideSeoul` blocks a call to another Region and allows Seoul and the listed global
  services; the pipeline cannot change account-level S3 Block Public Access; a Deny-all default version of
  `pipeline-boundary` blocks a role that carries it (E9 second switch).
- Record each policy simulator check (principal, action, resource, expected result) so E7 can re-run it (ADR 0003).
- (Review) Deleting a log object is denied; state reads and writes appear as data events; measure their cost.
- (Review) The root-activity runbook includes the G2 health check.

## 7. Carry-over to next phase
- (Phase 1) Add an `ec2:InstanceType` allowlist to P4 when compute arrives (ADR 0004 (f)).
- (Phase 1) Decide whether containers on a host follow problem 1 (code, approval, pipeline) or count as operations (design principles review).
- (Phase 2) Application CI/CD: compare a new GitHub OIDC role with deploys through the apply pipeline (ADR 0004 "Revisit when").
- (Phase 4) Decide how to review CloudTrail logs older than the 90-day Event history.
- (Phase 4) Decide which automatic actions need confirmation: first-level recovery, and Windows auto-stop for Phase 7. Under problem 1 (B), an automatic stop cannot wait for a pipeline approval (design principles review, problem 3).
- (Phase 5) Set a provider-side monthly spend limit for the AI API (vision §5.1).
- (Phase 6) Decide how a confirmation for a delegated task with external effects is authenticated; infrastructure changes use the pipeline approval (design principles review, problems 1 and 5).
- (Phase 7) Power state can be code (`aws_ec2_instance_state`: `running` or `stopped`); check how an instance that stops itself fits with it (problems 1 and 3).
