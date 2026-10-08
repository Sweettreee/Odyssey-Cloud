# ADR 0007: Security logging baseline and protection of the logging and alert path

- **Status:** Accepted
- **Date:** 2026-10-02
- **Phase:** 0
- **Amends:** ADR 0004 (P1, P3, P4, OIDC subject format, setting S15, workflow rules); ADR 0006 (SNS topic policy)

## Context
Phase 0 scope includes "A baseline for security logging" (`docs/vision.md` §6, Phase 0), and the design
principles say "Keep access and action logs for everything ... Logs must be reviewable" (`docs/vision.md` §5.2).
ADR 0004–0006 handed D7 these items:
- Protect CloudTrail, its log bucket, and the budget alerts from the pipeline, in place no later than E4
  (ADR 0004 EP-22; ADR 0006 hand-offs).
- An external access analyzer, and an alert on trust and resource-policy changes, including any role other than
  `pipeline-plan`/`pipeline-apply` whose trust names the GitHub OIDC provider (ADR 0004 EP-21).
- An alert on every apply-role assumption that lets me tell my own applies from others (ADR 0004 EP-24;
  ADR 0005 E9), and a root sign-in alert (ADR 0005).
- Security alerts as custom notifications through the ADR 0006 topic, with an EventBridge statement in its policy (ADR 0006).

D7 was split into four questions, decided in order: (a) trail, (b) alerts, (c) IAM Access Analyzer, and
(d) protection Denies. Two further items found while deciding them are recorded here: (e) the Region of the
apply-role assumption, and (f) removal of GitHub setting S15.

## Decisions at a glance

| # | Question | Chosen | Not adopted |
|---|---|---|---|
| (a) | Trail | One multi-Region trail in `bootstrap`; management events, read and write; data events for the state bucket; dedicated S3 log bucket that denies object deletes | Other data events, Insights events, CloudWatch Logs delivery, log expiry |
| (b) | Alerts | Groups G1–G5 through EventBridge to the ADR 0006 topic; hub in `ap-northeast-2`, forwarding from us-east-1, us-east-2, and us-west-2 | Alerts on plan-role use and on IAM user sign-in failures |
| (c) | Access Analyzer | One external access analyzer in `ap-northeast-2`, zone of trust = this account | Archive rules |
| (d) | Protection | Seven Deny statements in P4, including a service-wide Deny for CloudTrail, Budgets, Amazon Q Developer, and Access Analyzer | `NotAction` with `Resource: "*"`; resource-scoped Denies for those four services; a tag-based Deny |
| (e) | Assumption Region | P3 requires `aws:RequestedRegion` = `ap-northeast-2` | Forwarding rules in all 17 default Regions (fallback); deactivating STS in unused Regions |
| (f) | S15 | Drop S15; P1 and P3 check the `ref` condition key | Keep S15 (fallback) |

## Decision

### (a) Trail
- One trail, `bootstrap-trail`, in the `bootstrap` module, so it exists no later than E4 (ADR 0004 EP-22).
  It is a multi-Region trail with `ap-northeast-2` as its home Region. "When you create a multi-Region trail, CloudTrail
  records events in all AWS Regions that are enabled in your AWS account" [CT1].
- Management events, read and write. Read events are required: `AssumeRoleWithWebIdentity` is logged as read-only [IT1],
  and G2 depends on it (b).
- Data events for the state bucket only (added 2026-10-04, Phase 0 review), so reads and writes of state are logged
  (vision §5.2 "file access"). The trail uses advanced event selectors: one for management events
  (`eventCategory` = `Management`) and one with `eventCategory` = `Data`, `resources.type` = `AWS::S3::Object`, and
  `resources.ARN` starting with `arn:aws:s3:::<STATE_BUCKET>/`. A trail uses either basic or advanced event
  selectors, not both [CT6].
  - No data events for the log bucket: logging data events for the bucket that receives the trail's own log files
    makes CloudTrail log a data event each time it delivers a log file [CT6].
  - Cost: USD 0.10 per 100,000 data events [CT2]; about USD 0.001/month at plan and apply volumes (inference;
    Step 4 measures it).
- Not used: Insights events (charged per event [CT2]) and CloudWatch Logs delivery (alerts use
  EventBridge, which receives CloudTrail events only while a trail with logging is on, ADR 0006 [EB2]).
- Cost: "You can deliver one copy of your ongoing management events to your S3 bucket at no charge ... however, there
  are Amazon S3 storage charges" [CT1]. Additional copies cost USD 2.00 per 100,000 management events [CT2], so there
  is exactly one trail. Step 4 measures the log storage and request cost.
- Log bucket `<LOG_BUCKET>` (name starts with `bootstrap-`) in `ap-northeast-2`, used only for this trail ("As a best
  practice, use a dedicated S3 bucket for CloudTrail logs" [CT3]):
  - Versioning on; all public access blocked.
  - Bucket policy: the two CloudTrail statements (`s3:GetBucketAcl`, `s3:PutObject` with
    `s3:x-amz-acl` = `bucket-owner-full-control`), each with `aws:SourceArn` = the trail ARN [CT3].
  - A third statement (added 2026-10-04) denies `s3:DeleteObject` and `s3:DeleteObjectVersion` on `<LOG_BUCKET>/*`
    to every principal (`"Principal": "*"`). Object deletes are data events that this trail does not log; with this
    statement, deleting a log file first needs `PutBucketPolicy`, a management event that G4 alerts on.
  - Encryption: SSE-S3, the S3 default, "at no cost" [S3E]. No KMS key (USD 1/month avoided, ADR 0006 [K1]).
  - No lifecycle expiry: logs are kept indefinitely.
  - `lifecycle { prevent_destroy = true }` on the bucket (added 2026-10-07 at Step 4), as for the state bucket
    (ADR 0003): a plan that would delete the bucket fails at review time.
- Log file integrity validation on. CloudTrail delivers an hourly digest file, uses "SHA-256 for hashing and SHA-256
  with RSA for digital signing", and can show whether a log file "was modified, deleted, or unchanged" [CT4].
- E1–E3 happen before the trail exists; they are visible only in CloudTrail Event history [IT1] and in ADR 0003.
- Protection from the pipeline: P4 (d).

### (b) Alerts

#### Groups and event patterns
Every rule pattern includes `"account": ["<ACCOUNT_ID>"]`; AWS recommends an `account` field so that rules "do not
match any events sent from other accounts" [EB4]. G1–G5 use CloudTrail events, which reach EventBridge only while
the trail is logging [EB3].

| Group | Rule (Seoul) | Matches | Notes |
|---|---|---|---|
| G1 Root activity | `bootstrap-g1-root` | `detail.userIdentity.type` = `Root` | API calls, console sign-ins, and `aws login` sign-in events |
| G2 `pipeline-apply` assumed | `bootstrap-g2-apply-assumed` | source `aws.sts`, `eventName` `AssumeRoleWithWebIdentity`, `requestParameters.roleArn` = the apply role ARN, no `errorCode` | Successful assumptions only. Because of (e), they happen only in `ap-northeast-2`, so G2 is not forwarded |
| G3 IAM changes | `bootstrap-g3-iam` | source `aws.iam`, `readOnly` = false | Every IAM write, including roles, trust policies, users, access keys, login profiles, MFA, and identity providers |
| G4 Logging and alert path changes | `bootstrap-g4-logging-path` | `readOnly` = false and any of: source `aws.cloudtrail`, `aws.chatbot`, or `aws.access-analyzer` (detail-type `AWS API Call via CloudTrail`); EventBridge calls on rules named `bootstrap-*`, `UpdateEventBus`, `PutPermission`, `RemovePermission`; SNS calls on topic or subscription ARNs matching `arn:aws:sns:*:<ACCOUNT_ID>:bootstrap-*`; S3 calls on `<LOG_BUCKET>` | Includes analyzer and archive-rule changes (c) |
| G5 Budget changes | `bootstrap-g5-budget` | source `aws.budgets`, `readOnly` = false | Includes the temporary USD 0.01 test budget in Step 4 (expected alerts) |
| Access Analyzer findings | `bootstrap-access-analyzer` | see (c) | |

- Denied attempts are not filtered out of G1, G3, G4, and G5; their `errorCode` appears in the message.
- Not alerted: plan-role use and IAM user sign-in failures.
- Exact JSON patterns live in the `bootstrap` code; the table above is the reviewed specification.

#### Routing
- Hub: the Seoul default event bus. Global service events are logged mostly in us-east-1, "but some global service
  events are logged as occurring in other Regions, such as US East (Ohio) Region or US West (Oregon) Region" [CT5];
  Amazon Q Developer events, for example, show `awsRegion` `us-east-2` [QD1].
- One forwarding rule, `bootstrap-forward`, in each of us-east-1, us-east-2, and us-west-2. Its pattern is the union
  of the G1, G3, G4, and G5 patterns, and its target is the Seoul default event bus through the IAM role
  `arn:aws:iam::<ACCOUNT_ID>:role/bootstrap/event-forwarder` (`events:PutEvents` on that bus only; trusted by
  `events.amazonaws.com`). The Seoul rules then match the forwarded events.
- Every bootstrap rule, forwarding and Seoul, uses the state `ENABLED_WITH_ALL_CLOUDTRAIL_MANAGEMENT_EVENTS`.
  "A rule in the default `ENABLED` state does not match read-only management events", and forwarding read-only events
  needs this state on both rules [EB3]. Root `aws login` sign-in events are read-only [IT1].
- Targets: the Seoul rules publish to the ADR 0006 topic, named `bootstrap-alerts`.

#### Topic policy (amends ADR 0006)
The topic policy gains one statement:
- `Allow` `sns:Publish` to `events.amazonaws.com` on `bootstrap-alerts`, with `ArnLike` `aws:SourceArn` =
  `arn:aws:events:ap-northeast-2:<ACCOUNT_ID>:rule/bootstrap-*` and `StringEquals` `aws:SourceAccount` = `<ACCOUNT_ID>`.
- The EventBridge guide shows the statement without conditions [EB5]; adding `aws:SourceArn` and `aws:SourceAccount`
  narrows it to these rules (inference: EventBridge sends both keys to SNS; checked in the Step 4 render test).

#### Messages
- Amazon Q Developer custom notifications: `version` "1.0", `source` "custom", `content.textType` "client-markdown",
  `content.description` required (up to 8,000 characters), optional `title` (250) and `nextSteps` [QD2].
- Built by an EventBridge input transformer from an allowlist of scalar fields. Never map
  `responseElements.credentials`, `<aws.events.event>`, `<aws.events.event.json>`, whole objects, or free-text fields
  such as `errorMessage` (EventBridge does not escape extracted values).
- G2 fields: Time (UTC), Source IP, Region, Run (`roleSessionName`), Event ID. Next steps: open the run link; it is
  mine only if I approved it and its time matches (UTC = KST − 9 h). Otherwise run E9 now, follow ADR 0005
  "After each use", and later look up the Event ID. A broken link or a time mismatch is itself an E9 trigger; the
  session name is a clue, not evidence.
- G1, G3, G4, G5 fields: Event, Who (`userIdentity.type` + `arn`), Time (UTC), Region, Source IP, Result (`errorCode`
  and `responseElements.ConsoleLogin`), Event ID. Next step: match the event to a merged PR (E7) or to my own E6 task.
  Pipeline changes show Who = `.../assumed-role/pipeline-apply/<run ID>`.
- Root activity that is not mine: handled by a Step 4 runbook.
- Health check (added 2026-10-04): every approved apply produces a G2 message. No G2 message within 15 minutes of an
  approved apply means the alert path is broken: check E10 (`aws chatbot describe-slack-workspaces`) and the topic
  subscription.
- Workflow rule (amends ADR 0004): the apply and plan jobs set `role-session-name: ${{ github.run_id }}`.
- Cost: USD 0. AWS management events are ingested by the event bus for free; forwarding between Regions can add data
  transfer charges [EB6], which are negligible at these volumes (inference). Custom notifications have "no additional
  costs" [QD2].

### (c) IAM Access Analyzer
- One external access analyzer, `bootstrap-external-access`, in `ap-northeast-2`, zone of trust = this account,
  in the `bootstrap` module. External access analysis is free (ADR 0004 [A6]).
- Coverage: resources in `ap-northeast-2` and all IAM roles (an analyzer covers its own Region; role findings are
  generated in each enabled Region, ADR 0004 F2–F3).
- Alert: a Seoul EventBridge rule matches source `aws.access-analyzer`, detail-type `Access Analyzer Finding`,
  `detail.status` `ACTIVE`, and `detail.isDeleted` `false` [AA1]. Message fields: Resource, Resource type,
  `principal.AWS` or `principal.Federated`, Public, Error, Finding ID, Region. Events arrive "within about an hour" [AA1].
- No archive rules. The filter keys include `principal.Federated` but no key for the GitHub `sub` or `ref` conditions
  [AA2], so an archive rule for the two pipeline roles would also hide a widened trust on them.
- Expected at E4: the two pipeline roles trust the GitHub OIDC provider and produce active findings (inference).
- Creating the analyzer creates the service-linked role `AWSServiceRoleForAccessAnalyzer`. Its resources must be
  cleaned up before it can be deleted [AA3]; the pipeline cannot delete the analyzer (d), so it cannot remove the
  role either (inference).
- Changes to the analyzer or its archive rules are G4 events (b).

### (d) Protection of the logging and alert path (P4)
P4 (ADR 0004) gains seven Deny statements. The full policy stays in ADR 0004, so P4 has one source.

| Sid | Denies | Resource |
|---|---|---|
| `DenyLogBucketConfig` | everything except `s3:Get*`, `s3:List*` | `arn:aws:s3:::<LOG_BUCKET>` |
| `DenyLogObjects` | `s3:*` | `arn:aws:s3:::<LOG_BUCKET>/*` |
| `DenyLoggingAndAlertServices` | `cloudtrail:*`, `budgets:*`, `chatbot:*`, `access-analyzer:*` | `*` |
| `DenyAlertRuleChanges` | everything except `events:Describe*`, `events:List*` | `arn:aws:events:*:<ACCOUNT_ID>:rule/bootstrap-*` |
| `DenyDefaultBusUpdate` | `events:UpdateEventBus` | `arn:aws:events:*:<ACCOUNT_ID>:event-bus/default` |
| `DenyEventBusPermissionChanges` | `events:PutPermission`, `events:RemovePermission` | `*` |
| `DenyAlertTopicChanges` | everything except `sns:Get*`, `sns:List*` | `arn:aws:sns:*:<ACCOUNT_ID>:bootstrap-*` |

- Service-wide Deny for four services: the pipeline never manages them. `NotAction` with a Deny "explicitly denies
  the actions not listed", and `Resource` decides which services apply [IA1]; with `Resource: "*"` it would deny every
  other service. A resource-scoped Deny would miss actions without a resource type, such as
  `chatbot:DeleteSlackWorkspaceAuthorization` [SR1]. `service:*` has the same shape as `DenyAccountLevelChanges` and
  also covers actions AWS adds later. Consequence: roles the pipeline creates carry P4, so they cannot read these four
  services either.
- `events:PutPermission` and `events:RemovePermission` have no resource type [SR1], so only `Resource: "*"` matches
  them [IA2]. Same-account forwarding between Regions uses the rule's IAM role, not a bus policy [EB8].
- `events:UpdateEventBus`: the default event bus can use a customer managed key, and that key encrypts each rule's
  event pattern and targets [EB7]. A pipeline-owned key could make the bootstrap rules unusable (inference).
- SNS subscription actions (`Subscribe`, `Unsubscribe`, `SetSubscriptionAttributes`) use the topic resource type
  [SR1], so the topic Deny also protects the subscriptions.
- Log objects: the pipeline never needs the log files, and `s3:*` blocks reading, overwriting, and deleting them.
  CloudTrail omits `secretAccessKey` from STS responses [IT1], so the logged session token is not the reason.
- Access points (added 2026-10-08, Step 4 simulator finding): a request through an access point names the access point
  ARN (`arn:aws:s3:REGION:ACCOUNT:accesspoint/NAME/object/KEY`), which `DenyLogObjects` does not match, and P4 did not
  deny creating one. `DenyAccessPointCreation` denies `s3:CreateAccessPoint`, `s3:CreateAccessPointForObjectLambda`,
  and `s3:CreateMultiRegionAccessPoint` [SR1]; Phase 0 needs no access points. Deletes through an access point are
  still denied by the bucket policy: "both the access point and the underlying bucket ... must permit the request" [S3AP].
- The IAM user admin and root are out of scope, as in ADR 0003; G3 and G4 alert on their changes.
- Size: P4 grows from 2,827 to about 3,786 characters (about 4,210 with ADR 0004 (f)) (example values, whitespace removed); the limit is 6,144 and
  "IAM doesn't count white space" [IQ1].
- Step 4: the IAM policy simulator shows that each statement blocks its target and that normal `main` actions (for
  example creating EC2 and S3 resources) stay allowed; creating an S3 access point is denied, so the log bucket cannot be reached through one.

### (e) Region of the apply-role assumption (P3)
- Calls to a Regional STS endpoint are logged in that Region, and calls to the global endpoint in us-east-1; STS is
  active by default in 17 Regions [ST1]. Without a Region condition, a changed workflow could assume `pipeline-apply`
  through a Region without a rule, and G2 would not fire.
- P3 adds `"aws:RequestedRegion": "ap-northeast-2"`. The key "is always included in the request context" [CK1], and
  requests to the global endpoint carry `us-east-1` for it [ST1], so the global endpoint is refused as well.
- Normal applies: `configure-aws-credentials` uses the AWS SDK for JavaScript v3 [GA1], whose default is the Regional
  STS endpoint for the configured Region [SD1] (inference: Seoul when `aws-region` is `ap-northeast-2`).
- Unverified: that trust-policy evaluation uses this key. A failure is fail-closed and shows on the first Step 4 apply;
  the fallback is forwarding rules in all 17 default Regions.
- Not adopted: deactivating STS in unused Regions. It is a console procedure [ST2], us-east-1 cannot be deactivated
  [ST1], and P4 would also need a Deny on `iam:SetSTSRegionalEndpointStatus` [SR1].

### (f) GitHub setting S15 removed (P1, P3)
- IAM now maps GitHub claims to condition keys, including `token.actions.githubusercontent.com:ref`, which "identifies
  the git ref (branch or tag) that triggered the workflow run" [OK1]. The first version of ADR 0004 said that only
  standard OIDC claims were mapped and that `ref` was not among them; that was outdated, and ADR 0004 now records the
  correction.
- `sub` is still required: for GitHub Actions the required claim is `token.actions.githubusercontent.com:sub` [OK2].
- P1: default `sub` `repo:Sweettreee@<OWNER_ID>/Odyssey-Cloud@<REPO_ID>:pull_request` (`StringEquals`) and
  `ref` like `refs/pull/*/merge` (`StringLike`).
- P3: default `sub` `repo:Sweettreee@<OWNER_ID>/Odyssey-Cloud@<REPO_ID>:environment:production` and
  `ref` = `refs/heads/main`. GitHub documents this `sub` form for environments [GH1]; the `pull_request` form with
  IDs is an inference.
- P1 keeps a `ref` check because GitHub does not say whether `pull_request_target` runs get the `pull_request`
  subject [GH1]; without it, P1 could become weaker than before (inference).
- S15 leaves E8, together with its ordering step and the write-scoped `gh` login it needed.
- Fallback: if the `ref` key does not match in Step 4, restore S15 and the previous `sub` values.

## 6-Layer check (chosen options)

| Layer | Notes |
|---|---|
| Traffic | Nothing inbound. CloudTrail writes to S3 and EventBridge; EventBridge publishes to SNS; Amazon Q Developer posts to Slack. GitHub runners call only the Seoul STS endpoint (e). |
| Compute | None: no server and no function. |
| Data | Log bucket: versioning, public access blocked, SSE-S3, integrity digests, no expiry. The pipeline cannot read, overwrite, or delete the log files (d); nobody deletes them without first changing the bucket policy (a). State-bucket reads and writes are logged as data events (a). Alert messages carry allowlisted scalar fields only, never credentials. |
| Security | The pipeline cannot turn off or change the trail, the log bucket, the rules, the default bus, the topic, the budget, the Slack channel configuration, or the analyzer (d). Every successful apply-role assumption alerts (G2) and can happen only in Seoul (e). Root activity, IAM changes, logging-path changes, and budget changes alert (G1, G3–G5). External access is detected for Seoul resources and all IAM roles (c). The IAM user admin and root are not blocked; G1, G3, and G4 detect their changes. |
| Cost | About USD 0 plus log storage and about USD 0.001/month for state-bucket data events (inference): the first copy of management events is free [CT1]; management events are ingested by EventBridge for free and forwarding adds small data transfer [EB6]; external access analysis is free (ADR 0004 [A6]); custom notifications are free [QD2]; no KMS key. Step 4 measures the storage cost. |
| Observability | One account-wide record in S3 and alerts in Slack. CloudTrail delivers service events to EventBridge "on a best effort basis" [EB9]; Access Analyzer events arrive within about an hour [AA1]. |

## Consequences
- Easier: the logging and alert path is outside the pipeline's reach; all alerts use one delivery path; the cost is about zero.
- Harder:
  - Every IAM change by the pipeline raises a G3 alert, which I match to a merged PR.
  - Changes to P4 are E7 applies.
  - Roles the pipeline creates cannot read CloudTrail, Budgets, Amazon Q Developer, or Access Analyzer.
  - The `bootstrap` module grows: a trail, a bucket, nine rules (six in Seoul, three forwarding rules), one role, and an analyzer.
- Known limits:
  - Alerts come after the event and can lag. E9 shortens a takeover; it does not prevent the first damage (ADR 0005).
  - The IAM user admin and root can still change all of it; detection only.
  - Events in Regions other than the four with rules are logged but not alerted; the pipeline cannot act there
    (ADR 0004 (f)). This includes root API calls there;
    root sign-ins are alerted (inference: they are logged in us-east-1, us-east-2, or us-west-2).
  - Data events cover the state bucket only. Log-bucket object deletes are denied by the bucket policy; removing that
    statement is a G4 event. Admin and root can still remove it.
  - E1–E3 happen before the trail exists.
  - Several inferences wait for Step 4: the `aws:RequestedRegion` and `ref` keys in trust policies, the topic policy
    conditions, the `readOnly` field in forwarded events, and message rendering. Each has a fallback or a test below.

## Revisit when
- A pipeline-created role must read CloudTrail, Budgets, Amazon Q Developer, or Access Analyzer (narrow
  `DenyLoggingAndAlertServices`; expected for Phase 4–5 agent tools).
- File-access logging is needed (S3 data events, expected in Phase 2).
- A workload runs outside `ap-northeast-2` (analyzer and alert rules per Region).
- The Paid-plan transition happens (ADR 0005): organization trail, RCPs, and delegated administration.
- A Step 4 result contradicts an inference in (b), (e), or (f).
- G3 alerts become too frequent to review.
- AWS changes the Regions where global service events are logged.

## Hand-offs

| To | Item |
|---|---|
| Step 4 | Measure log storage and request cost. IAM policy simulator: each new P4 statement blocks its target, normal `main` actions stay allowed, and the log bucket is denied through an S3 access point. First apply: P3 works with `aws:RequestedRegion` and `ref`; one assumption through another Region is denied; verify the `sub` and `ref` values from a real token, printing only those two claims. Render test for every group: empty variables, separators, the run link with `roleSessionName`, line breaks, the topic policy conditions, and the `readOnly` field. Write the runbook for root activity that is not mine, with the G2 health check. Deleting a log object is denied; state reads and writes appear as data events. Expect active findings for the two pipeline roles at E4. |

## Sources
- [CT1] CloudTrail, Working with CloudTrail trails: https://docs.aws.amazon.com/awscloudtrail/latest/userguide/cloudtrail-trails.html
- [CT2] AWS CloudTrail pricing (checked 2026-10-02): https://aws.amazon.com/cloudtrail/pricing/
- [CT3] CloudTrail, Amazon S3 bucket policy for CloudTrail: https://docs.aws.amazon.com/awscloudtrail/latest/userguide/create-s3-bucket-policy-for-cloudtrail.html
- [CT4] CloudTrail, Validating CloudTrail log file integrity: https://docs.aws.amazon.com/awscloudtrail/latest/userguide/cloudtrail-log-file-validation-intro.html
- [CT5] CloudTrail, CloudTrail concepts (Global service events): https://docs.aws.amazon.com/awscloudtrail/latest/userguide/cloudtrail-concepts.html
- [S3E] S3, Configuring default encryption: https://docs.aws.amazon.com/AmazonS3/latest/userguide/default-bucket-encryption.html
- [IT1] IAM, Logging IAM and AWS STS API calls with AWS CloudTrail: https://docs.aws.amazon.com/IAM/latest/UserGuide/cloudtrail-integration.html
- [AA1] IAM, Monitoring IAM Access Analyzer with Amazon EventBridge: https://docs.aws.amazon.com/IAM/latest/UserGuide/access-analyzer-eventbridge.html
- [AA2] IAM, IAM Access Analyzer filter keys: https://docs.aws.amazon.com/IAM/latest/UserGuide/access-analyzer-reference-filter-keys.html
- [AA3] IAM, Using service-linked roles for IAM Access Analyzer: https://docs.aws.amazon.com/IAM/latest/UserGuide/access-analyzer-using-service-linked-roles.html
- [EB3] EventBridge, AWS service events delivered via AWS CloudTrail: https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-service-event-cloudtrail.html
- [EB4] EventBridge API, PutPermission (`Principal`): https://docs.aws.amazon.com/eventbridge/latest/APIReference/API_PutPermission.html
- [EB5] EventBridge, Using resource-based policies (Amazon SNS permissions): https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-use-resource-based.html
- [EB6] Amazon EventBridge pricing (checked 2026-10-02): https://aws.amazon.com/eventbridge/pricing/
- [EB7] EventBridge, Encrypting event buses with AWS KMS keys: https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-encryption-event-bus-cmkey.html
- [EB8] EventBridge, Permissions for event buses: https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-event-bus-perms.html
- [EB9] EventBridge Events Reference, AWS Budgets events: https://docs.aws.amazon.com/eventbridge/latest/ref/events-ref-budgets.html
- [QD1] Amazon Q Developer in chat applications, Logging API calls with AWS CloudTrail: https://docs.aws.amazon.com/chatbot/latest/adminguide/logging-using-cloudtrail.html
- [QD2] Amazon Q Developer in chat applications, Custom notifications: https://docs.aws.amazon.com/chatbot/latest/adminguide/custom-notifs.html
- [IA1] IAM, NotAction: https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_elements_notaction.html
- [IA2] IAM, Resource: https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_elements_resource.html
- [SR1] AWS service reference (events, sns, chatbot, iam; checked 2026-10-01): https://servicereference.us-east-1.amazonaws.com/v1/events/events.json
- [IQ1] IAM and AWS STS quotas (checked 2026-10-01): https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_iam-quotas.html
- [S3AP] S3, Configuring IAM policies for using access points (checked 2026-10-08): https://docs.aws.amazon.com/AmazonS3/latest/userguide/access-points-policies.html
- [ST1] IAM, AWS STS Regions and endpoints: https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_temp_region-endpoints.html
- [ST2] IAM, Manage AWS STS in an AWS Region: https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_temp_enable-regions.html
- [CK1] IAM, AWS global condition context keys (`aws:RequestedRegion`): https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_condition-keys.html#condition-keys-requestedregion
- [GA1] aws-actions/configure-aws-credentials (README and package.json): https://github.com/aws-actions/configure-aws-credentials
- [SD1] AWS SDKs and Tools Reference, AWS STS Regional endpoints: https://docs.aws.amazon.com/sdkref/latest/guide/feature-sts-regionalized-endpoints.html
- [OK1] IAM, Available keys for AWS OIDC federation (GitHub tab): https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_iam-condition-keys.html#condition-keys-wif
- [OK2] IAM, Identity-provider controls for shared OIDC providers: https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_providers_oidc_secure-by-default.html
- [GH1] GitHub, OpenID Connect reference: https://docs.github.com/en/actions/reference/security/oidc
- [CT6] CloudTrail, Logging data events (checked 2026-10-04): https://docs.aws.amazon.com/awscloudtrail/latest/userguide/logging-data-events-with-cloudtrail.html
