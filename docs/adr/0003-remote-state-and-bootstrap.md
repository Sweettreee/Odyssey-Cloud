# ADR 0003: Remote state storage and bootstrap

- **Status:** Accepted
- **Date:** 2026-09-23
- **Phase:** 0

## Context
Terraform (ADR 0002) needs a remote state store with locking, shared by me and the pipeline.
State can contain secrets. Some things must exist before any IaC can run (the bootstrap
problem), yet Phase 0 exit criterion 1 says every resource exists because of code.
This ADR decides where state lives, how the bootstrap resources are created, and how
the actions that cannot be done as code are listed and controlled.

## Options considered

### State storage

| Option | Pros | Cons | Monthly cost impact |
|---|---|---|---|
| A. S3 with native lock file (`use_lockfile`) | One resource. Current recommended locking. Moves to S3-compatible storage in Stage 2. | Needs a recent Terraform version (verify in Step 4). | ~0 |
| B. S3 + DynamoDB lock table | Most common in older material. | Deprecated direction. One more resource. DynamoDB is AWS-only. | ~0 |
| C. HCP Terraform (hosted) | No AWS bootstrap for state. | Outsources the part I am here to learn. My infrastructure inventory lives with a third party. Pulls D4 toward its workflow. | 0 (free tier) |

### Bootstrap resources (state bucket, OIDC provider, pipeline roles)

| Option | Pros | Cons | Monthly cost impact |
|---|---|---|---|
| A. Create by hand, record as exception, import later | Simplest. | More exceptions; desired state not reviewable or drift-checkable until imported. | 0 |
| B. Terraform in the main module, local state then migrate | Everything in code. | The pipeline could change its own role and its own state store. | 0 |
| C. Separate `bootstrap` root module, local state then migrate into the bucket it creates (C-1) | Desired state in code: reviewable and drift-checkable. The pipeline cannot modify its own permissions or state store. A failure in main cannot spread to them. | Two root modules. Bootstrap changes are applied by a human (E7). | 0 |

## 6-Layer check (chosen option)

| Layer | Notes |
|---|---|
| Traffic | Not applicable. |
| Compute | Not applicable. |
| Data | Bucket: versioning on, default encryption, all public access blocked. State never in Git. |
| Security | Bootstrap owns the pipeline roles and the state bucket; the pipeline has no permission on the bootstrap module. No identity gets bucket delete permission. |
| Cost | ~0 (KB-scale objects, few requests). |
| Observability | Bucket and role changes appear in CloudTrail management events (D7). Bootstrap drift is checked with `terraform plan`. |

## Decision

**State:** S3 with the native lock file (option A). B is the deprecated direction;
C outsources the learning goal and hands my infrastructure inventory to a third party.
Pin the Terraform version in Step 4 and confirm `use_lockfile` support in the official docs;
fall back to B only if it is not supported.

**Bootstrap:** separate `bootstrap` root module (option C), with its state migrated into
the bucket it creates (C-1), for two reasons:

1. The desired state of the state bucket, OIDC provider, and roles is declared in code,
   so it can be reviewed and checked for drift, and every resource after bootstrap follows the IaC rule.
2. Separating bootstrap from main means the pipeline cannot modify its own permissions or
   its state store, and a failure in main cannot spread to them.

## Bootstrap exceptions

Only the items below may be done outside code. Any other manual change is a violation.

| # | Exception | Kind | Who / how | Read-only check |
|---|---|---|---|---|
| E1 | Create the AWS account | One-time | Me / web sign-up | `aws sts get-caller-identity` returns the account ID |
| E2 | Register root MFA | One-time | Root / console | `aws iam get-account-summary` shows `AccountMFAEnabled: 1` |
| E3 | Create the first admin identity | One-time | Root / console (IAM user, ADR 0005) | IAM console, read-only: the admin user has console access, one MFA device, no access keys, and the policies `AdministratorAccess` and `SignInLocalDevelopmentAccess` |
| E4 | First `bootstrap` apply with local state | One-time | E3 identity / laptop | `terraform plan` in `bootstrap` shows no changes |
| E5 | Migrate bootstrap state into the bucket (`terraform init -migrate-state`) | One-time | E3 identity / laptop | `aws s3api get-bucket-versioning` shows `Enabled`; no local state file remains |
| E6 | Root-only tasks, only when required: "Activate IAM Access" to the Billing console (once), and any root-only task that becomes necessary later, such as recovering the admin identity (ADR 0005) | Standing | Root / console | `aws iam get-account-summary` shows `AccountMFAEnabled: 1` and `AccountAccessKeysPresent: 0`; the admin can open the Billing console |
| E7 | Every change to the `bootstrap` module | Standing | E3 identity / laptop, see below | `terraform plan` in `bootstrap` shows no changes; each apply matches a merged PR (CloudTrail, D7) |

> Amended by ADR 0004 (exception E8), ADR 0005 (exception E9), and ADR 0006 (exception E10).

**E7 procedure:** change via pull request only, with the local `terraform plan` output
attached; review and merge; apply only from the merged `main`, with the E3 identity.
This covers later changes too (for example, widening the apply role's permissions),
so keep the `bootstrap` module small and rarely changed.

**Control rules**
1. This table is the only list of exceptions.
2. Every exception has a read-only check, run during Phase 0 Step 5 verification.
3. An exception that later becomes possible as code is moved into code and removed from the list
   (by a new ADR that supersedes this one).

**Exit criteria interpretation**
- Criterion 1: every resource, except those created by E1–E6 and E10, exists because of code.
- Criterion 2: changes to the `main` module reach the cloud only through the pipeline;
  the `bootstrap` module follows E7.

## Consequences
- Easier: the pipeline's blast radius excludes its own permissions and state; bootstrap drift is visible.
- Harder: two root modules to maintain; bootstrap changes need a human apply and discipline.
- The bucket holds its own module's state; it is protected by versioning and by granting delete to no one.
- Actions taken before CloudTrail is on (D7) leave no audit trail except this ADR,
  so Step 4 turns on CloudTrail as early as possible. Whether CloudTrail belongs to
  `bootstrap` or `main` is decided in D7.

## Revisit when
- Terraform removes or changes `use_lockfile`.
- A safe way appears to apply `bootstrap` without a human, without giving the pipeline power over itself.
- Stage 2 planning starts (state backend moves to S3-compatible storage).
