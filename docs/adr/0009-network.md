# ADR 0009: Network: VPC, default VPC, traffic rules, and IP version

- **Status:** Accepted
- **Date:** 2026-10-30
- **Phase:** 1
- **Uses:** ADR 0008 (the origin keeps a public IPv4 and admits only CloudFront; Session Manager connects out)

## Context
- Phase 1 scope: "A private network, a VPN or zero-trust access layer, and Linux instances that host on-demand
  containers". Exit criterion: "An external scan shows only what is intended" (`docs/vision.md` §6, Phase 1).
- ADR 0008: the Web entry is CloudFront in front of Caddy on a host with a public IPv4; the admin path is Session
  Manager, whose agent connects out.
- Residents: the Linux host now and a Windows instance in Phase 7 (`docs/vision.md` §6). Both need an internet path.
- Hard constraints (`docs/vision.md` §5.1): AWS target USD 20, ceiling USD 25, Phase 1 line USD 12; every
  infrastructure change goes through code and the pipeline; console use is read-only except recorded exceptions.
- The pipeline cannot act outside Seoul (P4 `DenyOutsideSeoul`, ADR 0004 (f)).
- Carry-over from Phase 0: keep the AWS-created default VPCs or remove them through code.
- Factors (owner, 2026-10-25): (a) VPC and subnets, (b) default VPC, (c) outbound path and traffic rules, (d) IP
  version.

Facts this ADR relies on (checked 2026-10-29 and 2026-10-30):
- A VPC IPv4 CIDR is /16 to /28; a subnet CIDR cannot change after creation; with a primary CIDR in `10.0.0.0/15`, a
  secondary CIDR cannot come from `10.0.0.0/16`. A VPC can get an Amazon-provided IPv6 /56 and a subnet a /64
  [VPC2]. Each subnet reserves 5 addresses [VPC3].
- Default quotas: 5 IPv4 CIDR blocks per VPC; 60 inbound and 60 outbound rules per security group; 20 inbound and 20
  outbound rules per network ACL [VPC4]. A rule that references an AWS-managed prefix list counts as the list's
  weight [VPC10]; the CloudFront list leaves room for only 5 more rules [VPC12].
- The default VPC has a public subnet in each Availability Zone and an internet gateway [VPC5]. An instance gets an
  Amazon public IPv4 in a default subnet or in a subnet set to assign one [VPC7]. After the default VPC is deleted, a
  launch must name a subnet [VPC6].
- "There's no additional charge for using a VPC" [VPC7]; none for network ACLs [VPC11]. Public IPv4: USD 0.005 an
  hour, in use or idle; no IPv6 address charge is listed (inference: free) [VPC1]. Free Tier customers get 750 hours of
  public IPv4 with EC2 at no charge [VPC7]; whether this applies to the Free plan is unverified. NAT gateway USD 0.059
  an hour and interface endpoint USD 0.013 an hour (`docs/phases/phase-1.md` §2, checked 2026-10-11).
- `enableDnsHostnames` is false by default in a non-default VPC [VPC8].
- Security groups are stateful allow lists; network ACLs are stateless, with allow and deny rules in order [VPC9].
  A stateless deny must leave reply ports (1024 and up) open [VPC14]. Neither blocks DNS to the Route 53 Resolver
  [VPC10][VPC11]; instance metadata and Time Sync are not filtered either (`docs/phases/phase-1.md` §2).
- AWS-managed prefix lists in Seoul (read-only `describe-managed-prefix-lists`, 2026-10-30): `pl-22a6434b`
  (`com.amazonaws.global.cloudfront.origin-facing`), `pl-07ac407da2b364d6c` (its IPv6 version), `pl-78a54011`
  (`com.amazonaws.ap-northeast-2.s3`). None for Systems Manager.
- Session Manager needs outbound HTTPS (443) to `ssm`, `ssmmessages`, and `ec2messages` [SM1]. SSM Agent uses AWS
  managed S3 buckets for updates, and without S3 permissions "makes an HTTP call to download the update" [SM2]
  (inference: port 80). On 2026-10-30 the three Seoul endpoints resolved to addresses inside EC2 ranges in
  `ip-ranges.json` (createDate 2026-10-30-00-27-05; 127 `AMAZON` prefixes in Seoul) [IPR]. IPv6-only nodes also need
  the `*.region.api.aws` endpoints [SM3].
- CloudFront: a custom origin must be a publicly resolvable DNS name [CF1]; for HTTPS to the origin, the origin
  certificate must come from a CA on the Mozilla list and match the origin domain [CF2]; custom origins can use IPv6
  since 2025-09-08 [CF3].
- Let's Encrypt: IP address certificates are generally available since 2026-01-15 [LE1]; HTTP-01 uses port 80 and
  TLS-ALPN-01 port 443 [LE2]. That it refuses `amazonaws.com` names comes only from its community forum answers.
- Route 53 Domains: "Free Tier accounts are not supported for this service" (read-only
  `aws route53domains list-prices`, 2026-10-30).
- Docker's default address pools lie in `172.17.0.0`–`172.31.255.255` and `192.168.0.0/16` [DK1]. The home Wi-Fi uses
  `192.168.0.x`.
- AZ names map to the same AZ IDs for accounts created from November 2025 [AZ1]. On 2026-10-30 all four Seoul AZs
  were available and offered `t4g.nano`, `t4g.micro`, and `t4g.small` (read-only `describe-availability-zones` and
  `describe-instance-type-offerings`).
- Official guidance gives no number for spare address space [WA1]; an AWS Startups blog example splits a VPC into four
  and keeps spare [BL1].
- `aws_default_vpc` adopts an existing default VPC and creates one if none exists; `force_destroy = true` makes
  destroy delete it [TF1]. `aws_security_group` removes the AWS default allow-all egress rule, and the provider
  recommends `aws_vpc_security_group_ingress_rule` and `aws_vpc_security_group_egress_rule` [TF2].
- VPC Block Public Access blocks internet traffic in a Region, with exclusions per VPC or subnet [VPC13].

## Options considered
Stage 2 exit cost, every option: the AWS network is replaced by my own; the address plan and the allow-list rules
are rewritten for it (inference). No data lives in these parts.

### (a) VPC and subnets

| Option | Class | Pros | Cons | Monthly cost impact |
|---|---|---|---|---|
| a. Use the default VPC, read only | Primitive | Nothing to build | Outside code; an IaC exception for something code can do; default subnets give a public IPv4 | USD 0 |
| a'. Adopt the default VPC (`aws_default_*`) | Primitive | In code | Destroy only removes it from state; adopting the route table first deletes its routes; the internet gateway needs an import; (b) is fixed to keep | USD 0 |
| **b. Own VPC, one public subnet, by code** | Primitive | Ordinary resources rebuilt from code in an empty account; every public address is set in code | More resources to write | USD 0 |
| b with two subnets now | Primitive | Ready for Phase 7 | No resident until Phase 7 | USD 0 |

A private subnet behind a NAT gateway was not considered further: about USD 43 a month, over the Phase 1 line.

### (b) Default VPC in Seoul

| Option | Class | Pros | Cons | Monthly cost impact |
|---|---|---|---|---|
| a. Keep | — | Nothing to do | A launch without a subnet gets a public IPv4 outside the planned network | USD 0 |
| **b. Delete through code and the pipeline** | — | Record in Git and the approval history; a launch without a subnet fails | Two pipeline runs (adopt with `force_destroy`, then remove the block) | USD 0 |
| b'. Delete in the console | — | One action | Exception E11; no record in Git or the approval history | USD 0 |
| c. Also delete other Regions' default VPCs | — | No default VPC anywhere | The pipeline cannot act outside Seoul: a bootstrap change or an exception, for little gain | USD 0 |
| d. VPC Block Public Access with an exclusion for my VPC | Primitive | The default VPC stays but cannot reach the internet | One more setting and exclusion to maintain; a wrong exclusion cuts off the host | USD 0 |

### (c) Outbound path and traffic rules
The outbound path is the subnet route `0.0.0.0/0` to the internet gateway with the host's public IPv4 (ADR 0008).

| Option | Class | Pros | Cons | Monthly cost impact |
|---|---|---|---|---|
| **a. Security group allow list by protocol and port; NACL allows all, with deny rules for specific addresses** | Primitive | Deny by default; one inbound rule; the NACL can block one address in both directions | Outbound 443 open to any address | USD 0 |
| b. Security group allows all outbound; NACL blocklist | Primitive | Fewer security group rules | Allow by default; stateless denies on ports 1024 and up can drop replies | USD 0 |
| c. Outbound narrowed to the `AMAZON` ranges | Primitive | Narrower than any address | 127 Seoul prefixes, over the 60-rule quota; includes EC2 ranges anyone can rent | USD 0 |
| d. Interface endpoints for `ssm`, `ssmmessages`, `ec2messages` | Managed (AWS) | Systems Manager traffic stays in the VPC | About USD 28.47 a month, over the Phase 1 line | About USD 28.47 |
| e. A custom guard-rail NACL by port now | Primitive | A second port filter | A second rule set to keep in step with the security group | USD 0 |

### (d) IP version

| Option | Class | Pros | Cons | Monthly cost impact |
|---|---|---|---|---|
| **a. IPv4 only** | Primitive | One address family to filter, scan, and log; every service reachable | The public IPv4 stays | USD 0 (the IPv4 is in ADR 0008) |
| b. Dual-stack | Primitive | IPv6 available | The public IPv4 stays, so nothing is saved; a second family to filter, scan (`nmap -6`), and log | USD 0 |
| c. IPv6 only | Primitive | Removes the public IPv4 | Reopens ADR 0008; only CloudFront and Systems Manager confirmed over IPv6; one IPv4-only service needs a NAT gateway (about USD 43) | About −3.65 (0 if the 750 free hours apply) |

## 6-Layer check (chosen options)

| Layer | Notes |
|---|---|
| Traffic | In: CloudFront → internet gateway → `10.0.0.0/26` → host public IPv4, TCP 443 only from `pl-22a6434b`. Out: host → `0.0.0.0/0` → internet gateway, TCP 443 to any address. No IPv6. No other path. |
| Compute | No new compute. `apne2-az4` offered `t4g.nano`, `t4g.micro`, and `t4g.small` on 2026-10-30. |
| Data | The network parts hold no data. Anything on the host can leave over TCP 443 to any address. |
| Security | Deny by default in both directions; one inbound rule; one address family; the NACL can block single addresses. With the Seoul default VPC gone, a launch without a subnet fails instead of getting a public IPv4. DNS, IMDS, and Time Sync are not filtered. |
| Cost | VPC, subnet, internet gateway, route table, security group, and NACL: USD 0 [VPC7][VPC11]. Public IPv4 about USD 3.65 a month, already in ADR 0008. New cost USD 0. |
| Observability | CloudTrail records the network API calls (ADR 0007). Flow Logs and an alert on `DeleteVpc` are decided in question 6. Step 5 scans IPv4 only. |

## Decision

### (a) VPC and subnets: b
- My own VPC `10.0.0.0/24` with one public subnet `10.0.0.0/26` (usable `10.0.0.4`–`10.0.0.62`) in `apne2-az4`
  (`ap-northeast-2d`), all created by code, with the route `0.0.0.0/0` to an internet gateway.
- No private subnet: both residents need an internet path, and a NAT gateway is about USD 43 a month. Phase 7 decides
  whether Windows shares the subnet; security groups separate instances within one subnet.
- Range `10/8`: outside Docker's default pools and the home Wi-Fi. Rejected: `172.16/12` (holds Docker's pools) and
  `192.168/16` (Docker's pools and the home Wi-Fi).
- Size: a VPC is free at any size and its CIDR cannot be resized. `/24` covers the count (5 reserved + 2 machines + 2
  during replacement + up to 6 interface endpoints, about 15 per subnet) and gives four `/26` slots: one used now, the
  others for Phase 7 or later [BL1]. Rejected: `/25` subnets (one spare slot); `/27` (27 usable).
- AZ: every Seoul AZ offered the candidate types, so the choice is arbitrary. Each later subnet picks its AZ when it is
  created, after rechecking offerings.
- `enable_dns_hostnames` stays `false`: the CloudFront origin uses a name under my own domain from a registrar other
  than Route 53 (question 8). Rejected: the EC2 public DNS name (no certificate, so CloudFront-to-origin would stay
  HTTP and carry the `basic_auth` password unencrypted); a Let's Encrypt IP address certificate without CloudFront
  (validation needs port 80 or 443 open to everyone, which is ADR 0008 option A).

### (b) Default VPC: b
- Delete the Seoul default VPC through code and the pipeline: adopt it with `aws_default_vpc` and
  `force_destroy = true`, then remove the block, because the resource creates a new default VPC when none exists
  [TF1].
- Why delete: otherwise a launch without a subnet lands in it with a public IPv4 [VPC5][VPC7]. Why code: the change
  must leave a record in Git and the approval history (strict IaC).
- Other Regions keep theirs; the pipeline cannot act there.

### (c) Traffic rules: a
- Security group, deny by default:
  - Inbound: TCP 443 from `pl-22a6434b` only. The port becomes final in question 8.
  - Outbound: TCP 443 to `0.0.0.0/0` only. It cannot be narrowed: Systems Manager has no AWS-managed prefix list and
    its endpoints sit in EC2 ranges.
  - Port 80 stays closed. Question 4 decides whether SSM Agent updates need it; if so, it opens only to `pl-78a54011`.
  - New ports are added in the Phase that needs them, through the pipeline.
- NACL: allow all, plus deny rules for specific addresses when needed, in both directions and numbered before the
  allow rule. Behind CloudFront it sees only CloudFront addresses, so Web attackers are blocked at CloudFront after
  the flat-rate switch (ADR 0008).

### (d) IP version: a
- IPv4 only: no IPv6 CIDR block, route, or rule.
- Why: on 2026-10-30 only CloudFront and Systems Manager were confirmed over IPv6, and one IPv4-only service would
  need a NAT gateway. With IPv4, later services work without that check. Dual-stack saves nothing while the public
  IPv4 stays.

## Consequences
- Easier: every network part is ordinary code, rebuilt in an empty account; one inbound rule and one address family
  to scan and log; a launch without a subnet in Seoul fails instead of going public.
- Harder: every new port or destination is a pipeline change; deleting the default VPC takes two pipeline runs.
- Known limits accepted:
  - Outbound TCP 443 is open to any address, so a compromised host can send data out. Flow Logs (question 6) can show
    it, not stop it.
  - One subnet in one AZ: an outage of `apne2-az4` stops the host.
  - The NACL holds 20 rules per direction by default [VPC4], so it blocks only a few addresses.
  - A secondary VPC CIDR must come from outside `10.0.0.0/16` (for example, `10.2.0.0/24`) [VPC2].
  - The public IPv4 costs about USD 3.65 a month (USD 0 if the 750 free hours apply; unverified).
- Follow-ups for Step 4: check that the default VPC is empty and whether its subnets and internet gateway are deleted
  with it; manage the NACL in code (the default NACL or a custom one); use the separate security group rule resources
  [TF2]; confirm the AL2023 repository host on the instance (`/etc/yum.repos.d/`). Question 6: Flow Logs and a
  `DeleteVpc` alert. Question 8: domain, origin certificate, and origin port.

## Revisit when
- Phase 7 places the Windows instance (same subnet or a new `/26`).
- A needed service requires another port or protocol, or a destination outside TCP 443.
- Every needed service is confirmed over IPv6 and the public IPv4 cost matters (including the 750-hour check).
- Blocked addresses outgrow the NACL quota.
- NAT gateway or interface endpoint prices fit the budget.
- Stage 2 starts.

## Sources
- [VPC1] Amazon VPC pricing: https://aws.amazon.com/vpc/pricing/
- [VPC2] VPC CIDR blocks: https://docs.aws.amazon.com/vpc/latest/userguide/vpc-cidr-blocks.html
- [VPC3] Subnet CIDR blocks: https://docs.aws.amazon.com/vpc/latest/userguide/subnet-sizing.html
- [VPC4] Amazon VPC quotas: https://docs.aws.amazon.com/vpc/latest/userguide/amazon-vpc-limits.html
- [VPC5] Default VPCs: https://docs.aws.amazon.com/vpc/latest/userguide/default-vpc.html
- [VPC6] Work with default VPCs: https://docs.aws.amazon.com/vpc/latest/userguide/work-with-default-vpc.html
- [VPC7] What is Amazon VPC? ("Pricing for Amazon VPC"): https://docs.aws.amazon.com/vpc/latest/userguide/what-is-amazon-vpc.html
- [VPC8] Understanding Amazon DNS: https://docs.aws.amazon.com/vpc/latest/userguide/AmazonDNS-concepts.html
- [VPC9] Infrastructure security in Amazon VPC: https://docs.aws.amazon.com/vpc/latest/userguide/infrastructure-security.html
- [VPC10] Security group rules: https://docs.aws.amazon.com/vpc/latest/userguide/security-group-rules.html
- [VPC11] How network ACLs work: https://docs.aws.amazon.com/vpc/latest/userguide/nacl-basics.html
- [VPC12] AWS-managed prefix lists: https://docs.aws.amazon.com/vpc/latest/userguide/working-with-aws-managed-prefix-lists.html
- [VPC13] VPC Block Public Access: https://docs.aws.amazon.com/vpc/latest/userguide/security-vpc-bpa.html
- [VPC14] Ephemeral ports: https://docs.aws.amazon.com/vpc/latest/userguide/nacl-ephemeral-ports.html
- [SM1] Session Manager prerequisites: https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-prerequisites.html
- [SM2] SSM Agent technical details ("SSM Agent communications with AWS managed S3 buckets"): https://docs.aws.amazon.com/systems-manager/latest/userguide/ssm-agent-minimum-s3-permissions.html
- [SM3] VPC endpoints for Systems Manager: https://docs.aws.amazon.com/systems-manager/latest/userguide/setup-create-vpc.html
- [IPR] AWS IP address ranges: https://ip-ranges.amazonaws.com/ip-ranges.json
- [CF1] Origin settings: https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/DownloadDistValuesOrigin.html
- [CF2] Requirements for SSL/TLS certificates with CloudFront: https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/cnames-and-https-requirements.html
- [CF3] CloudFront IPv6 origins (2025-09-08): https://aws.amazon.com/about-aws/whats-new/2025/09/amazon-cloudfront-ipv6-origins/
- [LE1] Let's Encrypt, 6-day and IP address certificates GA: https://letsencrypt.org/2026/01/15/6day-and-ip-general-availability
- [LE2] Let's Encrypt challenge types: https://letsencrypt.org/docs/challenge-types/
- [DK1] dockerd reference (default address pools): https://docs.docker.com/reference/cli/dockerd/
- [AZ1] AWS Availability Zones: https://docs.aws.amazon.com/global-infrastructure/latest/regions/aws-availability-zones.html
- [WA1] Well-Architected REL02-BP03: https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_planning_network_topology_ip_subnet_allocation.html
- [BL1] AWS Startups blog, "Practical VPC Design" (2014): https://aws.amazon.com/blogs/startups/practical-vpc-design/
- [TF1] Terraform `aws_default_vpc`: https://raw.githubusercontent.com/hashicorp/terraform-provider-aws/main/website/docs/r/default_vpc.html.markdown
- [TF2] Terraform `aws_security_group`: https://raw.githubusercontent.com/hashicorp/terraform-provider-aws/main/website/docs/r/security_group.html.markdown
