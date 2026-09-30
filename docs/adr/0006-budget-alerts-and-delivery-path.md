# ADR 0006: AWS budget alerts and alert delivery path

- **Status:** Accepted
- **Date:** 2026-09-30
- **Phase:** 0
- **Amends:** ADR 0003 exception table (adds exception E10)

## Context
Phase 0 needs AWS budget alerts at 50%, 75%, 90%, and 100% of the AWS target and at the ceiling,
and a test alert for every threshold must reach Slack (`docs/vision.md` §6, Phase 0). The AWS budget is
USD 20/month with a USD 25 ceiling; credit-covered usage counts as cost; the AI API and subscriptions are
tracked manually (`docs/vision.md` §5.1). ADR 0004 hands D6 the delivery path for the apply-role assumption
alert and other security alerts, and requires budget alerts to exist no later than E4 (EP-22).
The account runs on the Free plan (ADR 0005). I asked to evaluate an AWS Deadline Cloud budget
notification sample as the method [DL1][DS1].

Facts this ADR relies on (checked 2026-09-29; [QC1] and [QL1] on 2026-09-30):
- AWS Budgets tracks AWS costs and usage and notifies an SNS topic, email, or both. Its information is updated
  up to three times a day, typically 8–12 hours apart; costs can pass a threshold before the notification arrives [B1].
- Every official example uses USD [B2]. Cost budgets include credits and taxes by default
  (`IncludeCredit` and `IncludeTax` default to `true`) [B3]. Korean VAT is charged to individual customers [TX1].
- Each alert goes to up to 10 email addresses and one SNS topic. An actual-spend alert is sent once per budget
  period, when the threshold is first reached. Forecasts need about five weeks of usage data [B4].
  A budget has up to five notifications [CF1].
- The SNS topic must be in the budget's account. Budgets needs `SNS:Publish` in the topic policy, scoped with
  `aws:SourceAccount` and `aws:SourceArn`. An encrypted topic needs a KMS key policy that allows Budgets;
  otherwise encryption must be off [BS1].
- Budget alerts reach Slack through Amazon Q Developer in chat applications (formerly AWS Chatbot) subscribed
  to that topic [BQ1]. The Slack workspace ID exists only after an authorization flow in the Amazon Q Developer
  console; without a guardrail policy, `AdministratorAccess` is the default guardrail [CF2]. A channel
  configuration can subscribe to topics in several Regions [QS1]. Custom notifications use the same SNS path [CN1].
- The EventBridge reference lists only API-call events for AWS Budgets, delivered through CloudTrail [EB1].
  CloudTrail events, including console sign-ins, reach EventBridge only while a trail with logging is on [EB2].
- Deadline Cloud budgets aggregate usage and cost per render farm [DL2]. The sample routes the Deadline Cloud
  "Budget Threshold Reached" event through an EventBridge rule to a KMS-encrypted SNS topic, then to email and
  a Slack channel; its channel role has no permissions and it sets no guardrail [DS1].
- On the Free plan, "No charges incur during usage"; the plan ends after six months or when the credits are used
  up, and the account then closes automatically [F2].

## Options considered

### (a) What the budget counts

| Option | Pros | Cons | Monthly cost impact |
|---|---|---|---|
| A. Credits subtracted (default) | Measures only what I pay. | Silent for the whole Free plan, because credits cover every charge [F2]; credit burn is never alerted. | 0 |
| B. Credit-covered usage counted as cost | Alerts on real usage while credits last; a design above USD 20 shows up before the credits run out. | After the Paid-plan transition, alerts can fire before any real payment. | 0 |

### (b) Delivery path to Slack

| Option | Pros | Cons | Monthly cost impact |
|---|---|---|---|
| A. SNS → Amazon Q Developer → Slack | AWS-managed: no code, no stored secret. Documented path for Budgets [BQ1]; D7 reuses it with custom notifications [CN1]. | Slack authorization is console-only (E10). Links the Slack workspace to the account, so the guardrail matters [CF2]. Fixed budget message format. | 0 [QP1][SNS1] |
| B. SNS → Lambda → Slack incoming webhook | Full control of the message format. | Code and a runtime to maintain; the webhook URL is a secret to store; more moving parts; Slack app setup is manual too. | USD 0.40/month for the secret [S2]; Lambda not priced |
| C. Budget email to a Slack channel address | No AWS delivery parts. | Needs a paid Slack plan [SL2]; plain email text; cannot carry D7 events. | Slack subscription (outside the budget) |

### (c) SNS topic encryption

| Option | Pros | Cons | Monthly cost impact |
|---|---|---|---|
| A. No server-side encryption | Budgets publishes without a key policy [BS1]. | Messages are not encrypted with a KMS key. | 0 |
| B. Customer managed KMS key (as in the sample) | Encryption with a key I control. | Key policy must allow Budgets, and EventBridge in D7. | USD 1/month per key [K1] |

Chosen: (a) B, (b) A, (c) A.

## 6-Layer check (chosen option)

| Layer | Notes |
|---|---|
| Traffic | No inbound traffic. Budgets (and EventBridge in D7) publish to SNS; Amazon Q Developer posts to Slack. |
| Compute | None: no server and no function. |
| Data | Alert messages only: amounts and thresholds, and event summaries in D7. No secrets (inference). No server-side encryption on the topic. |
| Security | The topic policy lets Budgets publish only for this account [BS1]. The channel role and the guardrail are both empty and explicit [CF2], under the IAM path `/bootstrap/`. D7's Denies keep the pipeline from removing the path (EP-22). E10 links the Slack workspace to the account. |
| Cost | USD 0/month. Budget monitoring and notifications are free [BP1]; Amazon Q Developer has no additional charge [QP1]; SNS includes 1 million requests and 100,000 HTTP/S deliveries per month at no charge [SNS1]; no KMS key (USD 1/month avoided [K1]). |
| Observability | Alerts lag by hours and do not stop spending [B1]. Budget changes are visible through CloudTrail and EventBridge [EB1] (D7). |

## Decision

### Budget
- One AWS cost budget: monthly, recurring, USD 20.
- Credit-covered usage counts as cost (`IncludeCredit = false`) [B3]. Taxes stay included (default) [B3][TX1].
  Other cost types keep their defaults.
- Actual-spend notifications at 50%, 75%, 90%, and 100% (USD 10, 15, 18, 20) and at 125% (USD 25, the ceiling):
  the five-notification maximum [CF1]. No forecast notifications: not requested, and they need about five weeks of data [B4].
- Every notification goes to the SNS topic and to my email address [B4].
- It lives in the `bootstrap` module, so it exists no later than E4 (ADR 0004 EP-22).

### Delivery path
- One standard SNS topic in `ap-northeast-2`, without server-side encryption, in the `bootstrap` module.
- Topic policy: `SNS:Publish` for `budgets.amazonaws.com` with `aws:SourceAccount` and `aws:SourceArn` [BS1].
  D7 adds the statement for EventBridge.
- One Amazon Q Developer Slack channel configuration (Terraform `aws_chatbot_slack_channel_configuration`),
  subscribed to the topic, posting to one private Slack channel.
- Channel role: trusted by Amazon Q Developer only, with no permissions, as in the sample [DS1].
  Guardrail: set explicitly to a policy with no permissions, instead of the default `AdministratorAccess` [CF2].
  The role and the guardrail policy use the IAM path `/bootstrap/`, so P4 `DenyBootstrapIamChanges` covers them (ADR 0004).

### The owner's reference sample (Deadline Cloud)
- Adopted: SNS → Amazon Q Developer → Slack, plus email.
- Not adopted for budgets: the EventBridge rule. Deadline Cloud budgets cover render farms only [DL2], and
  AWS Budgets emits only API-call events to EventBridge [EB1].
- Handed to D7: the EventBridge rule → SNS pattern, for security alerts [EB2].
- Changed from the sample: Terraform instead of CloudFormation (ADR 0002); no KMS key; an explicit guardrail;
  a topic policy for Budgets.

### Slack plan
- Free. The features the vision needs are on the Free plan: apps (up to 10) [SL1]; the Events API and
  interactivity through Socket Mode, with no plan requirement stated [SK1]; workspace-wide 2FA [SL3].
- Records stay in AWS and the Web UI, not in Slack: Free shows 90 days of history and deletes content
  older than one year [SL1].
- Upgrade to Pro, the cheapest paid plan [SL7], only when Slack sign-in logs [SL4] or guest accounts [SL5]
  become necessary; expected in Phase 5–6, when Slack becomes the command path (inference).
  Subscriptions are outside the budget (`docs/vision.md` §5.1).

### Why
- Counting credit-covered usage keeps the alerts working during the Free plan, which serves the goal of saving
  and optimizing the budget.
- (b) A has the fewest moving parts: no code, no secret, and one path for budget and security alerts.
- The alerts carry no secrets (inference), so a KMS key is not worth 5% of the AWS target.

## Exception E10 (amends ADR 0003)

| # | Exception | Kind | Who / how | Read-only check |
|---|---|---|---|---|
| E10 | Connect the Slack workspace to Amazon Q Developer | One-time; repeated only if the connection is lost | Me. In Slack: add the Amazon Q Developer app, create the private alert channel, and invite `@Amazon Q` [QS1]. In AWS: the IAM user admin runs the Slack authorization flow in the Amazon Q Developer console [CF2] | `aws chatbot describe-slack-workspaces` lists the workspace with `State` `ENABLED` [QC1] |

- Order: before E4, because the channel configuration in `bootstrap` needs the workspace ID [CF2].
- ADR 0003 control rules apply to E10. Resources created by E10 are excluded from exit criterion 1, like E1–E6.

## Consequences
- Easier: no code or secret to maintain; one delivery path for budget and security alerts; USD 0 per month.
- Harder: one more manual exception (E10); the Slack workspace is linked to the account, so the channel role
  and the guardrail must stay empty.
- Known limits:
  - Alerts lag by hours and do not stop spending [B1].
  - Phase 0 usage should stay far below USD 10, so no real alert is expected in Phase 0 (inference);
    exit criterion 3 is tested with a temporary budget (Step 4).
  - After the Paid-plan transition, alerts can fire before any real payment while credits remain.
  - Only AWS costs are seen [B1]. An AI API billed through AWS (for example, Amazon Bedrock) would appear
    in this budget (inference); decided in Phase 5.
  - A Route 53 domain's yearly fee lands in one month and can trigger several alerts at once (inference).
  - Alert history is not kept in Slack [SL1].

## Hand-offs

| To | Item |
|---|---|
| D7 | Add an EventBridge statement to the topic policy. Deny the pipeline any change to the budget, the SNS topic (policy and subscriptions), and the channel configuration (EP-22, extended). Alert on Budgets API changes such as `DeleteBudget` and `UpdateBudget` [EB1]. Security alerts use this topic as custom notifications [CN1] and need a trail with logging [EB2]. A topic in another Region, if global-service events need one, joins the same channel configuration [QS1]. |
| Step 4 | Run E10 before E4. Check whether E10 creates the `AWSServiceRoleForAWSChatbot` service-linked role [QL1]; if so, record it under E10. Verify that budget and custom notifications render with an empty channel role and guardrail. Confirm how the current Budgets API and AWS provider express `IncludeCredit`. Decide whether the Slack workspace and channel IDs go in code or in an ignored `*.tfvars` file (the repository is public). Exit criterion 3: a temporary budget (credits counted, USD 0.01, the same five notifications and topic) added and removed through E7; every alert must arrive in Slack and by email (inference: Phase 0 usage passes USD 0.01 in a month). Confirm Amazon Q Developer is available on the Free plan (existing check after E1). |

## Revisit when
- The Paid-plan transition happens (ADR 0005): recheck the budget once the account joins an organization.
- The AI API is billed through AWS, or a domain is bought through Route 53.
- Slack sign-in logs or guest accounts become necessary (Pro plan).
- More than five alert levels are needed on one budget [CF1].
- AWS Budgets starts sending threshold events to EventBridge.

## Sources
- [B1] Managing your costs with AWS Budgets: https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-managing-costs.html
- [B2] Budgets API, Spend: https://docs.aws.amazon.com/aws-cost-management/latest/APIReference/API_budgets_Spend.html
- [B3] Budgets API, CostTypes: https://docs.aws.amazon.com/aws-cost-management/latest/APIReference/API_budgets_CostTypes.html
- [B4] Best practices for AWS Budgets: https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-best-practices.html
- [CF1] AWS::Budgets::Budget: https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-budgets-budget.html
- [BS1] Creating an Amazon SNS topic for budget notifications: https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-sns-policy.html
- [BQ1] Receiving budget alerts in chat applications: https://docs.aws.amazon.com/cost-management/latest/userguide/sns-alert-chime.html
- [BP1] AWS Budgets pricing (checked 2026-09-29): https://aws.amazon.com/aws-cost-management/aws-budgets/pricing/
- [CF2] AWS::Chatbot::SlackChannelConfiguration: https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-resource-chatbot-slackchannelconfiguration.html
- [QS1] Amazon Q Developer in chat applications, Get started with Slack: https://docs.aws.amazon.com/chatbot/latest/adminguide/slack-setup.html
- [CN1] Custom notifications: https://docs.aws.amazon.com/chatbot/latest/adminguide/custom-notifs.html
- [QC1] AWS CLI, chatbot describe-slack-workspaces: https://docs.aws.amazon.com/cli/latest/reference/chatbot/describe-slack-workspaces.html
- [QL1] Service-linked roles for Amazon Q Developer in chat applications: https://docs.aws.amazon.com/chatbot/latest/adminguide/using-service-linked-roles.html
- [QP1] AWS Chatbot pricing (checked 2026-09-29): https://aws.amazon.com/chatbot/pricing/
- [SNS1] Amazon SNS FAQs, pricing (checked 2026-09-29): https://aws.amazon.com/sns/faqs/
- [K1] AWS KMS pricing (checked 2026-09-29): https://aws.amazon.com/kms/pricing/
- [S2] AWS Secrets Manager pricing (checked 2026-09-28, ADR 0005): https://aws.amazon.com/secrets-manager/pricing/
- [EB1] AWS Budgets events (EventBridge): https://docs.aws.amazon.com/eventbridge/latest/ref/events-ref-budgets.html
- [EB2] AWS service events delivered via AWS CloudTrail: https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-service-event-cloudtrail.html
- [DL1] Managing Deadline Cloud events using Amazon EventBridge: https://docs.aws.amazon.com/deadline-cloud/latest/developerguide/eventbridge-integration.html
- [DL2] Deadline Cloud, Monitor a budget with EventBridge events: https://docs.aws.amazon.com/deadline-cloud/latest/userguide/budget-threshold-events.html
- [DS1] aws-deadline/deadline-cloud-samples, budget_events_notification: https://github.com/aws-deadline/deadline-cloud-samples/tree/mainline/cloudformation/notification_templates/budget_events_notification
- [F2] Choosing a plan (Billing User Guide): https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/free-tier-plans.html
- [TX1] AWS Tax Help, South Korea: https://aws.amazon.com/tax-help/south-korea1/
- [SL1] Slack, Usage limits for free workspaces: https://slack.com/help/articles/115002422943-Usage-limits-for-free-workspaces
- [SL2] Slack, Send emails to Slack: https://slack.com/help/articles/206819278-Send-emails-to-Slack
- [SL3] Slack, Require two-factor authentication: https://slack.com/help/articles/212221668-Require-two-factor-authentication-for-your-workspace
- [SL4] Slack, View access logs: https://slack.com/help/articles/360002084807-View-Access-Logs-for-your-workspace
- [SL5] Slack, Multi-Channel and Single-Channel Guests: https://slack.com/help/articles/202518103-Multi-Channel-and-Single-Channel-Guests
- [SL7] Slack pricing (checked 2026-09-29): https://slack.com/pricing
- [SK1] Slack, Using Socket Mode: https://docs.slack.dev/apis/events-api/using-socket-mode
