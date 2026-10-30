# Phase 1: Secure Access & Linux Compute (working notes)

> Recovery point for this Phase and the source for the STATUS.md report.
> Update at the end of each learning topic, decision, and implementation step. Keep it short; this is not a transcript.

**Phase status:** In progress
**Current step:** 3 Design & decisions (since 2026-10-18)
**Next action:** Design question 3 (compute). Question 8 (domain and certificates) was added on 2026-10-30.
**Last updated:** 2026-10-30

## Carry-over from previous phase
- Add an `ec2:InstanceType` allowlist to P4 when compute arrives (ADR 0004 (f)).
- Decide whether to keep the AWS-created default VPCs or remove them through code.
- Handle the AWS User Notifications email contact created outside code at the E4 apply (delete, bring into code, or verify and record); the owner decides when.
- Decide whether containers on a host follow code, approval, and pipeline, or count as operations.

## 1. Learning Brief

Status: Final (agreed on 2026-10-10). Narrowed 4, widened 5 and 7, added topics 8–11 and two "before moving on" items; nothing removed.

### Before starting
- [x] 1. Networking basics: IP addresses, subnets, CIDR, ports, DNS, and routing.
- [x] 2. Public vs. private networks, and how private resources reach the internet (NAT).
- [x] 3. Firewalls: inbound and outbound rules, and stateful filtering.
- [x] 4. Secure communication basics: public and private keys, TLS, and SSH (TLS at a basic level; encryption in transit is covered in Phase 2).
- [x] 5. Ways to reach a private server: VPN, zero-trust access, and remote shell access through the cloud provider.
- [x] 6. Linux basics: the shell, file system, permissions, processes, and service management.
- [x] 7. VMs vs. containers, images and registries, and how a container on a host is described, started, and removed.
- [x] 8. Cloud virtual networks: subnets, route tables, gateways, and firewalls at the instance and subnet level.
- [x] 9. How compute and networking are billed: instance hours, disks, public IPv4 addresses, and data transfer.
- [x] 10. Running a host with little upkeep: OS updates (patch in place vs. replace from a fresh image), and how a server gets cloud permissions without stored keys.
- [x] 11. Proving exposure and access: what an external port scan shows (open, closed, filtered), and where access attempts are recorded (network, host, access layer).

### Before moving on (I can explain…)
- [ ] The path a request takes from my device to a container.
- [ ] Why only the Web entry is reachable from the internet, and what an outsider sees there.
- [ ] The access approach I chose, the alternatives I rejected, and their cost difference.
- [ ] How a container is created and destroyed through code, and who approves each step.
- [ ] Where an access attempt is recorded, and how I review it.

### Targets (agreed at Step 1, 2026-10-10)
- Availability: always on (I must reach it at any time, and starting it through the pipeline each time is too much friction); 99% per month; one instance; rebuilt from code within 30 minutes if broken (measured in Step 5). On-demand (off by default) was rejected.
- Latency: round trip from my device in Korea to the host through the access layer under 100 ms (inference, no official threshold); from approval to a container created or destroyed under 5 minutes, excluding the wait for my approval.
- AWS budget allocation: 12 USD/month (`docs/vision.md` §5.1), unchanged. An always-on design must fit it; instance size and public IPv4 are decided in Step 3.
  - Reference prices (Seoul, Linux, on-demand, 730 h, checked 2026-10-10): t4g.micro USD 0.0104/h (about 7.59/month); gp3 USD 0.0912/GB-month; public IPv4 USD 0.005/h, in use or idle (about 3.65/month). Sources: https://aws.amazon.com/ec2/pricing/on-demand/, https://aws.amazon.com/ebs/pricing/, https://aws.amazon.com/vpc/pricing/ ("Public IPv4 Address").

## 2. Learning notes

### 1. Networking basics
- An IP address finds the machine and a port finds the program; a connection is a pair of IP:port sockets. CIDR `/n` fixes the first n bits: a smaller n is a bigger range, and `0.0.0.0/0` means everywhere.
- Routing picks the next hop by destination, hop by hop; the most specific route wins, the default route catches the rest, and replies need their own route back. An AWS subnet's type (public, private, isolated) comes from its route table.
- DNS turns names into addresses (A, AAAA) through resolvers and authoritative name servers; answers are cached for the TTL, so an address change is not seen at once.

### 2. Public vs. private networks, and NAT
- Private ranges (10/8, 172.16/12, 192.168/16) are not routed on the internet; IPv6 addresses are public by default, so reachability comes from routes and firewalls. In AWS, a subnet is public when its route table points to an internet gateway, and an instance also needs a public address.
- NAT rewrites private source addresses (and ports) to a public one and remembers each connection, so replies come back but outsiders cannot start a connection.
- Outbound options in Seoul (checked 2026-10-11): NAT gateway (USD 0.059/h, about 43/month, over the whole AWS budget), NAT instance (self-managed), IPv6 egress-only gateway (no gateway charge, IPv6 only), or a public IPv4 on the host (USD 0.005/h; inbound is then limited only by the firewall).

### 3. Firewalls
- A firewall rule matches direction, protocol, source and destination address, and port; deny by default blocks everything inbound and outbound that is not expressly allowed (NIST SP 800-41r1 §2.1.1, §4).
- A stateful firewall keeps a state table, so replies to an allowed connection pass without their own rule and forged "established" packets are dropped; a stateless filter needs separate rules for the replies.
- With no inbound rule at all, a stateful host can still open outbound connections and receive their replies, while nothing from outside can start a connection.

### 8. Cloud virtual networks
- A VPC is an isolated network cut into subnets (one AZ each, 5 addresses reserved); each subnet follows one route table (the main one by default) whose local route covers the VPC, and gateways (internet, egress-only, NAT, gateway endpoint) are route targets. Avoid `172.17.0.0/16` (Docker overlap).
- Two firewall layers: security groups (instance level, allow only, stateful, all rules evaluated; AWS's primary control) and network ACLs (subnet level, allow and deny, stateless, lowest number first; the default NACL allows everything). Neither filters Amazon DNS, DHCP, instance metadata, or time sync.
- The default VPC has an internet gateway, a `0.0.0.0/0` route, and default subnets that give instances a public IPv4; an instance launched without a subnet lands there. AWS creates it outside IAM; it can be deleted and a new one created, but not restored.

### 4. Keys, TLS, and SSH
- A symmetric key is one shared secret; a key pair has a public key anyone may hold and a private key only the owner holds. Key pairs sign (origin and integrity) and agree on a shared secret; SSH and TLS use them to authenticate and agree on keys, then encrypt the data with symmetric keys.
- SSH: the client checks the server's host key (`known_hosts` or a CA; an unchecked first connection is open to man-in-the-middle), and the server checks the user, where publickey (a private-key signature against `authorized_keys`) is the only required method. Upstream OpenSSH allows passwords by default; a rebuilt host likely gets a new host key (inference).
- TLS: in the handshake the server proves itself with a certificate (a CA-signed binding of a public key to a name) and a signature, both sides agree on keys, and the client must check that the name matches; everything after the key exchange is encrypted.

### 5. Ways to reach a private server
- A VPN carries my device's private traffic inside an encrypted tunnel (IPsec, TLS/OpenVPN, WireGuard). Self-hosted needs one open port (WireGuard stays silent to unauthenticated packets); AWS Client VPN costs about USD 73/month for the endpoint alone in Seoul.
- Zero trust (NIST SP 800-207) gives no trust for network location and checks each session at a PEP. Outbound connectors (Cloudflare Tunnel, Tailscale) need no inbound port but add a third-party account and control plane (free plans checked 2026-10-14).
- Session Manager: outbound-only agent, IAM, no SSH keys, free on EC2, but needs an outbound path (public IPv4, IPv6, or interface endpoints at USD 0.013/h each) and SSH or port-forwarding sessions have no session log. EICE: free, logs every attempt to CloudTrail, but needs SSH allowed from inside the VPC and caps a connection at 1 hour.

### 6. Linux basics
- The shell (bash) runs commands found on `PATH`; exit status 0 means success, and `|` and `>` connect and redirect input and output. Files live in one tree from `/` with fixed roles (FHS): `/etc` config, `/var/lib` state, `/var/log` logs, `/proc` a virtual view of the kernel.
- Every process runs as a UID. Permission bits give read, write, and execute (search for directories) to owner, group, and others (for example `600`, `700`). UID 0 (root) bypasses all checks, so work as a normal user and use `sudo`. sshd refuses an `authorized_keys` file that others can write.
- systemd (PID 1) supervises services from unit files: `start`/`stop` act now, `enable` starts at boot, `Restart=` restarts on failure, and services run as root unless `User=` is set. journald collects service output and logs; AL2023 has no `/var/log/messages`, so logs are read with `journalctl`.

### 7. VMs vs. containers
- A VM has its own virtual hardware and full OS under a hypervisor (EC2 is a VM on Nitro); containers share the host kernel and are separated by namespaces (PID, network, mount, user) and cgroups, so a Linux host runs only Linux containers and the boundary is weaker than a VM's (NIST SP 800-190).
- An image is an immutable set of layers plus a manifest and config. A tag is a movable, human-readable pointer; a digest is a hash of the content. The image must match the host CPU (t4g is arm64). ECR: IAM token valid 12 hours, a pull-only policy exists, storage USD 0.10/GB-month in Seoul, and same-region transfer to EC2 is free (checked 2026-10-16).
- `run` creates and starts, `stop` sends SIGTERM then SIGKILL after 10 s, and `rm` deletes the writable layer (volumes persist). `-p` publishes on all addresses unless bound to `127.0.0.1`. The `docker` group is root-equivalent. Containers can be declared in `compose.yaml` or Podman Quadlet files and applied from code through user data (at launch) or SSM Run Command (on a running host).

### 10. Running a host with little upkeep
- AL2023 locks to a repository version and does not update itself. Update in place (`dnf upgrade --releasever`, or Patch Manager, which by default reboots after any install) or replace from the latest AMI (SSM public parameter). Kernel updates need a reboot; live patching only defers it (3 months per kernel). On replacement, the root volume is deleted by default (checked 2026-10-17).
- A server gets AWS permissions from an IAM role in an instance profile (one role per instance). IMDS hands out temporary credentials that rotate automatically, so no keys are stored. Attaching a role needs `iam:PassRole`, which should name specific role ARNs. IAM and IMDS requests cost nothing (checked 2026-10-18).
- IMDSv2 requires a `PUT` session token (up to 6 hours, valid only on that instance). The hop limit is 1 by default (2 with an IMDSv2-only AMI or account default); 1 can block containers, while 2 lets them reach the role's credentials, so the role must be least privilege. SSM permissions come from an instance profile (`AmazonSSMManagedInstanceCore`) or the account-level DHMC.

### 9. How compute and networking are billed
- EC2 bills only while `running`, per second with a 1-minute minimum per start. EBS bills on provisioned GB until deleted, even when the instance is stopped. Seoul (checked 2026-10-18): t4g.nano/micro/small USD 0.0052/0.0104/0.0208 per hour (about 3.80/7.59/15.18 a month); gp3 0.0912/GB-month with 3,000 IOPS and 125 MiB/s included; snapshots 0.05/GB-month.
- T4g launches in `unlimited` mode. Averaging above baseline (10% per vCPU on micro) over 24 hours costs USD 0.04 per vCPU-hour, so a runaway process can add about 23 to 53 USD a month. `standard` mode throttles to baseline instead.
- Public IPv4 costs USD 0.005/h (about 3.65/month), in use or idle. Inbound data is free; the first 100 GB/month out is free account-wide, then 0.126/GB. Gateway endpoints are free; interface endpoints cost 0.013/h each. Always-on totals: micro + 20 GB + public IPv4 about 13.07 (over the 12 USD line), micro + 8 GB + IPv4 about 11.97, and micro + 20 GB without IPv4 about 9.42.

### 11. Proving exposure and access
- A SYN scan reads SYN/ACK as open, RST as closed, and no reply or ICMP unreachable as filtered. nmap scans only the 1,000 most common ports unless given `-p-`, open UDP ports show as `open|filtered`, and IPv6 needs `-6`. AWS allows scanning my own EC2 without approval but bans flooding and DoS. The proof must come from an outside network.
- Each layer sees something different. VPC Flow Logs record flow metadata with ACCEPT/REJECT (not DNS, IMDS, or time sync). The host journal records only what reaches the host (sshd at INFO). CloudTrail records access-layer calls (`StartSession`, `OpenTunnel`) with the caller and source IP; the Phase 0 trail keeps them, and Event history shows the last 90 days. Session Manager cannot log SSH or port-forwarding sessions, and Tailscale flow logs need a paid plan.
- Host logs are lost with the host, so ship them off with the CloudWatch agent (journald) or Docker `awslogs`; Docker `json-file` does not rotate by default. Seoul (checked 2026-10-18): CloudWatch Logs ingestion USD 0.76/GB, storage 0.0314/GB-month, Logs Insights 0.0076/GB scanned, vended logs to S3 0.38/GB (Flow Logs mapping inferred). Log groups keep data forever unless retention is set.

## 3. Decisions

| ADR | Title | Status |
|---|---|---|
| [0008](../adr/0008-access-layer.md) | Access layer: Web entry, Web login, and admin path | Accepted |
| [0009](../adr/0009-network.md) | Network: VPC, default VPC, traffic rules, and IP version | Accepted |

## 4. Implementation log

| Date | Step | Result |
|---|---|---|
| — | — | — |

## 5. Verification

### Exit criteria
- [ ] An external scan shows only what is intended. (evidence: …)
- [ ] A container can be created and destroyed through code within minutes. (evidence: …)
- [ ] Access attempts are logged. (evidence: …)

## 6. Open issues
- Step 3 design questions (suggested order; the owner may reorder):
  1. Access layer, split by use (owner, 2026-10-24): the Web (my services and my own files, CRUD) works in a browser on any device over the internet with a simple login, with no VPN client and no `aws login`; developing and managing services is never possible through the Web and happens in practice from the MacBook with the existing `aws login` (not enforced per device). Factors: 1-1 Web entry, 1-2 Web login (including lost-device cut-off), 1-3 MacBook admin path (including SSH host keys on rebuild).
     - 1-1 decided (2026-10-25): CloudFront in front of Caddy on the host (managed front, self-run origin), in two stages. Now: pay-as-you-go CloudFront within the always-free allowance (1 TB and 10 million requests a month) on the Free account plan, with Shield Standard only and no AWS WAF. At the upgrade to the Paid plan (due within the Free plan's six months): subscribe the same distribution to the Free flat-rate plan (no overage charges; blocked attacks do not count). Reason: no self-run option keeps the cost of a many-IP flood within the budget hard constraint (`docs/vision.md` §5.1); an automatic stop breaks the human-in-the-loop rule and a manual stop depends on my reaction time. CloudFront terminates the viewer TLS (AWS sees the traffic; no new third party). The origin keeps a public IPv4, and its security group admits only the CloudFront managed prefix list. Accepted risks: until the switch, a flood beyond the always-free allowance uses credits (counted as cost), and using them up closes the account; after it, there is no advanced DDoS protection, so a large flood can slow or stop the site but cannot raise the bill. Rejected: Caddy alone with an automatic or a manual stop; Cloudflare Tunnel (a third party carries the traffic); ALB (about USD 16.4 a month in us-east-1 alone); AWS WAF before the switch (at least about USD 6 a month plus per-request charges). Follow-ups: CloudFront-to-origin protocol and certificate; `Authorization` header forwarding; a domain and its price; an early alarm on CloudFront request volume (question 6); whether the plan subscription can be code; geographic blocking after the switch.
     - 1-2 decided (2026-10-25): a, Caddy `basic_auth` (self-run; one long random password from a password manager, stored as a bcrypt hash). Brute-force blocking: none until the flat-rate switch (fail2ban behind CloudFront sees only CloudFront addresses), then the plan's IP-based rate limiting. Chosen over b (Authelia with a passkey) as simpler. Accepted risks: anyone past the login can read and change everything the Web shows, though the Web cannot change infrastructure (`docs/vision.md` §4.1); cutting off one lost device means changing the password for every device (recheck against the Phase 2 lost-device criterion). Rejected: b (one more service; no per-device session revoke upstream); c (mTLS; Safari support known only from Apple forum answers; a private CA to run). Follow-ups: where the bcrypt hash is kept outside git (question 4); the rate-limit threshold; whether Caddy logs carry the status code and the viewer IP behind CloudFront. ADR 0008 is written after 1-3.
     - 1-3 decided (2026-10-25): a, Session Manager (managed, AWS) from the MacBook with the existing `aws login`. Chosen as the simplest: SSM Agent is preinstalled on AL2023, there are no SSH keys, and no host key to re-trust after a rebuild. No new internet entry: the agent connects out. Systems Manager is "Available on both plans" on the AWS Free Tier page (checked 2026-10-25). Records: CloudTrail `StartSession`; shell session content can also be logged. Needs: SSM permissions for the host (instance profile with `AmazonSSMManagedInstanceCore`, or DHMC) and an outbound path to Systems Manager (the host's public IPv4). Self-run is clearly worse on security here: the only self-run option, c (WireGuard for the MacBook), opens a second internet entry against "only the Web entry is reachable". Rejected: b (EICE; an endpoint, two security group rules, SSH keys, and a new host key on every rebuild, though the host would need no AWS permissions); d (no shell). Stage 2 exit: only the admin path is replaced (inference). Accepted risk: the host role gains SSM permissions; IMDS hop limit 1 keeps containers away from them (question 4). Follow-ups: where shell session logs go and their cost (question 6); whether the shell is for looking only, not changing (strict IaC).
  2. Network: public IPv4 or IPv6 only, the outbound path, and the default VPC (carry-over).
     - Factors (2026-10-25): 2-1 VPC and subnets, 2-2 default VPC (carry-over), 2-3 outbound path and rules (public IPv4 already set by ADR 0008), 2-4 IPv6.
     - 2-1 decided (2026-10-29): b, my own VPC with one public subnet in one AZ, all created by code (primitive; USD 0). Only two machines will live in the VPC, the Linux host now and a Windows instance in Phase 7, and both need an internet path, so there is no private subnet (a NAT gateway is about USD 43 a month). Phase 7 decides whether Windows shares the subnet; security groups separate instances within one subnet. The VPC CIDR cannot be resized, so it leaves room for more subnets. Chosen over a' because every part is an ordinary resource rebuilt from code in an empty account, 2-2 stays open, and public IPv4 is off by default, so every public address is in code. Rejected: a (read the default VPC only; it stays outside code and would need an IaC exception for something code can do); a' (adopt it with `aws_default_*`: destroy only removes it from state, adopting the route table first deletes all its routes, the internet gateway needs an import, and 2-2 is fixed to keep); two subnets now (no resident until Phase 7). Follow-ups: CIDR (below); the AZ (below); `enable_dns_hostnames` (below).
     - 2-1 CIDR decided (2026-10-30): VPC `10.0.0.0/24`, host subnet `10.0.0.0/26` (usable `10.0.0.4`–`10.0.0.62`, 59 addresses). Range `10/8`: outside Docker's default address pools (`172.17`–`172.31`, `192.168/16`) and the home Wi-Fi range (`192.168.0.x`). VPC size: free at any size, and `/24` fits the count (5 reserved + 2 machines + 2 during replacement + up to 6 interface endpoints, about 15 per subnet); a smaller VPC only lowers overlap risk on a direct link that does not exist. The `/24` is cut into four `/26` slots: one used now, the others for Phase 7 or later. This follows the "split into four, keep spare" example in the AWS Startups blog "Practical VPC Design" (2014); official guidance gives no number (Well-Architected REL02-BP03). Subnet CIDRs cannot change after creation, and a secondary VPC CIDR cannot come from `10.0.0.0/16` (for example, `10.2.0.0/24`). Rejected: `172.16/12` and `192.168/16`; `/25` (one spare slot); `/27` (27 usable).
     - 2-1 AZ decided (2026-10-30): `apne2-az4` (`ap-northeast-2d`) for the host subnet. On 2026-10-30 all four Seoul AZs were `available` to this account and each offered `t4g.nano`, `t4g.micro`, and `t4g.small` (read-only `describe-availability-zones` and `describe-instance-type-offerings`), so the choice is arbitrary. Each later subnet picks its AZ when it is created, after rechecking offerings; question 3 rechecks if the type is not `t4g`. The account was created after November 2025, so AZ names map to the same AZ IDs as in other accounts.
     - 2-1 `enable_dns_hostnames` decided (2026-10-30): keep the default `false`. The CloudFront origin will use a name under an own domain bought from a registrar other than Route 53 (Route 53 Domains returned "Free Tier accounts are not supported for this service" on 2026-10-30); question 8. Rejected: the EC2 public DNS name (Let's Encrypt refuses `amazonaws.com` names, per its community answers, so CloudFront-to-origin would stay HTTP and carry the `basic_auth` password unencrypted); dropping CloudFront for a Let's Encrypt IP address certificate (validation needs port 80 or 443 open to everyone, which is ADR 0008 option A). A nightly stop (00–08) was costed at about USD 3.75 a month saved on `t4g.micro` but not adopted: it conflicts with the always-on target and brings a new public IPv4 every morning.
     - 2-2 decided (2026-10-30): b, delete the Seoul default VPC through code and the pipeline (`aws_default_vpc` with `force_destroy = true`, then remove the block, because the resource creates a new default VPC when none exists). Reason to delete: in Seoul, a launch without a subnet lands in the default VPC with a public IPv4; after deletion such a launch fails. Chosen over a console deletion (one action, but exception E11 and no record in Git or the approval history) because the change must leave a record (strict IaC, 2026-10-04). Other Regions keep theirs: the pipeline cannot act outside Seoul (P4 `DenyOutsideSeoul`), so deleting them (c) needs a bootstrap change or an exception for little gain. Rejected: a (keep); d (VPC Block Public Access with an exclusion for my VPC: one more setting and exclusion to maintain, and a wrong exclusion cuts off the host). Cost USD 0. Follow-ups for Step 4: check that the default VPC is empty (no instances or network interfaces); check whether the default subnets and internet gateway are deleted with it; consider an alert on `DeleteVpc` (question 6).
     - 2-3 decided (2026-10-30): the outbound path is the subnet route `0.0.0.0/0` to the internet gateway with the host's public IPv4 (ADR 0008, 2-1). Security group = allowlist of protocol and port, deny by default: inbound TCP 443 only from `pl-22a6434b` (`com.amazonaws.global.cloudfront.origin-facing`; the port is final in question 8); outbound TCP 443 to `0.0.0.0/0` only. The outbound destination cannot be narrowed: Systems Manager has no AWS-managed prefix list, and on 2026-10-30 `ssm`, `ssmmessages`, and `ec2messages` resolved to addresses inside EC2 ranges in `ip-ranges.json`. Other 443 services (AL2023 repositories on S3, registry, CloudWatch Logs, ACME, DNS API) pass the same rule. Port 80 stays closed; SSM Agent may use it to download updates from AWS managed S3 buckets (the docs say "an HTTP call"; port 80 is an inference), so question 4 decides, and if needed it opens only to `pl-78a54011` (`com.amazonaws.ap-northeast-2.s3`). New ports are added in the Phase that needs them, through the pipeline. NACL = allow all, plus deny rules for specific IP addresses when needed (in both directions, numbered before the allow rule). Limits: behind CloudFront the NACL sees only CloudFront addresses, so Web attackers are blocked at CloudFront (rate limiting or geographic blocking after the flat-rate switch); the NACL has 20 rules per direction by default. DNS, IMDS, and Time Sync need no rule (not filtered). Rejected: security group allow-all plus a NACL blocklist (default allow; stateless denies on ports 1024 and up can drop replies); narrowing SSM by the `AMAZON` ranges (127 Seoul prefixes over the 60-rule quota, and they include EC2 ranges anyone can rent); SSM interface endpoints (about USD 28.47 a month); a custom guard-rail NACL now. Cost USD 0. Follow-ups for Step 4: confirm the AL2023 repository host on the instance (`/etc/yum.repos.d/`); manage the NACL in code (the default NACL or a custom one); use `aws_vpc_security_group_ingress_rule` and `aws_vpc_security_group_egress_rule` (provider recommendation). Question 6: Flow Logs to watch outbound traffic. 2-4: IPv6 rules.
     - 2-4 decided (2026-10-30): a, IPv4 only. The VPC and the subnet get no IPv6 CIDR block, so there is no IPv6 route and no IPv6 security group or NACL rule. Reason: IPv6 only would remove the public IPv4 (about USD 3.65 a month, or USD 0 if the 750 free hours apply), but on 2026-10-30 only two needed services were confirmed over IPv6: CloudFront origins (since 2025-09-08) and Systems Manager (`*.region.api.aws` endpoints). The image registry, the ACME CA, the DNS provider API, CloudWatch Logs, and the sites Phase 3 collects from were not checked. A single IPv4-only service would need a NAT gateway (about USD 43 a month) or another outbound path. With IPv4, later services work without that check. Rejected: b, dual-stack (the public IPv4 stays, so nothing is saved, and it adds a second address family to filter, scan with `nmap -6`, and log); c, IPv6 only (reopens ADR 0008, and reachability is unverified). Revisit only after checking every needed service over IPv6. Cost USD 0 (the public IPv4 is already counted in ADR 0008).
  3. Compute: OS, instance size, CPU credit mode, root disk size, and the P4 `ec2:InstanceType` allowlist (carry-over).
  4. Host upkeep and permissions: patch in place or replace (and whether scheduled patching is a change under strict IaC), DHMC or instance profile, IMDS hop limit, and `iam:PassRole` scope.
  5. Containers: how they are declared and applied, registry, arm64 image by digest, non-root, and the approval path (carry-over).
  6. Logging: Flow Logs, shipping host logs off the host, retention, and alerts on `StartSession`/`OpenTunnel` (ADR 0007 G1–G5 do not cover them).
  7. AWS User Notifications email contact (carry-over).
  8. Domain and certificates (added 2026-10-30): registrar and TLD (price, and which budget line it counts toward; `docs/vision.md` §5.1 names only Route 53 domains), DNS hosting, how the origin gets a certificate (HTTP-01 is blocked because the security group admits only CloudFront), how the origin record follows a public IPv4 change, whether viewers use the domain on CloudFront, and registrar account security.
- Vision v1.0 (2026-10-24) inputs for Step 3:
  - Self-run is the default candidate for the access layer, the registry, and log shipping; each ADR states every option's class (self-run, primitive, managed) and its Stage 2 exit cost (`docs/vision.md` §5.2).
  - Cloud hosts are file sync endpoints (`docs/vision.md` §2.2): root disk size belongs in question 3, and how a rebuilt host gets its synced files back in question 4.
  - One user only (`docs/vision.md` §5.1 Access); the Web must work in a browser on a laptop, an iPad, and a phone (§4.1 Devices).
- Not yet verified (check before deciding):
  - Whether current AL2023 AMIs set `ImdsSupport` to `v2.0`.
  - Whether a security group silently drops traffic, so nmap shows filtered (inference; Step 5 verifies).
  - Whether the CloudWatch Logs free tier and each candidate service are available on the Free plan, and which vended-log price applies to Flow Logs.
  - Whether the 750 free hours of public IPv4 for Free Tier customers (VPC User Guide, "Pricing for Amazon VPC") apply to this account's Free plan; if so, the about USD 3.65 a month changes.

## 7. Carry-over to next phase
- None yet.
