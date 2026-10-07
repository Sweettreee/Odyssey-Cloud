# GitHub Actions OIDC trust and the two pipeline roles (ADR 0004).
# Policy JSON in policies/ must match ADR 0004; placeholders <X> become ${x}.

locals {
  policy_vars = {
    account_id   = local.account_id
    owner_id     = local.github_owner_id
    repo_id      = local.github_repo_id
    actor_id     = local.github_actor_id
    state_bucket = aws_s3_bucket.state.bucket
    log_bucket   = local.log_bucket
  }
}

# No thumbprint_list: for GitHub, AWS validates with its own trusted CA library.
resource "aws_iam_openid_connect_provider" "github" {
  url            = "https://token.actions.githubusercontent.com"
  client_id_list = ["sts.amazonaws.com"]
}

resource "aws_iam_role" "pipeline_plan" {
  name               = "pipeline-plan"
  path               = "/bootstrap/"
  assume_role_policy = templatefile("${path.module}/policies/p1-plan-trust.json", local.policy_vars)
  depends_on         = [aws_iam_openid_connect_provider.github]
}

resource "aws_iam_role_policy_attachment" "pipeline_plan_readonly" {
  role       = aws_iam_role.pipeline_plan.name
  policy_arn = "arn:aws:iam::aws:policy/ReadOnlyAccess"
}

resource "aws_iam_role_policy" "pipeline_plan_p2" {
  name   = "p2-state-lock-and-read-denies"
  role   = aws_iam_role.pipeline_plan.id
  policy = templatefile("${path.module}/policies/p2-plan-inline.json", local.policy_vars)
}

# P4: the apply role and every identity the pipeline creates must carry this boundary.
resource "aws_iam_policy" "pipeline_boundary" {
  name   = "pipeline-boundary"
  path   = "/bootstrap/"
  policy = templatefile("${path.module}/policies/p4-boundary.json", local.policy_vars)
}

resource "aws_iam_role" "pipeline_apply" {
  name                 = "pipeline-apply"
  path                 = "/bootstrap/"
  assume_role_policy   = templatefile("${path.module}/policies/p3-apply-trust.json", local.policy_vars)
  permissions_boundary = aws_iam_policy.pipeline_boundary.arn
  depends_on           = [aws_iam_openid_connect_provider.github]
}

resource "aws_iam_role_policy_attachment" "pipeline_apply_admin" {
  role       = aws_iam_role.pipeline_apply.name
  policy_arn = "arn:aws:iam::aws:policy/AdministratorAccess"
}
