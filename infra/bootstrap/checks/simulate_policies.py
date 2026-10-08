"""Check the pipeline roles and the log bucket policy with the IAM policy simulator (ADR 0004, ADR 0007 (d)).

Read-only: calls `aws iam simulate-principal-policy` and `aws s3api get-bucket-policy` only;
the simulator "does not perform the API operations" it evaluates.
Run from anywhere after `aws login --profile odyssey-admin`:
    python3 infra/bootstrap/checks/simulate_policies.py
Re-run when a file in policies/ or the log bucket policy in trail.tf changes (E7, ADR 0003).
Simulator results can differ from live AWS; live checks are logged in the phase note.
"""
import json, subprocess

ACCT = "186972156090"
SEOUL = "ap-northeast-2"
APPLY = f"arn:aws:iam::{ACCT}:role/bootstrap/pipeline-apply"
PLAN = f"arn:aws:iam::{ACCT}:role/bootstrap/pipeline-plan"
ADMIN = f"arn:aws:iam::{ACCT}:user/odyssey-admin"
BOUNDARY = f"arn:aws:iam::{ACCT}:policy/bootstrap/pipeline-boundary"
STATE = f"arn:aws:s3:::odyssey-tfstate-{ACCT}"
LOG_BUCKET = f"bootstrap-cloudtrail-{ACCT}"
LOG = f"arn:aws:s3:::{LOG_BUCKET}"
LOG_OBJ = f"{LOG}/AWSLogs/{ACCT}/CloudTrail/{SEOUL}/2026/10/08/example.json.gz"
APP_ROLE = f"arn:aws:iam::{ACCT}:role/app-example"
DENY_ALL = json.dumps({"Version": "2012-10-17", "Statement": [{"Effect": "Deny", "Action": "*", "Resource": "*"}]})
A, X, I = "allowed", "explicitDeny", "implicitDeny"

def ec2(region):
    return f"arn:aws:ec2:{region}:{ACCT}:instance/*"

def aws(*args):
    r = subprocess.run(["aws", "--profile", "odyssey-admin", "--output", "json", *args], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip()[:200])
    return json.loads(r.stdout)

LOG_POLICY = aws("s3api", "get-bucket-policy", "--bucket", LOG_BUCKET)["Policy"]

def simulate(src, action, resource, region=SEOUL, boundary=None, resource_policy=False, deny_all=False):
    ctx = [{"ContextKeyName": "aws:RequestedRegion", "ContextKeyValues": [region], "ContextKeyType": "string"}]
    if boundary:
        ctx.append({"ContextKeyName": "iam:PermissionsBoundary", "ContextKeyValues": [boundary], "ContextKeyType": "string"})
    args = ["iam", "simulate-principal-policy", "--policy-source-arn", src, "--action-names", action,
            "--resource-arns", resource, "--context-entries", json.dumps(ctx)]
    if resource_policy:  # "Simulation of resource-based policies isn't supported for IAM roles."
        args += ["--resource-policy", LOG_POLICY]
    if deny_all:
        args += ["--permissions-boundary-policy-input-list", json.dumps([DENY_ALL])]  # JSON list: the CLI splits bare values on commas
    return aws(*args)["EvaluationResults"][0]["EvalDecision"]

cases = [
  # A. Normal main work: pipeline-apply in Seoul
  ("A", "create an EC2 instance", A, APPLY, "ec2:RunInstances", ec2(SEOUL), {}),
  ("A", "create a VPC", A, APPLY, "ec2:CreateVpc", f"arn:aws:ec2:{SEOUL}:{ACCT}:vpc/*", {}),
  ("A", "create an app bucket", A, APPLY, "s3:CreateBucket", "arn:aws:s3:::odyssey-app-example", {}),
  ("A", "read main state", A, APPLY, "s3:GetObject", f"{STATE}/main/terraform.tfstate", {}),
  ("A", "write main state", A, APPLY, "s3:PutObject", f"{STATE}/main/terraform.tfstate", {}),
  ("A", "release the main lock", A, APPLY, "s3:DeleteObject", f"{STATE}/main/terraform.tfstate.tflock", {}),
  ("A", "create a role with the boundary", A, APPLY, "iam:CreateRole", APP_ROLE, {"boundary": BOUNDARY}),
  ("A", "read a bootstrap role", A, APPLY, "iam:GetRole", APPLY, {}),
  ("A", "read the log bucket policy", A, APPLY, "s3:GetBucketPolicy", LOG, {}),
  ("A", "create an app rule", A, APPLY, "events:PutRule", f"arn:aws:events:{SEOUL}:{ACCT}:rule/app-example", {}),
  ("A", "create an app topic", A, APPLY, "sns:CreateTopic", f"arn:aws:sns:{SEOUL}:{ACCT}:app-example", {}),
  ("A", "IAM through us-east-1 (global service)", A, APPLY, "iam:CreateRole", APP_ROLE, {"boundary": BOUNDARY, "region": "us-east-1"}),
  ("A", "Route 53 through us-east-1 (global service)", A, APPLY, "route53:ChangeResourceRecordSets", "arn:aws:route53:::hostedzone/ZEXAMPLE", {"region": "us-east-1"}),
  # B. Each P4 Deny: pipeline-apply
  ("B", "DenyBootstrapIamChanges: apply role trust", X, APPLY, "iam:UpdateAssumeRolePolicy", APPLY, {}),
  ("B", "DenyBootstrapIamChanges: boundary version", X, APPLY, "iam:CreatePolicyVersion", BOUNDARY, {}),
  ("B", "DenyBootstrapIamChanges: GitHub OIDC provider", X, APPLY, "iam:DeleteOpenIDConnectProvider", f"arn:aws:iam::{ACCT}:oidc-provider/token.actions.githubusercontent.com", {}),
  ("B", "DenyStateBucketConfig", X, APPLY, "s3:PutBucketPolicy", STATE, {}),
  ("B", "DenyStateObjectHistoryAndAcl: delete a version", X, APPLY, "s3:DeleteObjectVersion", f"{STATE}/main/terraform.tfstate", {}),
  ("B", "DenyStateObjectHistoryAndAcl: object ACL", X, APPLY, "s3:PutObjectAcl", f"{STATE}/main/terraform.tfstate", {}),
  ("B", "DenyBootstrapState", X, APPLY, "s3:GetObject", f"{STATE}/bootstrap/terraform.tfstate", {}),
  ("B", "DenyMainStateDelete", X, APPLY, "s3:DeleteObject", f"{STATE}/main/terraform.tfstate", {}),
  ("B", "RequireBoundaryOnIamWrites: no boundary", X, APPLY, "iam:CreateRole", APP_ROLE, {}),
  ("B", "RequireBoundaryOnIamWrites: other boundary", X, APPLY, "iam:CreateRole", APP_ROLE, {"boundary": f"arn:aws:iam::{ACCT}:policy/other"}),
  ("B", "DenyBoundaryRemoval", X, APPLY, "iam:DeleteRolePermissionsBoundary", APP_ROLE, {}),
  ("B", "DenyIamGroupWrites", X, APPLY, "iam:CreateGroup", f"arn:aws:iam::{ACCT}:group/app-example", {}),
  ("B", "DenyLongLivedCredentials: access key", X, APPLY, "iam:CreateAccessKey", f"arn:aws:iam::{ACCT}:user/app-example", {}),
  ("B", "DenyLongLivedCredentials: admin console password", X, APPLY, "iam:DeleteLoginProfile", ADMIN, {}),
  ("B", "DenyMfaChanges", X, APPLY, "iam:DeactivateMFADevice", ADMIN, {}),
  ("B", "DenyNewIdentityProviders", X, APPLY, "iam:CreateOpenIDConnectProvider", f"arn:aws:iam::{ACCT}:oidc-provider/example.com", {}),
  ("B", "DenyAccountLevelChanges: account S3 Block Public Access", X, APPLY, "s3:PutAccountPublicAccessBlock", "*", {}),
  ("B", "DenyAccountLevelChanges: account contacts", X, APPLY, "account:PutAlternateContact", f"arn:aws:account::{ACCT}:account", {}),
  ("B", "DenyOutsideSeoul: EC2 in us-east-1", X, APPLY, "ec2:RunInstances", ec2("us-east-1"), {"region": "us-east-1"}),
  ("B", "DenyLogBucketConfig", X, APPLY, "s3:PutBucketPolicy", LOG, {}),
  ("B", "DenyLogObjects", X, APPLY, "s3:GetObject", LOG_OBJ, {}),
  ("B", "DenyLoggingAndAlertServices: CloudTrail", X, APPLY, "cloudtrail:StopLogging", f"arn:aws:cloudtrail:{SEOUL}:{ACCT}:trail/bootstrap-trail", {}),
  ("B", "DenyLoggingAndAlertServices: budget", X, APPLY, "budgets:ModifyBudget", f"arn:aws:budgets::{ACCT}:budget/bootstrap-monthly-cost-050pct", {}),
  ("B", "DenyLoggingAndAlertServices: Slack channel", X, APPLY, "chatbot:DeleteSlackChannelConfiguration", "*", {}),
  ("B", "DenyLoggingAndAlertServices: analyzer", X, APPLY, "access-analyzer:DeleteAnalyzer", f"arn:aws:access-analyzer:{SEOUL}:{ACCT}:analyzer/bootstrap-external-access", {}),
  ("B", "DenyAlertRuleChanges", X, APPLY, "events:DisableRule", f"arn:aws:events:{SEOUL}:{ACCT}:rule/bootstrap-g2-apply-assumed", {}),
  ("B", "DenyDefaultBusUpdate", X, APPLY, "events:UpdateEventBus", f"arn:aws:events:{SEOUL}:{ACCT}:event-bus/default", {}),
  ("B", "DenyEventBusPermissionChanges", X, APPLY, "events:PutPermission", "*", {}),
  ("B", "DenyAlertTopicChanges", X, APPLY, "sns:SetTopicAttributes", f"arn:aws:sns:{SEOUL}:{ACCT}:bootstrap-alerts", {}),
  # F. Access points: a request through one names the access point ARN, which DenyLogObjects does not match,
  #    so P4 denies creating them (DenyAccessPointCreation, ADR 0007 (d))
  ("F", "DenyAccessPointCreation: access point", X, APPLY, "s3:CreateAccessPoint", f"arn:aws:s3:{SEOUL}:{ACCT}:accesspoint/example", {}),
  ("F", "DenyAccessPointCreation: Object Lambda access point", X, APPLY, "s3:CreateAccessPointForObjectLambda", f"arn:aws:s3-object-lambda:{SEOUL}:{ACCT}:accesspoint/example", {}),
  ("F", "DenyAccessPointCreation: Multi-Region access point", X, APPLY, "s3:CreateMultiRegionAccessPoint", f"arn:aws:s3::{ACCT}:accesspoint/example", {}),
  # C. Plan role: ReadOnlyAccess + P2, no boundary
  ("C", "read main state", A, PLAN, "s3:GetObject", f"{STATE}/main/terraform.tfstate", {}),
  ("C", "take the main lock", A, PLAN, "s3:PutObject", f"{STATE}/main/terraform.tfstate.tflock", {}),
  ("C", "release the main lock", A, PLAN, "s3:DeleteObject", f"{STATE}/main/terraform.tfstate.tflock", {}),
  ("C", "write main state", I, PLAN, "s3:PutObject", f"{STATE}/main/terraform.tfstate", {}),
  ("C", "read bootstrap state", X, PLAN, "s3:GetObject", f"{STATE}/bootstrap/terraform.tfstate", {}),
  ("C", "read a log object", X, PLAN, "s3:GetObject", LOG_OBJ, {}),
  ("C", "read DynamoDB items", X, PLAN, "dynamodb:GetItem", f"arn:aws:dynamodb:{SEOUL}:{ACCT}:table/example", {}),
  ("C", "create an EC2 instance", I, PLAN, "ec2:RunInstances", ec2(SEOUL), {}),
  # D. Log bucket policy (live), simulated for the admin user because roles cannot take a resource policy
  ("D", "admin deletes a log object version", X, ADMIN, "s3:DeleteObjectVersion", LOG_OBJ, {"resource_policy": True}),
  ("D", "admin deletes a log object", X, ADMIN, "s3:DeleteObject", LOG_OBJ, {"resource_policy": True}),
  ("D", "admin reads a log object", A, ADMIN, "s3:GetObject", LOG_OBJ, {"resource_policy": True}),
  # E. Emergency stop, second switch (E9): a Deny-all boundary blocks the apply role
  ("E", "Deny-all boundary blocks EC2", X, APPLY, "ec2:RunInstances", ec2(SEOUL), {"deny_all": True}),
]
fails = 0
for group, name, expect, src, action, resource, opts in cases:
    try:
        got = simulate(src, action, resource, **opts)
    except RuntimeError as e:
        print(f"ERROR {group} {name}: {e}"); fails += 1; continue
    ok = got == expect
    fails += 0 if ok else 1
    print(f"{'PASS' if ok else 'FAIL'} {group} expect={expect:12} got={got:12} {name}")
print(f"\n{len(cases)} cases, {fails} failed")
raise SystemExit(1 if fails else 0)
