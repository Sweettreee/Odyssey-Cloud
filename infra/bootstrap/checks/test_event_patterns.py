"""Check the bootstrap EventBridge patterns against hand-built CloudTrail-shaped events.

Read-only: calls `aws events test-event-pattern` only; creates no AWS resources.
Run from anywhere after `aws login --profile odyssey-admin`:
    python3 infra/bootstrap/checks/test_event_patterns.py
Re-run when events.tf changes (E7). Delete this file when it is no longer useful.
Real events are still checked in Step 4 M6 (render tests).
"""
import json, os, subprocess, uuid
BOOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ACCT = "186972156090"
APPLY = f"arn:aws:iam::{ACCT}:role/bootstrap/pipeline-apply"
PLAN = f"arn:aws:iam::{ACCT}:role/bootstrap/pipeline-plan"
LOG = f"bootstrap-cloudtrail-{ACCT}"

def tf(expr):
    out = subprocess.run(["terraform", "console"], input=expr, capture_output=True, text=True, cwd=BOOT).stdout.strip()
    return json.loads(json.loads(out))

pats = {
  "G1": tf('local.seoul_rules["bootstrap-g1-root"]'),
  "G2": tf('jsonencode(merge(local.g2, {detail = merge(local.g2.detail, {requestParameters = {roleArn = ["%s"]}})}))' % APPLY),
  "G3": tf('local.seoul_rules["bootstrap-g3-iam"]'),
  "G4": tf('local.seoul_rules["bootstrap-g4-logging-path"]'),
  "G5": tf('local.seoul_rules["bootstrap-g5-budget"]'),
  "AA": tf('local.seoul_rules["bootstrap-access-analyzer"]'),
  "FWD": tf('local.forward_pattern'),
}

def ev(source, dtype, detail, region="ap-northeast-2"):
    return {"version": "0", "id": str(uuid.uuid4()), "detail-type": dtype, "source": source, "account": ACCT,
            "time": "2026-10-07T00:00:00Z", "region": region, "resources": [], "detail": detail}
API = "AWS API Call via CloudTrail"
def ct(src, name, ro, params=None, ident=None, **extra):
    d = {"eventSource": src.replace("aws.", "") + ".amazonaws.com", "eventName": name, "readOnly": ro,
         "userIdentity": ident or {"type": "IAMUser", "arn": f"arn:aws:iam::{ACCT}:user/odyssey-admin"},
         "requestParameters": params or {}, "eventID": str(uuid.uuid4())}
    d.update(extra)
    return ev(src, API, d)

root_login = ev("aws.signin", "AWS Console Sign In via CloudTrail",
                {"eventName": "ConsoleLogin", "userIdentity": {"type": "Root", "arn": f"arn:aws:iam::{ACCT}:root"}, "readOnly": False})
user_login = ev("aws.signin", "AWS Console Sign In via CloudTrail",
                {"eventName": "ConsoleLogin", "userIdentity": {"type": "IAMUser"}, "readOnly": False})
g4_events = [
  ("cloudtrail StopLogging",            ct("aws.cloudtrail", "StopLogging", False, {"name": "bootstrap-trail"})),
  ("events PutRule bootstrap-g1-root",  ct("aws.events", "PutRule", False, {"name": "bootstrap-g1-root"})),
  ("events RemoveTargets bootstrap-g3", ct("aws.events", "RemoveTargets", False, {"rule": "bootstrap-g3-iam", "ids": ["x"]})),
  ("events UpdateEventBus default",     ct("aws.events", "UpdateEventBus", False, {"name": "default"})),
  ("sns SetTopicAttributes alerts",     ct("aws.sns", "SetTopicAttributes", False, {"topicArn": f"arn:aws:sns:ap-northeast-2:{ACCT}:bootstrap-alerts"})),
  ("sns Unsubscribe alerts sub",        ct("aws.sns", "Unsubscribe", False, {"subscriptionArn": f"arn:aws:sns:ap-northeast-2:{ACCT}:bootstrap-alerts:1b2c"})),
  ("s3 PutBucketPolicy log bucket",     ct("aws.s3", "PutBucketPolicy", False, {"bucketName": LOG})),
  ("chatbot DeleteSlackChannelConfig",  ct("aws.chatbot", "DeleteSlackChannelConfiguration", False, {})),
]
cases = [
  ("G1", "root console sign-in", root_login, True),
  ("G1", "root API call (CreateUser)", ct("aws.iam", "CreateUser", False, ident={"type": "Root", "arn": f"arn:aws:iam::{ACCT}:root"}), True),
  ("G1", "IAM user sign-in", user_login, False),
  ("G2", "apply role assumed, success", ct("aws.sts", "AssumeRoleWithWebIdentity", True, {"roleArn": APPLY, "roleSessionName": "123"}, ident={"type": "WebIdentityUser"}), True),
  ("G2", "apply role assume denied", ct("aws.sts", "AssumeRoleWithWebIdentity", True, {"roleArn": APPLY}, ident={"type": "WebIdentityUser"}, errorCode="AccessDenied"), False),
  ("G2", "plan role assumed", ct("aws.sts", "AssumeRoleWithWebIdentity", True, {"roleArn": PLAN}, ident={"type": "WebIdentityUser"}), False),
  ("G3", "IAM write (CreateRole)", ct("aws.iam", "CreateRole", False, {"roleName": "x"}), True),
  ("G3", "IAM read (GetRole)", ct("aws.iam", "GetRole", True, {"roleName": "x"}), False),
] + [("G4", n, e, True) for n, e in g4_events] + [
  ("G4", "events PutRule other-rule", ct("aws.events", "PutRule", False, {"name": "other-rule"}), False),
  ("G4", "sns SetTopicAttributes other topic", ct("aws.sns", "SetTopicAttributes", False, {"topicArn": f"arn:aws:sns:ap-northeast-2:{ACCT}:app-topic"}), False),
  ("G4", "s3 PutBucketPolicy other bucket", ct("aws.s3", "PutBucketPolicy", False, {"bucketName": "some-app-bucket"}), False),
  ("G4", "cloudtrail read (DescribeTrails)", ct("aws.cloudtrail", "DescribeTrails", True), False),
  ("G5", "budget write (UpdateBudget)", ct("aws.budgets", "UpdateBudget", False), True),
  ("G5", "budget read (DescribeBudgets)", ct("aws.budgets", "DescribeBudgets", True), False),
  ("AA", "active finding", ev("aws.access-analyzer", "Access Analyzer Finding", {"status": "ACTIVE", "isDeleted": False, "resourceType": "AWS::IAM::Role"}), True),
  ("AA", "archived finding", ev("aws.access-analyzer", "Access Analyzer Finding", {"status": "ARCHIVED", "isDeleted": False}), False),
  ("FWD", "root sign-in (us-east-1)", root_login, True),
  ("FWD", "IAM write", ct("aws.iam", "CreateRole", False), True),
  ("FWD", "G4 sns part", g4_events[4][1], True),
  ("FWD", "budget write", ct("aws.budgets", "UpdateBudget", False), True),
  ("FWD", "apply role assumed (G2, not forwarded)", ct("aws.sts", "AssumeRoleWithWebIdentity", True, {"roleArn": APPLY}), False),
  ("FWD", "IAM read", ct("aws.iam", "GetRole", True), False),
]
fails = 0
for rule, name, event, expect in cases:
    r = subprocess.run(["aws", "events", "test-event-pattern", "--profile", "odyssey-admin", "--region", "ap-northeast-2",
                        "--event-pattern", json.dumps(pats[rule]), "--event", json.dumps(event), "--query", "Result", "--output", "text"],
                       capture_output=True, text=True)
    got = r.stdout.strip()
    if r.returncode != 0:
        print(f"ERROR {rule:3} {name}: {r.stderr.strip()[:200]}"); fails += 1; continue
    ok = (got == "True") == expect
    fails += 0 if ok else 1
    print(f"{'PASS' if ok else 'FAIL'} {rule:3} expect={'match' if expect else 'no-match':8} got={got:5} {name}")
print(f"\n{len(cases)} cases, {fails} failed")
raise SystemExit(1 if fails else 0)
