# Phase 1: Secure Access & Linux Compute (working notes)

> Recovery point for this Phase and the source for the STATUS.md report.
> Update at the end of each learning topic, decision, and implementation step. Keep it short; this is not a transcript.

**Phase status:** In progress
**Current step:** 3 Design & decisions (since 2026-10-18)
**Next action:** Design question 1 (access layer). The question list and unverified facts are in §6.
**Last updated:** 2026-10-18

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
- [ ] Why I can connect even though no ports are open to the public.
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
| — | — | — |

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
  1. Access layer: Session Manager, EICE, Tailscale, Cloudflare, or a self-hosted VPN (including SSH host keys on rebuild).
  2. Network: public IPv4 or IPv6 only, the outbound path, and the default VPC (carry-over).
  3. Compute: OS, instance size, CPU credit mode, root disk size, and the P4 `ec2:InstanceType` allowlist (carry-over).
  4. Host upkeep and permissions: patch in place or replace (and whether scheduled patching is a change under strict IaC), DHMC or instance profile, IMDS hop limit, and `iam:PassRole` scope.
  5. Containers: how they are declared and applied, registry, arm64 image by digest, non-root, and the approval path (carry-over).
  6. Logging: Flow Logs, shipping host logs off the host, retention, and alerts on `StartSession`/`OpenTunnel` (ADR 0007 G1–G5 do not cover them).
  7. AWS User Notifications email contact (carry-over).
- Not yet verified (check before deciding):
  - Which needed services are reachable over IPv6 only.
  - Whether current AL2023 AMIs set `ImdsSupport` to `v2.0`.
  - Whether a security group silently drops traffic, so nmap shows filtered (inference; Step 5 verifies).
  - Whether the CloudWatch Logs free tier and each candidate service are available on the Free plan, and which vended-log price applies to Flow Logs.

## 7. Carry-over to next phase
- None yet.
