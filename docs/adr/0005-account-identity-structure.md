# ADR 0005: Account identity structure

- **Status:** Accepted
- **Date:** 2026-09-28
- **Phase:** 0
- **Fills in:** ADR 0003 exception E3 (form of the first admin identity)
- **Amends:** ADR 0003 exception table (adds exception E9)

## Context
Phase 0 scope includes "Account hardening: root lockdown, MFA, and no long-lived keys" (`docs/vision.md` §6, Phase 0).
The human admin also runs E4, E5, and E7 from a laptop (ADR 0003), so it needs CLI credentials without access keys.
ADR 0004 handed several items to D5: EP-13, EP-20, EP-21, EP-24, and a separate account for secrets.
I want to keep the Free plan and its credits for as long as possible.

Facts this ADR relies on (all checked 2026-09-28):
- The Free plan "ends after six months or when your credits are fully used - whichever occurs first"; after that
  "your account closes automatically", and it can be upgraded to the Paid plan within 90 days [F2].
- Free plan accounts "will automatically upgrade to paid plan if you join AWS Organizations" [F2], and then
  "you will no longer be able to use or earn credits offered under the Free Tier" [F1]. Creating an organization
  from a free tier account: "Your free tier credits expire immediately." [I3]
- A normal upgrade keeps the credits: "your remaining Free Tier credits will automatically apply to future AWS bills
  until they expire"; an upgrade by joining an organization does not [F3].
- The Identity Center access portal for AWS accounts works only with an organization instance in the
  Organizations management account [I1].
- "AWS Organizations can have IAM Identity Center enabled only in a single AWS Region." Changing the Region
  requires deleting the instance and creating a new one [I3].
- "SCPs don't affect users or roles in the management account" [O2]. "RCPs don't affect resources in the
  management account" [O3].
- "New accounts you create in AWS Organizations have no root user credentials by default." After centralizing
  root access, root credentials can be deleted from existing member accounts [R2]. This applies to member accounts only [R1].
- `aws login` (AWS CLI >= 2.32.0) turns a console sign-in (root, IAM user, or federation) into temporary
  credentials. The session lasts up to 12 hours, and the credentials are cached in `~/.aws/login/cache`.
  An IAM user needs the `SignInLocalDevelopmentAccess` managed policy [C1][C2].
- Terraform 1.15.0 changelog: "backend/s3: Support authentication via `aws login`" [T3].
- AWS provider: a maintainer comment on #45316 says `aws login` works with provider ">= 6.23.0" [T4].
  The 6.23.0 changelog does not mention it [T5].
- With `aws login`, role chaining through `source_profile` behaves differently in Terraform and in the AWS CLI.
  Issue #45817 is still open [T6].
- IAM, AWS Organizations, and IAM Identity Center are offered at no additional charge [P1][O1][I2].

## Options considered

| Option | Pros | Cons | Monthly cost impact | Free Tier credit impact |
|---|---|---|---|---|
| A. One account, IAM user admin, permanently | Simplest. No new concepts. | Never reaches account isolation, SCP, or RCP. Not the AWS-recommended Identity Center setup. | USD 0 | Kept |
| B. One account as management account + Identity Center | AWS-recommended sign-in. | SCP and RCP have no effect on the management account [O2][O3]. Workloads would have to leave the management account to reach C. | USD 0 | Lost immediately [I3] |
| C. Management account + workload member account now | Account isolation. SCP and RCP apply to the member. The member's root credentials can be removed [R2]. | Loses the credits now. Most manual steps. | USD 0 | Lost immediately [F1] |
| D. A now, C at the Paid-plan transition | Keeps the credits. Simple now. Reaches C later without moving any infrastructure. | A's limits until the trigger. The human sign-in path changes once, later. | USD 0 | Kept until the trigger; see Consequences |

Chosen: D.

## 6-Layer check (chosen option)

| Layer | Notes |
|---|---|
| Traffic | Not applicable. Human sign-in goes to the AWS sign-in endpoint; nothing inbound. |
| Compute | Not applicable. |
| Data | No new data store. The `aws login` cache (`~/.aws/login/cache`) on the laptop holds temporary credentials, so it is a credential file under CLAUDE.md §10. |
| Security | Root has MFA, no access keys, and is sealed. The admin is an IAM user with MFA and no access keys. The admin is protected from the pipeline only by P4 (ADR 0004). No SCP or RCP until the trigger. |
| Cost | USD 0 per month for every option [P1][O1][I2]. The credits stay until the trigger. At the transition, the sensitive-data account adds USD 1/month per KMS key [K1]; secrets cost USD 0.40/month each wherever they live [S2] (both checked 2026-09-28). |
| Observability | Admin and root API calls are recorded by CloudTrail (D7). Alerts on root use are decided in D6/D7. |

## Decision

### Stage 1 (now, Free plan)
- One AWS account (E1) on the Free plan, to keep the Free Tier credits.
- Root: MFA registered (E2), then sealed. No root access keys.
- Root email: my existing personal Gmail address (decided 2026-10-06 at E1). Known limits: AWS recommends that the
  root email "should not be used for other purposes" [M2]; that Gmail account plus my phone number is a root
  recovery path [M2]; one person holds both recovery channels. The Gmail account has no passkey or security-key
  2FA (owner's choice, 2026-10-06); accepted.
- Admin identity (E3): one IAM user with a console password and MFA. Policies: `AdministratorAccess` and
  `SignInLocalDevelopmentAccess`. No access keys.
- CLI for E4, E5, and E7: `aws login` (AWS CLI >= 2.32.0). Temporary credentials, up to 12 hours.
- Terraform `~> 1.15.0` (the S3 backend supports `aws login` only from 1.15.0 [T3]) and AWS provider `~> 6.23`
  (`aws login` works from 6.23.0 [T4]); bounds per ADR 0004 (e) "Versions".
- Do not use `source_profile` role chaining with `aws login` (#45817 [T6]).

### Trigger
Upgrading to the Paid plan: when the credits run out or the 6-month Free plan ends, whichever comes first.

### Transition (at the trigger; reaches option C)
1. Create a new management account. Enable Organizations and IAM Identity Center in `ap-northeast-2`
   (changing the Region later means deleting the instance [I3]).
2. Invite the existing account as a member. Enable centralized root access and delete the member's root credentials [R2].
3. Assign a permission set to the member account and switch the CLI to `aws sso login`. Delete the IAM user admin.
4. The state bucket, pipeline roles, OIDC provider, and CloudTrail stay in the existing account (now a member).
   Only the human sign-in path and the secrets (step 5) move.
5. Create the sensitive-data account as a new member account (new member accounts have no root credentials [R2]).
   Move the secrets there, encrypted with a customer managed KMS key; the AWS managed key cannot be used
   across accounts [S1].
6. Record the transition in a new ADR that supersedes the affected exceptions (ADR 0003 control rule 3). That ADR also decides which account-wide P4 Denies move to SCPs (ADR 0004 "Revisit when").

### Why D
- A as a permanent state never reaches account isolation, SCP, or RCP.
- B loses the credits, SCP and RCP have no effect on it, and it blocks a clean move to C.
- C now loses the credits immediately, which conflicts with my plan to use the Free plan.
- D keeps the credits now and reaches C without moving any infrastructure.

## Exception E9 (amends ADR 0003)

| # | Exception | Kind | Who / how | Read-only check |
|---|---|---|---|---|
| E9 | Emergency stop of the pipeline apply role | Standing (emergency only) | Me, IAM user admin with `aws login` + MFA / (1) attach the inline policy `emergency-deny-all` (Deny `*` on `*`) to `pipeline-apply`; (2) create a Deny-all version of `pipeline-boundary` and set it as the default version; restore both after recovery | `aws iam list-role-policies --role-name pipeline-apply` shows no `emergency-deny-all`, and `aws iam get-policy` on `pipeline-boundary` shows the reviewed default version, in normal operation; each use has an incident record in a pull request |

- Trigger: an alert for an apply-role assumption that I did not start. D7 decides what the alert shows,
  so that I can tell my own applies from others.
- Why two switches (added 2026-10-04, Phase 0 review): a hijacked apply session can first create its own role with
  the P4 boundary and `AdministratorAccess` that trusts an outside account (ADR 0004 EP-21); the inline Deny on
  `pipeline-apply` does not reach it. Every role or user the pipeline creates must carry `pipeline-boundary`
  (ADR 0004 `RequireBoundaryOnIamWrites`), and a managed policy's default version "is in effect for all of the
  principal entities … that the managed policy is attached to" [V1]. Inference: a Deny-all default version blocks
  every identity the pipeline created at once; verify that a boundary behaves this way with the policy simulator in
  Step 4. A managed policy keeps at most five versions [V1]: if five exist, delete the oldest non-default version
  first. Trade-off: from Phase 1, legitimate workload roles also stop during the incident.
- After each use: search CloudTrail in every Region for events from `pipeline-apply` sessions in the incident window;
  list the roles, trust policies, and resource policies they created or changed, and stop any compute they started.
  Then secure the GitHub account, and record the incident and the restoration of both switches in a pull request
  (E7 procedure).
- Step 4 (inference): make sure a `bootstrap` apply does not silently remove `emergency-deny-all` or restore
  `pipeline-boundary` while E9 is in place.
- ADR 0003 control rules apply to E9.

## Consequences
- Easier: one account and one sign-in path while Phase 0 is built; no access keys anywhere.
- Harder: the human sign-in path changes once, at the trigger.
- Known limits accepted until the trigger:
  - No SCP or RCP. The admin is protected from the pipeline only by P4.
  - The admin and the pipeline share one account (ADR 0004 (e) known limit: the apply role can read secrets).
  - Not the AWS-recommended Identity Center setup.
- If the trigger is the 6-month end and credits remain, joining the organization forfeits them [F1],
  although a normal upgrade alone would keep them [F3].
- The new management account has its own root user. Centralized root access covers member accounts only [R1][R2],
  so that root user needs its own MFA and sealing (inference).
- The Free plan does not include "a subset of AWS services" [F3]. Whether every service Phase 0 needs is
  available on the Free plan could not be confirmed from the official pages; check right after E1 in Step 4.
- The docs do not state explicitly that the admin's MFA is enforced during the `aws login` browser flow [C1][C2].
  They say that `aws login` is how to get CLI credentials when using a passkey or security key [M1].
  Inference: it uses the console sign-in, so MFA applies. Verify in Step 4.

## Open items (all resolved in D5)
1. Resolved (option A): add `iam:DeleteLoginProfile` to the P4 statement `DenyLongLivedCredentials`,
   next to `iam:CreateLoginProfile` and `iam:UpdateLoginProfile`. Known limit: `iam:UpdateUser`
   (renaming the admin) remains a lockout path, not a takeover path. Recorded in ADR 0004 (P4, EP-26).
2. Resolved: ADR 0004 is edited in place, because Phase 0 is still in progress (CLAUDE.md §9):
   Terraform `>= 1.15.0` in (e), and `iam:DeleteLoginProfile` in P4 (EP-26).
3. Resolved (option A): no separate account before the trigger. Until then, secrets stay in the main account's
   Secrets Manager, and the ADR 0004 (e) known limit applies (the apply role can read secrets). The sensitive-data
   account is created at the transition (step 5). Reason: for a personal project, the loss or risk is not severe
   enough to justify another account and its exceptions before the trigger. Known limit (inference): the apply role
   can change the trust policy of any role that carries the P4 boundary, so even a separate account does not protect
   a secret whose reader role is managed by the pipeline. It protects secrets read only by principals outside the
   pipeline, and the secret and key policies.
4. Resolved (option B): GitHub-side controls and detection stay as in ADR 0004 (EP-24). In addition, the AWS human
   identity is the emergency stop: when an alert shows an apply-role assumption that I did not start (D7 alert,
   D6 delivery), I sign in with `aws login` and MFA and attach an inline Deny-all policy to `pipeline-apply`.
   This blocks existing and new sessions; "Revoke active sessions" alone does not block new sessions [R3].
   The pipeline cannot remove the policy (`DenyBootstrapIamChanges`, ADR 0004). This shortens a takeover;
   it does not prevent the first damage. Recorded as exception E9. Extended on 2026-10-04: E9 also sets a Deny-all
   default version of `pipeline-boundary` (see Exception E9).
5. Resolved: not applicable while the admin is an IAM user, because only roles can be passed to a service
   (`iam:PassRole` has the resource type `role` only [A3]). At the transition, the admin becomes an
   `AWSReservedSSO_` role, which "is only modifiable by AWS" and is changed only from the Identity Center
   console in the management account [I4]. Recheck in the transition ADR.
6. The MFA type, the E6 root-only settings, and the E3 read-only check:
   a. MFA type, resolved (option A): root (E2) and the admin (E3) each register one synced passkey in
      iCloud Keychain [M1]; their passwords are kept in the same iCloud Keychain. Reason: I already use
      Apple Keychain; it is simple and needs no purchase. iCloud Keychain is end-to-end encrypted and any
      Apple Account using it requires two-factor authentication [AP1]. Recovery: the passkey through iCloud
      Keychain escrow [AP1]; root through the registered email and phone [M2]; the admin's MFA is
      re-registered by root (inference). Known limits (inference): AWS recommends several MFA devices [M1],
      but only one is registered; the Apple Account, or an unlocked Mac, holds both the password and the
      passkey, so the two factors are not independent.
   b. E6 root-only settings, resolved: E6 becomes Standing and covers "Activate IAM Access" to the Billing
      console (once) [B1] and any root-only task that becomes necessary later, such as recovering the admin
      identity [R1]. ADR 0003 is edited in place. S3 MFA delete is not used: it needs a six-digit code from a
      TOTP device [S3M], and root has only a passkey (6a).
   c. E3 read-only check, resolved: a manual look in the IAM console. The admin user's page shows console
      access, one MFA device, no access keys, and the two policies [MS]. Reason: E3 is a one-time job, so a
      manual check is enough. `aws login` is proven in practice by E4. ADR 0003 is edited in place.
7. Resolved: manual check. AWS sends periodic email alerts about the credit balance and the approaching end
   of the Free plan [FT1]; I check the plan state myself in the console home or with
   `aws freetier get-account-plan-state` [FT1][FT2]. No automation. If the date is missed, the account can
   still be upgraded within 90 days of the notification [F1].

## Revisit when
- The trigger fires (run the transition and write the new ADR).
- AWS changes the Free plan terms for Organizations or credits.
- #45817 is fixed, or role chaining becomes necessary.
- Before the trigger, a secret appears that is read only by principals the pipeline does not manage (open item 3).
- Identity Center can grant access to AWS accounts without Organizations.

## Sources
- [F1] AWS Free Tier terms: https://aws.amazon.com/free/terms/
- [F2] Choosing a plan (Billing User Guide): https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/free-tier-plans.html
- [F3] AWS Free Tier FAQs: https://aws.amazon.com/free/free-tier-faqs/
- [FT1] Tracking your AWS Free Tier usage: https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/tracking-free-tier-usage.html
- [FT2] Free Tier API, GetAccountPlanState: https://docs.aws.amazon.com/aws-cost-management/latest/APIReference/API_freetier_GetAccountPlanState.html
- [I1] Identity Center organization and account instances: https://docs.aws.amazon.com/singlesignon/latest/userguide/identity-center-instances.html
- [I2] IAM Identity Center FAQs (pricing): https://aws.amazon.com/iam/identity-center/faqs/
- [I3] Enable IAM Identity Center: https://docs.aws.amazon.com/singlesignon/latest/userguide/enable-identity-center.html
- [O1] AWS Organizations FAQs (pricing): https://aws.amazon.com/organizations/faqs/
- [O2] Service control policies: https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_scps.html
- [O3] Resource control policies: https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_rcps.html
- [R1] AWS account root user: https://docs.aws.amazon.com/IAM/latest/UserGuide/id_root-user.html
- [R2] Centralize root access for member accounts: https://docs.aws.amazon.com/IAM/latest/UserGuide/id_root-enable-root-access.html
- [R3] Revoke IAM role temporary security credentials: https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_use_revoke-sessions.html
- [M1] AWS Multi-factor authentication in IAM: https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_mfa.html
- [M2] Root user best practices (checked 2026-10-06): https://docs.aws.amazon.com/IAM/latest/UserGuide/root-user-best-practices.html
- [MS] IAM, check MFA status: https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_mfa_checking-status.html
- [AP1] Apple, About the security of passkeys: https://support.apple.com/en-us/102195
- [B1] Billing, activating access to the Billing and Cost Management console: https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/control-access-billing.html
- [S3M] Amazon S3, configuring MFA delete: https://docs.aws.amazon.com/AmazonS3/latest/userguide/MultiFactorAuthenticationDelete.html
- [A3] AWS service reference for IAM: https://servicereference.us-east-1.amazonaws.com/v1/iam/iam.json
- [V1] IAM, Versioning IAM policies (checked 2026-10-03): https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies_managed-versioning.html
- [I4] IAM Identity Center troubleshooting, "Cannot perform the operation on the protected role": https://docs.aws.amazon.com/singlesignon/latest/userguide/troubleshooting.html
- [C1] AWS CLI, login with console credentials: https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sign-in.html
- [C2] AWS Sign-In, sign in through the AWS CLI: https://docs.aws.amazon.com/signin/latest/userguide/command-line-sign-in.html
- [P1] IAM FAQs (pricing): https://aws.amazon.com/iam/faqs/
- [S1] Secrets Manager, access secrets from a different account: https://docs.aws.amazon.com/secretsmanager/latest/userguide/auth-and-access_examples_cross.html
- [S2] AWS Secrets Manager pricing (checked 2026-09-28): https://aws.amazon.com/secrets-manager/pricing/
- [K1] AWS KMS pricing (checked 2026-09-28): https://aws.amazon.com/kms/pricing/
- [T3] Terraform CHANGELOG, 1.15.0 (April 29, 2026): https://github.com/hashicorp/terraform/blob/v1.15/CHANGELOG.md ; issue https://github.com/hashicorp/terraform/issues/37976
- [T4] terraform-provider-aws #45316 (maintainer comment, 2025-12-04): https://github.com/hashicorp/terraform-provider-aws/issues/45316
- [T5] terraform-provider-aws CHANGELOG, 6.23.0: https://github.com/hashicorp/terraform-provider-aws/blob/main/CHANGELOG.md
- [T6] terraform-provider-aws #45817 (open): https://github.com/hashicorp/terraform-provider-aws/issues/45817
