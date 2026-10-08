# Runbook: root activity that is not mine

Scope: G1 alerts and the G2 health check (ADR 0007 (b)). Commands are read-only unless marked, and run after
`aws login --profile odyssey-admin`.

## 1. Trigger
- Slack: ":rotating_light: G1 Root activity" (any root API call, console sign-in, or `aws login`; ADR 0007 G1).
- Root sign-ins are recorded in us-east-1, us-east-2, or us-west-2 and forwarded to Seoul (ADR 0007 (b)).

## 2. Was it me? (two minutes)
It is mine only if all of these hold:
- I was doing a task that needs root at that time (root is sealed, ADR 0005), for example E6 or a G1 test.
- Time (UTC) matches my clock: KST = UTC + 9 h.
- Source IP is my network.
- Event and Result match what I did, for example `ConsoleLogin` with Result `Success`.

If all hold: no action. If any fails, or I am unsure: go to section 3 now. A failed sign-in that is not mine also
goes to section 3.

## 3. Not mine, or unsure
Recovery channels first: "Make sure you have access to your root user email inbox" [R1].
1. Root email (my personal Gmail): change its password, check its 2-step verification and recovery options, and
   sign out its other sessions.
2. Sign in as root with the passkey (console change, recorded in the incident PR): change the root password,
   delete every MFA device that is not my passkey, and confirm that root has no access keys.
3. As the admin, list what root did since the alert time (all four Regions where root events land):
   ```
   for r in us-east-1 us-east-2 us-west-2 ap-northeast-2; do
     aws cloudtrail lookup-events --region "$r" --start-time "<UTC start>" --profile odyssey-admin --output json |
     python3 -c 'import json,sys; [print(d["eventTime"], d["awsRegion"], d["eventSource"], d["eventName"], d.get("errorCode")) for e in json.load(sys.stdin)["Events"] for d in [json.loads(e["CloudTrailEvent"])] if d["userIdentity"]["type"]=="Root"]'
   done
   ```
   Also read the G3, G4, and G5 alerts in Slack for the same window.
4. Undo what root changed: through code if the resource is in code (E7 for `bootstrap`, the pipeline for `main`);
   otherwise in the console, recorded in the incident PR.
5. If the pipeline may be involved (a G2 alert I did not approve, or changes by `pipeline-apply`): run E9 now
   (ADR 0005, both switches).
6. Contact AWS for assistance [R1].
7. Record the incident in a PR (time window, what root did, what was undone) and in the phase note.

## 4. G2 health check
Every approved apply produces a "G2 pipeline-apply was assumed" message. No G2 message within 15 minutes of an
approved apply means the alert path is broken (ADR 0007 (b)). Check:
```
aws chatbot describe-slack-workspaces --region us-east-2 --profile odyssey-admin
aws sns list-subscriptions-by-topic --region ap-northeast-2 --topic-arn arn:aws:sns:ap-northeast-2:186972156090:bootstrap-alerts --profile odyssey-admin
aws events describe-rule --region ap-northeast-2 --name bootstrap-g2-apply-assumed --query State --profile odyssey-admin
aws cloudtrail get-trail-status --region ap-northeast-2 --name bootstrap-trail --query IsLogging --profile odyssey-admin
```
Until the path works again, compare every `AssumeRoleWithWebIdentity` event for `pipeline-apply` in CloudTrail
with the runs I approved.

## 5. While E9 is in place
- Do not apply `bootstrap`. `pipeline-boundary` is `aws_iam_policy.pipeline_boundary`, so an apply would make the
  reviewed P4 the default version again and undo the second switch (inference); a plan shows it as a change.
- `emergency-deny-all` is added outside code. `pipeline-apply` uses no `inline_policy` block and no exclusive
  policy resource, so Terraform does not remove it (inference from [T1]).
- Restore both switches only after ADR 0005 "After each use", through the incident PR.

## Sources
- [R1] IAM, Root user best practices (checked 2026-10-08): https://docs.aws.amazon.com/IAM/latest/UserGuide/root-user-best-practices.html
- [T1] Terraform AWS provider, aws_iam_role (checked 2026-10-08): https://github.com/hashicorp/terraform-provider-aws/blob/main/website/docs/r/iam_role.html.markdown
