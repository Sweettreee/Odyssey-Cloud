# Autonomous Personal Cloud Platform
## Idea & Learning Vision Document

| | |
|---|---|
| **Owner** | Noel (김진식) |
| **Status** | Accepted v1.1 |
| **Date** | 2026-10-24 |
| **Document type** | Idea & Learning Vision. This is **not** a software design document. |

> This document explains **what** I want to build, **why** I want to build it, and **what kind of engineer** I intend to become by building it. It deliberately leaves implementation choices open. Architecture decisions will be made later, one problem at a time, and each will be recorded as an ADR.

---

## 1. Summary

I am building an **Autonomous Personal Cloud Platform**: my own cloud service.

**Destination.** The end goal is **my own private cloud on my own hardware**. How it will be built is deliberately undecided (§6, Stage 2). Until then, a public cloud such as AWS serves as the **interim foundation** (Stage 1).

**What the platform provides.**

- **Self-service compute.** Linux and Windows environments can be provisioned on demand, the way a public cloud provider offers them. The details depend on the stage (§4.1).
- **Secure access.** Only I can reach the platform, from anywhere. Sharing with people I approve comes only in Stage 2 (§4.1).
- **A Personal Web UI.** One place for my files and for all the information the platform collects.
- **An AI agent on Slack with two roles.**
  - **SysAdmin:** operates the infrastructure.
  - **Productivity Assistant:** carries out the tasks I assign and automates recurring work.

**Why I am building it.** One goal, reached through one means:

- **Goal:** Become a production-minded Cloud Engineer.
- **Means:** Build and operate my own private cloud service, designed against real problems and real constraints rather than as a tutorial or a showcase.

The everyday problems in §2.2 are those real problems.

---

## 2. Background & Motivation

### 2.1 Why I am building this

| Role | Item | What it means for the project |
|---|---|---|
| Goal | **Become a production-minded Cloud Engineer** | The project is my main vehicle for becoming a Cloud, DevOps, or SRE engineer. Learning means practicing judgment, not using many technologies: every design decision is also a learning exercise (§7), and the options I do not build are compared and explained in the ADRs. |
| Means | **Build and operate my own private cloud service** | I design and operate the cloud itself: virtualization, self-service provisioning, networking, identity, and operations, in an environment that I own and control. What gets built is decided by real problems (§2.2) and constraints (§5.1), never by learning value alone. Using someone else's cloud is not the end goal. |

### 2.2 Everyday problems the platform should also solve

| Problem | Today | Desired state |
|---|---|---|
| Academic information is scattered | I check the LMS, Everytime, department notices, and email separately | One morning briefing tells me today's classes, deadlines, and priorities |
| Career opportunities are scattered | I browse Linkareer, JobKorea, JobPlanet, Incruit, OKKY, Saramin, Jobda, Wevity, and company career pages by hand | Listings from these sources are in one place, ranked by relevance to Cloud, DevOps, and SRE, and new ones are announced in Slack. For each collected source I can trust that a listing missing here is not on that source; sources that cannot be collected completely are kept as links |
| Deadlines slip | I postpone assignments and club tasks ("I'll look later") and then forget them. Personal and club schedules agreed in chats are recorded nowhere | I add a schedule with one short line in Slack, and I get short, readable reminders before each deadline, so a postponed task comes back before it is too late |
| Repetitive work takes my time | I do recurring tasks by hand | I assign tasks to an AI assistant and receive the results |
| Files live on too many devices | Finding a file means guessing where it is | My files stay in sync on every device and host I use, without manual copying, and I can search them in one place, including with natural language |
| I occasionally need another machine | I have no remote Linux or Windows environment | I can start one from Slack when needed, and it stops itself when I am done |

---

## 3. Ultimate Goals

### 3.1 Technical goal
Run **my own private cloud on my own hardware**. How it will be built is decided later (§6, Stage 2). The public-cloud stage is an interim foundation on the way there.

At every stage, the platform must meet these conditions:

- It is secure and observable.
- Its cost stays within budget.
- All infrastructure is defined as code.
- An AI agent can inspect and operate it safely under human control.

### 3.2 Career goal
Be ready for Cloud, DevOps, and SRE roles. The evidence is the live system itself: the README introduces what I built, and the ADRs show how and why I decided, rather than a list of technologies I have "used".

---

## 4. Product Vision

### 4.1 Capability overview

This table is also the **requirements checklist** used in §9.

| Area | Capability |
|---|---|
| **Cloud foundation** | Compute is provisioned on demand through self-service, as with a public cloud provider. **Stage 1:** a public cloud provides the physical hosts and hypervisor, and my platform provisions compute as code through the CI/CD pipeline, after my approval. I am the only user, so I expect little reason to change host or resource size dynamically; containers and Windows sessions still start and stop on demand. Nothing is shared with other people. **Stage 2:** my own private cloud on my own hardware. Its main goal is to provision my own compute resources and share them with other people, each share approved by me; to be designed later (§6, Stage 2). |
| **Secure access** | Reachable from anywhere. Access is limited to me through a VPN or zero-trust layer, with a private network and least-privilege identities. **Stage 2:** people I approve one by one can reach only what I share with them. |
| **Linux compute** | Lightweight containers are provisioned on demand. **Stage 1:** they run on Linux instances. **Stage 2:** to be designed later. |
| **Windows compute** | Windows is provisioned **on demand only**, in two modes: CLI/script execution and a full GUI desktop over RDP or VNC. **Stage 1:** separate on-demand instances from the provider. **Stage 2:** to be designed later. |
| **Personal Web UI** | The place where I look at results; what it must show is listed below the table. It never changes infrastructure and is not an operations console; commands go through Slack. As a starting point, the only thing I change on it is my own files (upload, download, and delete); the exact set of writes is decided in the phase that builds each view. The AI agent can read, analyze, and search the files. **Beautiful UI/UX is a requirement.** Screens, layout, and design are decided in the phase that builds each view. |
| **AI SysAdmin** | It can query resources and monitor the platform, and it runs first-level recovery. Every infrastructure change it proposes, such as creating or starting a resource or allocating CPU, RAM, and storage, is written as code and reaches the cloud only through the pipeline after **Review & Confirm**. |
| **AI Productivity Assistant** | It **carries out tasks I assign and automates recurring work**. The first capabilities are examples, not the full scope: collecting LMS schedules, notices, class materials, and career listings; morning briefings; deadline alerts; and natural-language search (RAG) over files and collected data. Any task with an external effect (sending, submitting, booking, and similar) requires **Review & Confirm**. Its capabilities grow over time by adding tools as needed, through one standard tool interface (for example, MCP servers). Each new tool is a part like any other: it follows the order in §5.2 and gets only the permissions it needs. |
| **Devices** | Mainly a laptop and an iPad. Everything I use day to day (the Web UI, my files, Slack, and the secure access path to them) also works on my phone. |
| **Interface** | Slack is the interface for all commands, alerts, and briefings. |

**What the Personal Web UI must show.** Screens and layout are decided in the phase that builds each view.

- **Time view, seen first:** classes, assignments, exams, my own schedules, and deadlines on one time axis: this week, then this month, then the whole semester.
- **Career listings:** job, internship, and contest listings with filtering, search, and priority by relevance to Cloud, DevOps, and SRE, plus links to the sources that are not collected. Later: my application history (when I applied, the replies, and the schedules that follow), shown in the time view.
- **Automation status:** each automated job, its run history, and the last successful collection per source, with whether each one ran correctly shown first.
- **Notices, class materials, and briefing history.**
- **My files.**

### 4.2 Problem-first framing

Each capability starts from a question, not from a service name.

- How can I eventually run **a cloud of my own**, and how do I keep today's public-cloud work from blocking that move?
- How can I reach my environment from anywhere **without exposing anything unintended** to the public internet?
- How can I use a Windows desktop occasionally **without paying for it while it sits idle**?
- How can an AI operate my infrastructure **without ever being able** to destroy something I did not approve?
- How can I **hand off recurring work** to an AI and only receive the results, while it still cannot take external actions without my approval?
- How do I learn that a collector broke **before** I notice a missing deadline?
- How do I keep the whole platform within a **fixed monthly budget** while it keeps growing?

---

## 5. Guiding Principles & Constraints

### 5.1 Hard constraints

| Constraint | Detail |
|---|---|
| **Budget** | Separate monthly budgets in USD. **AWS:** target under USD 20, ceiling USD 25; alerts are automated. A domain registered through Route 53 counts toward the AWS budget. **AI API (agent):** under USD 10; capped by a monthly spend limit set at the provider, and tracked manually. Usage covered by credits counts as cost. Subscriptions, such as Claude Code and Slack, are not included. If a ceiling cannot be met, the options and trade-offs are reviewed with me before any decision. It is never exceeded silently. |
| **Host OS** | In Stage 1, Linux is the OS for every host I operate, such as container hosts. Stage 2 is undecided. |
| **Windows** | Windows runs on demand only and never stays on. Auto-shutdown is mandatory. |
| **Human-in-the-loop** | The AI may query resources and propose infrastructure changes as code. Two kinds of action always require explicit confirmation: every infrastructure change, including create, start, modify, stop, and delete, which reaches the cloud only through the pipeline after my approval; and delegated tasks with external effects. This must be enforced by permissions, not just by the prompt. How automatic actions, such as first-level recovery and Windows auto-stop, fit this rule is decided in the phase that builds them. |
| **Infrastructure as Code** | There is no ClickOps. Every resource and every service is deployed through code and CI/CD pipelines, except for exceptions recorded in an ADR. |
| **Access** | In Stage 1, only I can reach the platform. In Stage 2, people I approve one by one can reach only what I share with them (§4.1). |

**AWS budget allocation.** The AWS target is split by capability, so early phases leave room for later ones. Each phase confirms or adjusts its line at Step 1. The lines add up to the target.

| Capability (Phase) | USD per month |
|---|---|
| Foundations & guardrails (0) | 0.5 |
| Secure access & Linux compute (1) | 12 |
| Web UI & storage (2) | 2 |
| Collectors, observability, and agent infrastructure (3–6) | 1.5 |
| Windows on demand (7) | 3 |
| Reserve (yearly domain fee, price changes) | 1 |
| **Total (AWS target)** | **20** |

### 5.2 Design principles

When these principles pull against each other, this order decides:

1. **Hard constraints** (§5.1), the blank-page gate, and the Stage 2 block test (below). An option that fails any of them is not a candidate.
2. **Self-run by default** (below).
3. **Fewest moving parts**, then **least ongoing operation** (below).

Learning value and résumé value never justify adding a part or choosing a more complex option (§2.1).

- **The private cloud is the destination; I run its parts myself by default.** The public-cloud stage is interim. Stage 1 choices must not block a later move to my own hardware. An option blocks it if leaving it would force a redesign of other parts, or if its data could not be taken out. Every part is one of these:
  - **Self-run:** existing software that I install, configure, update, and operate on compute I control, depending on nothing the provider runs except primitives. Self-run does not mean writing the software myself.
  - **Primitive:** a basic resource that any infrastructure, my own hardware included, provides: compute, networks and firewall rules, disks and object storage, identities and permissions, audit logs, and commodity internet services such as domain names. Controls that exist only to watch or bill the provider account, hold no platform data, and disappear with the account also count.
  - **Managed service:** any part whose software or control plane someone else runs: a higher-level provider service, a third party's hosted control plane (even when its agent runs on my host), or a hosted product.
  - A managed service replaces a self-run part only through an ADR that shows one of these: every self-run and primitive option fails step 1; self-run is clearly worse on security or availability; or running it myself takes more operation or development work than I accept. The last is my call, made at design time or later when the burden shows up. The ADR records the burden and what leaving the managed service would cost.
  - The default decides how a needed part is provided, never whether a part is needed (§2.1). Services this document already sets, such as the chat interface and the AI API, are outside it.
- **Infrastructure and data collection come first; AI comes in stages.** Deterministic collection, briefings, and alerts come first. The AI is added in layers: read-only first, then actions and delegated tasks under confirmation. Rule-based components are not throwaway work: they become the agent's tools and remain as fallbacks.
- **Keep it simple.** Among the candidates the order above leaves, pick the simplest. Avoid resume-driven development.
  - **Gate:** I can explain every part of the design, and why it exists, on a blank page (§7.1). A design that fails this is not a candidate.
  - **Then compare, in order:**
    1. **Fewest moving parts:** fewer components, services, and connections that I must run.
    2. **Least ongoing operation:** less patching, upgrading, and manual work after it is built.
  - Cost is not a simplicity criterion. It is a hard constraint (§5.1).
- **Keep the platform extensible.** New services should plug in without re-architecting.
- **Log for security across the whole platform.** Keep access and action logs for everything, not only the AI: sign-ins, file access, resource changes, and agent actions. Logs must be reviewable.
- **Beautiful UI/UX is a requirement.** It is not an afterthought.
- **Treat collected content as untrusted.** Web pages, notices, and tool results that the AI reads may contain text that tries to steer it. That content must never be able to trigger infrastructure actions or delegated tasks.
- **Limit what leaves the platform.** Personal data sent to an outside service, such as the AI API, is limited to what each task needs.

### 5.3 Working principles

- **Assume no prior knowledge.** The project starts as if I know nothing about the technologies it uses. What I need to learn is laid out phase by phase (§6, Phase Learning Brief).
- **Explain like I'm 12 first, then technically.** Every explanation starts with the simplest version, then gives the short technical version.
- Before any implementation, write down what I am doing, why, which alternatives I considered, and the trade-offs. Implement only once I fully understand the plan.
- Record every significant decision as an **ADR**.
- AI-generated code is reviewed and applied by me, never pasted in blindly. One exception: the Web UI's look and feel (layout, styling, and visual components) may be designed and built with AI, and I judge it by the result. Web UI code at a trust boundary (sign-in, sessions, file handling, and data access) is reviewed like any other code.
- Documentation, code, and UI labels are all written in English.

### 5.4 Known cost traps to evaluate early

These do not rule anything out; I need to check them before designing.

- **Hourly base charges.** Some managed services have base charges that can exceed the whole monthly budget by themselves. Examples include always-on NAT gateways, managed client VPN endpoints, and load balancers.
- **Public IPv4 addresses** are billed as well.
- **Windows** requires x86 hardware and costs more per hour than Linux.
- **LLM API usage** grows with every briefing, query, and delegated task.

Current prices must be verified at design time. The goal is **the best solution within the budget**, not simply the cheapest one.

---

## 6. Phased Roadmap (conceptual)

The roadmap has two stages.

- **Stage 1** builds the platform on a public cloud as an interim foundation.
- **Stage 2** moves it onto my own hardware as a private cloud. Its design has not started.

The phases run in order, one at a time. They are ordered by dependency and risk, not by fixed dates. Each phase has a problem, a scope, a learning focus, exit criteria, and a **Phase Learning Brief**.

**Phase Learning Brief.** Instead of explaining every concept as it comes up, each phase has two lists:

- **Before starting:** topics to study before designing the phase.
- **Before moving on:** what I must be able to explain on a blank page before going to the next phase.

The lists stay at topic level and do not name specific tools, so they do not lock in any design. **They are guidelines only.** At the start of each phase, they are reviewed again and refined. Concepts outside the lists are explained when I ask, following the explain-like-I'm-12 rule.

### Stage 1: Public Cloud (interim foundation)

#### Phase 0: Foundations & Guardrails
- **Problem:** Nothing can be built safely if a mistake can quietly cost money or open access.
- **Scope:**
  - Account hardening: root lockdown, MFA, and no long-lived keys.
  - AWS budget alerts at 50%, 75%, 90%, and 100% of the AWS target, and when the AWS ceiling is reached.
  - An IaC repository with remote state.
  - Infrastructure CI/CD: a plan on every pull request, and apply after merge behind an approval gate.
  - Short-lived credentials for the pipeline instead of stored keys.
  - A baseline for security logging.
- **Learning focus:** Security and Cost.
- **Exit criteria:**
  - Every resource exists because of code.
  - Infrastructure changes reach the cloud only through the pipeline.
  - Test alerts for every AWS budget threshold reach Slack.
- **Learning Brief (guideline):**
  - *Before starting:*
    - Cloud account structure and the shared responsibility model.
    - Identity and access basics: users, roles, policies, least privilege, and MFA.
    - How cloud billing works, and budget alerts.
    - Git basics and the pull request flow.
    - What IaC is, and why it needs state.
    - What CI/CD is, and how a pipeline authenticates to a cloud (long-lived keys vs. short-lived credentials).
  - *Before moving on, I can explain:*
    - Why the root account should not be used day to day.
    - What happens between opening a pull request and the change reaching real infrastructure.
    - Why state is stored remotely.
    - The account's trust boundaries, drawn on a blank page.

#### Phase 1: Secure Access & Linux Compute
- **Problem:** I need to reach my own environment from anywhere, with nothing unintentionally exposed.
- **Scope:** A private network, a VPN or zero-trust access layer, and Linux instances that host on-demand containers.
- **Learning focus:** Traffic, Security, and Compute.
- **Exit criteria:**
  - An external scan shows only what is intended.
  - A container can be created and destroyed through code within minutes.
  - Access attempts are logged.
- **Learning Brief (guideline):**
  - *Before starting:*
    - Networking basics: IP addresses, subnets, CIDR, ports, DNS, and routing.
    - Public vs. private networks, and how private resources reach the internet (NAT).
    - Firewalls: inbound and outbound rules, and stateful filtering.
    - Secure communication basics: public and private keys, TLS, and SSH.
    - VPN vs. zero-trust access.
    - Linux basics: the shell, file system, permissions, processes, and service management.
    - VMs vs. containers, and images and registries.
  - *Before moving on, I can explain:*
    - The path a request takes from my device to a container.
    - Why only the Web entry is reachable from the internet, and what an outsider sees there.
    - The access approach I chose, the alternatives I rejected, and their cost difference.

#### Phase 2: Personal Web UI & Storage
- **Problem:** My files are spread across devices.
- **Scope:**
  - Durable storage, file sync across my devices and hosts (the method is decided in this phase), an authenticated Web UI for upload and download, encryption at rest, and lifecycle rules. Views for collected data are added in Phase 3.
  - **Application CI/CD** starts here, with the Web UI as the first service: build, test, package, deploy, and roll back. Every later service reuses it.
- **Learning focus:** Data, Security, Cost, and delivery automation.
- **Exit criteria:**
  - I can upload from my phone off-campus.
  - A file I add or change on one device appears on my other devices and hosts within the target set at Step 1.
  - A deleted or overwritten file can be restored.
  - A lost device can be cut off from my files without affecting the others.
  - I judge the UI beautiful and easy to use on my laptop, iPad, and phone.
  - File access is logged.
  - A Web UI change can be deployed and rolled back through the pipeline.
  - Storage cost stays bounded by policy.
- **Learning Brief (guideline):**
  - *Before starting:*
    - Object vs. block vs. file storage.
    - Encryption at rest and in transit.
    - Web basics: HTTP, frontend and backend, and APIs.
    - Authentication vs. authorization, and sessions vs. tokens.
    - Security risks of file uploads.
    - Image builds, automated tests, deployment strategies, and rollback.
  - *Before moving on, I can explain:*
    - How a file is synced, uploaded, stored, and downloaded, and the security control at each step.
    - What drives storage cost and how it is controlled.
    - How a code change gets deployed, and how it is rolled back.

#### Phase 3: Data Collection & Delivery: Building the Agent's Tools
- **Problem:** Academic and career information is scattered, and deadlines slip.
- **Scope:**
  - Scheduled collectors for the LMS, the class timetable (Everytime), notices, class materials, my email (Gmail: applications and subscriptions), and career sites (§2.2). A career source is collected only when it can be collected completely and its terms allow it; the others are kept as links. I can add a company career page as a new source.
  - Adding a schedule with one short line in Slack.
  - A normalized store for the collected data.
  - A **template-based** morning briefing and deadline alerts in Slack.
  - Web UI views for the collected information.
  - Each capability is built as a reusable tool with a clear interface, so the agent can call it later.
  - The template briefing remains as the fallback when the AI is unavailable.
- **Learning focus:** Compute (scheduling), Data, and Observability.
- **Exit criteria:**
  - Briefings arrive every weekday for several consecutive weeks without manual fixes.
  - A broken collector raises an alert before I notice missing data.
  - A spot check of each collected source finds no listing missing since its last successful collection, and that time is visible for every source.
  - All collected information can be browsed in the Web UI.
- **Learning Brief (guideline):**
  - *Before starting:*
    - Scheduled jobs.
    - Collection methods compared: official APIs, feeds, email subscriptions, and scraping, including legal and ethical limits such as terms of use and robots.txt.
    - Secrets management.
    - Data modeling basics: relational vs. NoSQL, schemas, and de-duplication.
    - Idempotency and retries.
    - How Slack bots work: webhooks and events.
    - Tool interface design: functions with clear inputs and outputs.
  - *Before moving on, I can explain:*
    - What alerts me, and how, when a collector fails.
    - Why collecting the same data twice causes no problem.
    - How the agent will call these capabilities later.

#### Phase 4: Observability & Recovery Tools
- **Problem:** I want to know about a failure before I feel its effects.
- **Scope:** Metrics, logs, Slack alerts, and first-level recovery (such as restarting a failed service), written as runbook tools the agent can call later. How recovery automation fits the confirmation rule is decided in this phase.
- **Learning focus:** Observability.
- **Exit criteria:**
  - An injected failure is detected and recovered automatically.
  - Time to detect and time to recover are measured.
- **Learning Brief (guideline):**
  - *Before starting:*
    - The three pillars of observability: metrics, logs, and traces.
    - Alert design: thresholds, alert fatigue, and severity.
    - Health checks and failure types.
    - Reliability metrics such as MTTD and MTTR, and SLO basics.
    - What a runbook is, and the risks of automated recovery.
    - Failure injection testing.
  - *Before moving on, I can explain:*
    - How a specific failure travels from occurrence to detection.
    - Which recoveries are automated and which need a human, and the criteria behind that split.
    - What my measured detection and recovery times mean.

#### Phase 5: AI Agent, Read-Only
- **Problem:** Questions like "What is due this week?", "What is running?", and "Where is that file?" take too many clicks.
- **Scope:**
  - A Slack agent with **read-only** access to infrastructure state and data.
  - RAG over my files and the collected data.
  - The agent uses the Phase 3 tools, including AI summaries on top of the briefing. The template briefing remains as the fallback.
- **Learning focus:** Security (agent identity) and Cost (LLM usage).
- **Exit criteria:**
  - The agent physically cannot change anything.
  - Answers cite their sources.
  - LLM spend is tracked separately.
- **Learning Brief (guideline):**
  - *Before starting:*
    - LLM basics: tokens, context, and cost structure.
    - Tool use (function calling) and the agent loop.
    - RAG: embeddings, vector search, chunking, and source citation.
    - How vector data is stored.
    - Prompt injection and untrusted input.
    - Agent identity and read-only permission separation.
    - Tracking and limiting LLM cost.
  - *Before moving on, I can explain:*
    - Why the agent cannot change anything, at the permission level.
    - The flow from a question to an answer: retrieval, tool calls, and citations.
    - Where injected instructions in collected web content are stopped.
    - How the fallback works when the AI fails.

#### Phase 6: AI Agent, Actions & Delegated Tasks with Human-in-the-Loop
- **Problem:** I want to operate the infrastructure from Slack and hand off real work to the AI, without risk.
- **Scope:**
  - **Infrastructure:** The agent proposes every change, including create, scale, start, and stop, as code. Each change goes through Review & Confirm and reaches the cloud only through the pipeline, which is the separate, elevated path.
  - **Delegated tasks:** The assistant carries out tasks I assign and automates recurring work. Tasks with external effects go through the same confirmation gate.
  - The agent can also trigger the Phase 4 recovery runbooks.
  - Every action is written to an audit log.
- **Learning focus:** Security and Observability.
- **Exit criteria:**
  - A destructive infrastructure action or an externally visible task is impossible without confirmation, at the permission level.
  - Every agent action can be traced.
- **Learning Brief (guideline):**
  - *Before starting:*
    - Separating elevated permission paths, and designing approval flows.
    - Limiting write access: least privilege and narrowly scoped credentials.
    - Audit log requirements: who, what, when, and the result.
    - Authentication for external services (for example, OAuth).
    - Reversible vs. irreversible actions.
    - Designing task automation: triggers, schedules, and failure handling.
  - *Before moving on, I can explain:*
    - Why a destructive action is impossible without confirmation, at the permission level rather than the prompt level.
    - The path one delegated task takes from request to completion, and what gets recorded.
    - The blast radius if the agent were compromised.

#### Phase 7: Windows On-Demand (CLI and GUI)
- **Problem:** I occasionally need Windows.
- **Scope:** On-demand Windows instances from the provider, for scripts and for full desktop sessions through the secure access layer, with enforced auto-stop.
- **Learning focus:** Compute and Cost.
- **Exit criteria:**
  - The start, use, and auto-stop cycle works end to end.
  - Windows cost is tracked separately and stays within budget.
- **Learning Brief (guideline):**
  - *Before starting:*
    - Windows Server basics: licensing, remote access (RDP), and PowerShell.
    - Instance lifecycle: start, stop, and terminate, and how billing differs for each.
    - Idle detection and auto-shutdown approaches.
    - Securing the remote desktop connection path.
    - Using images (snapshots) for faster startup.
  - *Before moving on, I can explain:*
    - The full path of one Windows session, from start to auto-stop.
    - The cost difference between stopping and terminating.
    - Why Windows cost stays within the budget.

### Stage 2: Private Cloud on My Own Hardware (destination)

#### Phase 8: Private Cloud on My Own Hardware
- **Trigger:** Stage 1 is complete, or I start considering a server purchase.
- **Goal:** My own private cloud on my own hardware.
- **Status:** Every technical choice is undecided. Design starts at the trigger.
- **Topics to discuss then** (ideas only, not decisions):
  - Choice of platform (OpenStack or others).
  - How to provide IaaS.
  - Preference for fast bare-metal containerization.
  - How to run Windows.
  - Where to practice before buying hardware.
  - Whether hardware and electricity count toward the monthly budget.
  - Moving IaC and CI/CD targets to my own cloud.
- **Learning Brief:** Written when Stage 2 design starts.

---

## 7. Learning Vision

### 7.1 How I will learn

| Method | How it applies here |
|---|---|
| **Phase Learning Brief** | Each phase lists what to study before starting and what I must be able to explain before moving on (§6). The lists are guidelines, reviewed and refined at the start of each phase. Explanations follow the explain-like-I'm-12 rule. |
| **Problem-first, top-down** | Every phase starts from a concrete constraint (§4.2, §6). Service choices come last. |
| **Recursive gap-filling with AI** | I design first. Then I ask AI to stress-test my design and to explain concepts until I can explain them myself: first simply, then technically. AI does not design the system for me. |
| **Avoiding the tutorial trap** | Before implementing, I close every tab and draw the architecture on a blank page. If I cannot explain *why* something is there, I am not ready to build it. |
| **6-Layer Decision Stack** | Every significant decision is checked against Traffic, Compute, Data, Security, Cost, and Observability. The result is recorded in the ADR. |
| **ClickOps to IaC** | All infrastructure is written in Terraform and deployed through CI/CD. The console is used only for reading. |

### 7.2 Competency map

| Competency | Where the project exercises it | Evidence I will produce |
|---|---|---|
| System design & trade-offs | Every phase, especially access, Windows on-demand, agent permissions, and the move to a private cloud | ADRs with alternatives and rejected options |
| Network & security | Private network, zero-trust access, least-privilege identities, agent isolation, and platform-wide security logging | Trust-boundary diagram, external scan results, and log reviews |
| Cost engineering | The AWS budget (USD 20 target, USD 25 ceiling), the AI API budget (under USD 10), on-demand Windows, and LLM usage | Monthly cost reports, split into AWS and AI API |
| Infrastructure as Code & CI/CD | Every phase | Repository history, infrastructure and application pipelines, and a rebuild-from-zero test |
| Observability & reliability | Phases 3 and 4 | Dashboards, alert history, and measured detection and recovery times |
| Automation & data pipelines | Collectors, briefings, and delegated tasks | Collector success rates, automated task history, and a log of how failures were handled |
| Safe AI operations | Phases 5 and 6 | Permission model, confirmation flow, and audit log |
| Private cloud | Phase 8 (details decided in Stage 2) | To be defined in Stage 2 |

**Priority.** Every competency above is an important learning target except Automation & data pipelines. That one is lower for learning: its features may matter in daily use, but studying it in depth is not a goal.

---

## 8. Outcomes & Portfolio

### 8.1 Artifacts
- A public repository (secrets and personal data excluded) containing IaC, the pipelines, and a README that introduces what I built.
- An ADR log and architecture diagrams for each phase.
- One introduction video for my portfolio, made when the project is done.

### 8.2 Metrics to track from day one

- Monthly cost for AWS and for the AI API, each compared with its own budget.
- Time to rebuild the environment from zero.
- Deployment frequency, deployment lead time, and failed deployment rate.
- Share of resources managed by code (target: 100%).
- Time to detect and time to recover from failures.
- Collector success rate and briefing delivery rate.
- Agent actions and delegated tasks: count, confirmations requested, and actions blocked.
- Coverage of security logging across components.

---

## 9. Success Criteria

- **Every requirement in §4.1 is delivered and works reliably.** The platform provides the features I need.
- Each monthly budget stays within its target where possible and never passes its ceiling without a prior decision.
- The whole environment can be rebuilt from code.
- Security-relevant access and actions are logged and reviewable.
- For every component, I can explain why it exists, what alternatives I rejected, and what it costs.
- The portfolio artifacts in §8.1 exist and are public.
- **Destination:** my own private cloud runs on my own hardware. Its success criteria are defined in Stage 2.

## 10. Non-Goals

- A commercial or public multi-tenant service. In Stage 2, sharing my compute with people I approve one by one (§4.1) is not excluded.
- Multi-region high availability.
- Technologies adopted mainly to decorate a résumé.
- Training or hosting my own LLM.
- Any autonomous destructive or externally visible action by the AI.

## 11. Risks

| Risk | Mitigation direction |
|---|---|
| Cost overrun | AWS budget alerts (50%, 75%, 90%, and 100% of the target, and the ceiling), manual AI API tracking, on-demand defaults, and a monthly cost review. If a ceiling cannot be met, options and trade-offs are reviewed with me before any decision. |
| Breach of a personal platform that holds credentials | Least privilege, secret management, a minimal public surface, and platform-wide security logs |
| AI misuse or prompt injection through collected content | Read-only first, a permission-level confirmation gate, and treating collected data as untrusted |
| Delegated tasks acting wrongly in external services | Narrowly scoped credentials, confirmation for external effects, and an audit trail |
| Collectors breaking when sites change | Failure alerts, and a preference for official APIs, subscriptions, or feeds over scraping |
| Sync spreads a deletion or damage to every copy | Earlier versions are kept so a file can be restored (Phase 2) |
| Scope creep and burnout | Strict phase exit criteria, with one phase active at a time |
| Falling back into the tutorial trap | The blank-page explanation is required before every build |

---

## 12. Open Questions (next review)

1. **Authorized personnel (answered 2026-10-04, changed 2026-10-24):** In Stage 1 the platform is only for me; nothing is shared or lent to other people. In Stage 2, sharing my compute with people I approve one by one is a goal (§4.1).
2. **LMS, Everytime, and email access:** How will the collectors authenticate to each? Do their terms of use allow automated access?
3. **Interim cloud provider and region (answered by ADR 0001):** AWS in the Seoul region (`ap-northeast-2`).

---

## 13. Change log

| Version | Date | Summary |
|---|---|---|
| 1.0 | 2026-10-24 | One goal (become a production-minded Cloud Engineer) and one means (my own private cloud service). Self-run by default, with a written order of precedence. Nothing is shared in Stage 1. The Web is for results, with a list of what it must show. Added devices, file sync, career sources and trust, schedules, tools for the AI, and an AI-built UI look and feel. Set the learning priority. The portfolio is now the README, the ADRs, and one video. Removed the timeline. |
| 1.1 | 2026-10-24 | Phase 1 chose one public Web entry, so the §4.2 access question and the Phase 1 "before moving on" item now allow one intended entry instead of no exposure at all. |

Earlier versions are in the git history.
