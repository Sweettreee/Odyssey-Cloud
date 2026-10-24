# ADR 0008: Access layer: Web entry, Web login, and admin path

- **Status:** Accepted
- **Date:** 2026-10-25
- **Phase:** 1
- **Uses:** the ADR 0005 trigger (upgrade to the Paid plan) as the switch point in (a)

## Context
- Phase 1 scope: "A private network, a VPN or zero-trust access layer, and Linux instances that host on-demand
  containers". Exit criteria include "An external scan shows only what is intended" and "Access attempts are logged"
  (`docs/vision.md` §6, Phase 1).
- Owner requirement (2026-10-24, `docs/phases/phase-1.md` §6): the Web (my services and my own files, CRUD) works in a
  browser on any device over the internet with a simple login, with no VPN client and no `aws login`. Developing and
  managing services is never possible through the Web; in practice it happens from the MacBook with the existing
  `aws login` (not enforced per device).
- Hard constraints (`docs/vision.md` §5.1): only I can reach the platform; AWS target USD 20, ceiling USD 25, Phase 1
  line USD 12; usage covered by credits counts as cost; every infrastructure change, including stop, goes through the
  pipeline after my approval.
- Order of precedence and self-run by default (`docs/vision.md` §5.2).
- The account stays on the Free account plan until the ADR 0005 trigger.

Facts this ADR relies on (checked 2026-10-24 and 2026-10-25):
- CloudFront pay-as-you-go always-free usage: 1 TB of data out and 10 million requests a month, on both account
  plans [FT1].
- CloudFront Free flat-rate plan: USD 0 a month, 1 million requests and 100 GB. "No overage charges"; "Blocked DDoS
  attacks and requests blocked by AWS WAF never count against your usage allowance"; sustained excess may have
  delivery "adjusted". Includes always-on DDoS protection, WAF (5 rules), IP-based rate limiting, and geographic
  blocking. Excludes advanced DDoS protection, access logs, VPC origins, and custom origin request policies [CF1].
- An account is not eligible for flat-rate plans if "Your account is using AWS Free Tier" [CF1].
- The Free account plan "ensures you won't incur any charges"; it ends after six months or when the credits are
  used, and then the account closes [FP1].
- Shield Standard reaches all AWS customers "at no additional charge" and covers network and transport layer
  events; with CloudFront, "all known infrastructure (Layer 3 and 4) events" [SH1].
- A WAF rate-based rule "counts incoming requests and rate limits requests when they are coming at too fast a
  rate" [WAF1]. Pay-as-you-go WAF: USD 5 per web ACL a month, USD 1 per rule a month, USD 0.60 per million
  requests [WAF2].
- With the CloudFront-assigned domain name, "CloudFront provides the SSL/TLS certificate"; an own domain needs an
  ACM or imported certificate [CF2]. Data transfer between CloudFront and AWS origins is waived on flat-rate
  plans [CF3]. An origin security group can admit only the CloudFront managed prefix list [CF4].
- AWS billing data for Budgets "is updated at least once per day" [B1]. A CloudWatch alarm can stop an EC2
  instance automatically [CW1].
- Public IPv4: USD 0.005 an hour, in use or idle [VPC1]. ALB: USD 0.0225 an hour in us-east-1 [ELB1].
- Caddy `basic_auth` stores bcrypt hashes by default and rejects plaintext passwords; its page does not mention
  brute-force protection [CD1]. HTTP Basic is not secure "unless used in conjunction with some external secure
  system" such as TLS [RFC7617].
- Session Manager: "No additional charges for usage on Amazon EC2 instances" [SM1]; SSM Agent is preinstalled on
  AL2023 [SM2]; instance permissions come from an instance profile with `AmazonSSMManagedInstanceCore` or from the
  Default Host Management Configuration [SM3]; idle sessions end after 20 minutes by default (1–60) [SM4];
  "Logging isn't available for Session Manager sessions that connect through port forwarding or SSH" [SM5].
  Systems Manager is "Available on both plans" [FT1].

## Options considered

### (a) Web entry

| Option | Class | Pros | Cons | Monthly cost impact | Stage 2 exit cost |
|---|---|---|---|---|---|
| A. Caddy on the host, public port 443 | Self-run + primitive | No third party; TLS ends on my host | A many-IP flood raises data-out and CPU cost with no automatic cap; an automatic stop breaks human-in-the-loop; a manual stop depends on my reaction time | Public IPv4 about USD 3.65 | About none |
| B. Cloudflare Tunnel and Access | Managed (third party) | No inbound port | A third party carries and decrypts my traffic; one more account | USD 0 (free plan) | DNS and login move |
| C. CloudFront with a VPC origin | Managed (AWS) | Origin stays private | VPC origins are not in the Free flat-rate plan | Not verified | Entry replaced |
| D. ALB | Managed (AWS) | Built-in load balancer | About USD 16.4 a month in us-east-1 alone | Over the line | Entry replaced |
| **E. CloudFront in front of Caddy, two stages** | Managed front, self-run origin | The flat-rate stage caps flood cost; L3/L4 DDoS cover; the origin admits only CloudFront | No cost cap beyond the always-free usage until the switch; AWS decrypts at the edge; no advanced DDoS protection | USD 0 + the same public IPv4 as A | The front can be dropped or kept; Caddy is unchanged (inference) |

### (b) Web login

| Option | Class | Pros | Cons | Monthly cost impact | Stage 2 exit cost |
|---|---|---|---|---|---|
| **a. Caddy `basic_auth`** | Self-run | No extra part | One shared password; no brute-force blocking until the switch | USD 0 | None |
| b. Authelia with a passkey | Self-run | Face ID; bans after failed attempts | One more service; no per-device session revoke upstream | USD 0 | None |
| c. Client certificates (mTLS) | Self-run | No login page at all | Safari support known only from Apple forum answers; a private CA to run | USD 0 | None |

A managed login (for example Cognito) was not considered further: self-run candidates exist (§5.2).

### (c) Admin path from the MacBook

| Option | Class | Pros | Cons | Monthly cost impact | Stage 2 exit cost |
|---|---|---|---|---|---|
| **a. Session Manager** | Managed (AWS) | Fewest parts; no SSH keys or host keys; no inbound port; session content can be logged | The host role gains SSM permissions; AWS only | USD 0 [SM1] | Admin path replaced |
| b. EC2 Instance Connect Endpoint | Managed (AWS) | The host needs no AWS permissions; every attempt in CloudTrail | An endpoint, two security group rules, SSH keys, a new host key on every rebuild; 1-hour cap | USD 0 | Admin path replaced |
| c. WireGuard for the MacBook | Self-run | No AWS dependency | A second internet entry, against "only the Web entry is reachable" | USD 0 | None |
| d. No shell | — | Fewest parts | When logs are not enough, the only fix is a rebuild | USD 0 | None |

## 6-Layer check (chosen options)

| Layer | Notes |
|---|---|
| Traffic | Browser → CloudFront (HTTPS) → origin public IPv4, security group admits only the CloudFront managed prefix list → Caddy → container. Admin: MacBook → Systems Manager ← SSM Agent connecting out. No other inbound rule. |
| Compute | Caddy and SSM Agent on the host. No new instance. |
| Data | Viewer TLS ends at CloudFront (AWS sees the traffic; no new third party). From Phase 2 my files pass through CloudFront. The bcrypt hash is kept outside git (question 4). |
| Security | One internet entry. Long random password; IP-based rate limiting only after the switch. The host role gains SSM permissions; IMDS hop limit 1 keeps containers away from them (question 4). Every request is authenticated at the entry and none is trusted by network location, which is how this meets "zero-trust access layer" (inference). |
| Cost | CloudFront USD 0 within always-free usage now and USD 0 on the flat-rate plan after the switch; Session Manager USD 0; public IPv4 about USD 3.65 (already in the Phase 1 line); no WAF before the switch. |
| Observability | Caddy access log on the host; CloudTrail `StartSession`. No CloudFront access logs on the Free plan. An early alarm on CloudFront request volume is decided in question 6. |

## Decision

### (a) Web entry: E, in two stages
- Now (Free account plan): pay-as-you-go CloudFront within the always-free usage, Shield Standard only, no AWS WAF.
- At the ADR 0005 trigger (upgrade to the Paid plan): subscribe the same distribution to the Free flat-rate plan.
- Why a managed front: no self-run option keeps the cost of a many-IP flood within the budget hard constraint. An
  automatic stop breaks human-in-the-loop, and a manual stop depends on my reaction time while billing data arrives
  only once a day [B1].
- The origin keeps a public IPv4 (VPC origins are not in the Free plan), and its security group admits only the
  CloudFront managed prefix list.

### (b) Web login: a
- Caddy `basic_auth` with one long random password from a password manager, stored as a bcrypt hash.
- No brute-force blocking until the switch (fail2ban behind CloudFront would see only CloudFront addresses); after
  the switch, the plan's IP-based rate limiting.
- Chosen over b as simpler.

### (c) Admin path: a
- Session Manager from the MacBook with the existing `aws login`.
- Chosen as the simplest. Self-run is clearly worse on security here: the only self-run option opens a second
  internet entry.

## Consequences
- Easier: one internet entry; no VPN client on any device; no SSH keys or host keys; no domain is needed to start,
  since CloudFront provides the certificate for its own name [CF2].
- Harder: the Web entry depends on CloudFront; the admin path depends on Systems Manager.
- Known limits accepted:
  - Until the switch, an HTTP flood beyond the always-free usage uses credits (counted as cost), and using them up
    closes the account [FP1].
  - After the switch, no advanced DDoS protection: a large flood can slow or stop the site but cannot raise the bill.
  - Anyone past the login can read and change everything the Web shows; the Web cannot change infrastructure
    (`docs/vision.md` §4.1).
  - Cutting off one lost device means changing the password for every device.
  - Session Manager does not log SSH or port-forwarding sessions [SM5]; only plain shell sessions are used.
- Follow-ups: CloudFront-to-origin protocol and certificate; whether the plan forwards the `Authorization` header;
  own domain or the CloudFront-assigned name (an ACM certificate is outside `DenyOutsideSeoul`, ADR 0004 (f)); where
  the bcrypt hash and shell session logs are kept; the rate-limit threshold; whether the flat-rate subscription can
  be code; geographic blocking after the switch; whether the shell is for looking only.

## Revisit when
- The ADR 0005 trigger happens: subscribe to the flat-rate plan and add rate limiting.
- An HTTP flood is seen, or credits fall fast.
- Phase 2 checks "A lost device can be cut off from my files without affecting the others".
- A second person needs access (Stage 2).
- CloudFront flat-rate plan terms or the always-free usage change.

## Sources
- [FT1] AWS Free Tier (CloudFront always-free usage; Systems Manager "Available on both plans", owner screenshots 2026-10-24 and 2026-10-25): https://aws.amazon.com/ko/free/
- [CF1] CloudFront flat-rate pricing plans: https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/flat-rate-pricing-plan.html
- [CF2] Require HTTPS between viewers and CloudFront: https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/using-https-viewers-to-cloudfront.html
- [CF3] CloudFront pricing: https://aws.amazon.com/cloudfront/pricing/
- [CF4] CloudFront VPC origins (managed prefix list): https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-vpc-origins.html
- [FP1] Choosing a plan: https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/free-tier-plans.html
- [SH1] AWS Shield features: https://aws.amazon.com/shield/features/
- [WAF1] Rate-based rule statements: https://docs.aws.amazon.com/waf/latest/developerguide/waf-rule-statement-type-rate-based.html
- [WAF2] AWS WAF pricing: https://aws.amazon.com/waf/pricing/
- [B1] Best practices for AWS Budgets: https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-best-practices.html
- [CW1] CloudWatch alarm EC2 actions: https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/UsingAlarmActions.html
- [VPC1] Amazon VPC pricing: https://aws.amazon.com/vpc/pricing/
- [ELB1] Elastic Load Balancing pricing: https://aws.amazon.com/elasticloadbalancing/pricing/
- [CD1] Caddy `basic_auth`: https://caddyserver.com/docs/caddyfile/directives/basic_auth
- [RFC7617] The 'Basic' HTTP Authentication Scheme: https://www.rfc-editor.org/rfc/rfc7617
- [SM1] AWS Systems Manager pricing: https://aws.amazon.com/systems-manager/pricing/
- [SM2] AMIs with SSM Agent preinstalled: https://docs.aws.amazon.com/systems-manager/latest/userguide/ami-preinstalled-agent.html
- [SM3] Instance permissions for Session Manager: https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-getting-started-instance-profile.html
- [SM4] Idle session timeout: https://docs.aws.amazon.com/systems-manager/latest/userguide/session-preferences-timeout.html
- [SM5] Start a session: https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-sessions-start.html
