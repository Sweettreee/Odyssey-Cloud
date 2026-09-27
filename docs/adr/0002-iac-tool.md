# ADR 0002: IaC tool

- **Status:** Accepted
- **Date:** 2026-09-21
- **Phase:** 0

## Context
Every Phase 0 building block (remote state, pipeline, roles) sits on the IaC tool.
Constraints:

- Strong AWS support (ADR 0001).
- Must not have to be thrown away for Stage 2 (own hardware), per `docs/vision.md` §5.2.
- Remote state with locking.
- A clear plan (compare only) / apply (change) split, for plan-on-PR and apply-after-merge.
- Simple enough that a beginner can see what each run will do.
- Relevant to the job market. Free to use.

## Options considered

| Option | Pros | Cons | Monthly cost impact |
|---|---|---|---|
| A. Terraform | Most mature AWS provider. Multi-provider, so usable for Stage 2. Clear plan/apply. Most job postings and learning material. | HCL is a new language. BUSL license (irrelevant for personal use). | 0 (tool free; state storage decided in D3) |
| B. OpenTofu | Same HCL and providers as A. Fully open source (MPL 2.0). | Smaller community; occasional version/command drift from Terraform material. | 0 |
| C. AWS CDK | AWS-native, fastest support for new services. General-purpose language. | AWS-only, so it is discarded at Stage 2. Two layers to learn (language + CloudFormation). | 0 |
| D. Pulumi | Multi-provider, general-purpose language. | Small community, little job demand, least learning material. | 0 |

## 6-Layer check (chosen option)

| Layer | Notes |
|---|---|
| Traffic | Not applicable. |
| Compute | Not applicable. |
| Data | State can contain secrets: remote S3 backend, encrypted, never in Git (D3). |
| Security | The tool has no permissions of its own; the pipeline role's permissions are its permissions (D4). |
| Cost | Tool is free. State storage cost is effectively zero. |
| Observability | `terraform plan` output is the change preview; attached to each PR (D4). |

## Decision
Terraform. It meets every constraint, and it applies the same criterion as ADR 0001:
the richest documentation and references, and the most job-market relevance.
C fails the Stage 2 portability principle; D lacks community and material.

## Consequences
- Easier: abundant examples; skills transfer directly to OpenTofu if ever needed.
- Harder: HCL must be learned before Step 4; version pinning is required so plans are reproducible.
- Switching to OpenTofu later is a binary swap with the same code, so lock-in risk is low.

## Revisit when
- Terraform's license changes in a way that affects personal use.
- A Stage 2 target has no usable Terraform provider.
