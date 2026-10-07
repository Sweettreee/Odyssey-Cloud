# Security alert rules and cross-Region forwarding (ADR 0007 (b), (c)). Targets with messages: step 3.6b.

locals {
  api_call = "AWS API Call via CloudTrail"
  acct     = [local.account_id]

  g1 = { account = local.acct, detail = { userIdentity = { type = ["Root"] } } }

  g2 = {
    account = local.acct, source = ["aws.sts"], "detail-type" = [local.api_call]
    detail = {
      eventName         = ["AssumeRoleWithWebIdentity"]
      requestParameters = { roleArn = [aws_iam_role.pipeline_apply.arn] }
      errorCode         = [{ exists = false }]
    }
  }

  g3 = { account = local.acct, source = ["aws.iam"], "detail-type" = [local.api_call], detail = { readOnly = [false] } }

  # G4 as separate parts so that no $or is nested inside another $or.
  g4_parts = [
    { account = local.acct, source = ["aws.cloudtrail", "aws.chatbot", "aws.access-analyzer"], "detail-type" = [local.api_call], detail = { readOnly = [false] } },
    { account = local.acct, source = ["aws.events"], "detail-type" = [local.api_call], detail = { readOnly = [false], requestParameters = { name = [{ prefix = "bootstrap-" }] } } },
    { account = local.acct, source = ["aws.events"], "detail-type" = [local.api_call], detail = { readOnly = [false], requestParameters = { rule = [{ prefix = "bootstrap-" }] } } },
    { account = local.acct, source = ["aws.events"], "detail-type" = [local.api_call], detail = { readOnly = [false], eventName = ["UpdateEventBus", "PutPermission", "RemovePermission"] } },
    { account = local.acct, source = ["aws.sns"], "detail-type" = [local.api_call], detail = { readOnly = [false], requestParameters = { topicArn = [{ wildcard = "arn:aws:sns:*:${local.account_id}:bootstrap-*" }] } } },
    { account = local.acct, source = ["aws.sns"], "detail-type" = [local.api_call], detail = { readOnly = [false], requestParameters = { subscriptionArn = [{ wildcard = "arn:aws:sns:*:${local.account_id}:bootstrap-*" }] } } },
    { account = local.acct, source = ["aws.s3"], "detail-type" = [local.api_call], detail = { readOnly = [false], requestParameters = { bucketName = [local.log_bucket] } } },
  ]

  g5 = { account = local.acct, source = ["aws.budgets"], "detail-type" = [local.api_call], detail = { readOnly = [false] } }

  access_analyzer = {
    account = local.acct, source = ["aws.access-analyzer"], "detail-type" = ["Access Analyzer Finding"]
    detail  = { status = ["ACTIVE"], isDeleted = [false] }
  }

  seoul_rules = {
    "bootstrap-g1-root"          = jsonencode(local.g1)
    "bootstrap-g2-apply-assumed" = jsonencode(local.g2)
    "bootstrap-g3-iam"           = jsonencode(local.g3)
    "bootstrap-g4-logging-path"  = jsonencode({ "$or" = local.g4_parts })
    "bootstrap-g5-budget"        = jsonencode(local.g5)
    "bootstrap-access-analyzer"  = jsonencode(local.access_analyzer)
  }

  # G2 is not forwarded: P3 limits the apply role to ap-northeast-2 (ADR 0007 (e)).
  forward_pattern = jsonencode({ "$or" = concat([local.g1, local.g3], local.g4_parts, [local.g5]) })
  forward_regions = toset(["us-east-1", "us-east-2", "us-west-2"])
  seoul_bus_arn   = "arn:aws:events:ap-northeast-2:${local.account_id}:event-bus/default"
}

resource "aws_cloudwatch_event_rule" "seoul" {
  for_each      = local.seoul_rules
  name          = each.key
  event_pattern = each.value
  state         = "ENABLED_WITH_ALL_CLOUDTRAIL_MANAGEMENT_EVENTS"
}

resource "aws_cloudwatch_event_rule" "forward" {
  for_each      = local.forward_regions
  region        = each.key
  name          = "bootstrap-forward"
  event_pattern = local.forward_pattern
  state         = "ENABLED_WITH_ALL_CLOUDTRAIL_MANAGEMENT_EVENTS"
}

resource "aws_cloudwatch_event_target" "forward" {
  for_each = local.forward_regions
  region   = each.key
  rule     = aws_cloudwatch_event_rule.forward[each.key].name
  arn      = local.seoul_bus_arn
  role_arn = aws_iam_role.event_forwarder.arn
}

resource "aws_iam_role" "event_forwarder" {
  name = "event-forwarder"
  path = "/bootstrap/"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "events.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "event_forwarder" {
  name = "put-events-seoul-default-bus"
  role = aws_iam_role.event_forwarder.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = "events:PutEvents"
      Resource = local.seoul_bus_arn
    }]
  })
}

# Alert messages: Amazon Q Developer custom notifications built by input transformers (ADR 0007 (b) Messages).
# Allowlisted scalar fields only; never credentials, whole events, or free text such as errorMessage.
# Templates are raw text, not jsonencode(), which would escape the < > of the EventBridge placeholders.
locals {
  ct_paths = {
    event    = "$.detail.eventName"
    who_type = "$.detail.userIdentity.type"
    who_arn  = "$.detail.userIdentity.arn"
    time     = "$.detail.eventTime"
    region   = "$.detail.awsRegion"
    ip       = "$.detail.sourceIPAddress"
    error    = "$.detail.errorCode"
    login    = "$.detail.responseElements.ConsoleLogin"
    event_id = "$.detail.eventID"
  }

  ct_template = <<-EOT
    {
      "version": "1.0",
      "source": "custom",
      "content": {
        "textType": "client-markdown",
        "title": "__TITLE__",
        "description": "*Event:* <event>\n*Who:* <who_type> <who_arn>\n*Time (UTC):* <time>\n*Region:* <region>\n*Source IP:* <ip>\n*Result:* <error> <login>\n*Event ID:* <event_id>",
        "nextSteps": [
          "Match this event to a merged PR (E7) or to my own E6 task.",
          "Pipeline changes show Who = .../assumed-role/pipeline-apply/RUN_ID."
        ]
      }
    }
  EOT

  g2_paths = {
    time     = "$.detail.eventTime"
    ip       = "$.detail.sourceIPAddress"
    region   = "$.detail.awsRegion"
    run      = "$.detail.requestParameters.roleSessionName"
    event_id = "$.detail.eventID"
  }

  g2_template = <<-EOT
    {
      "version": "1.0",
      "source": "custom",
      "content": {
        "textType": "client-markdown",
        "title": ":rotating_light: G2 pipeline-apply was assumed",
        "description": "*Time (UTC):* <time>\n*Source IP:* <ip>\n*Region:* <region>\n*Run:* <run>\n*Event ID:* <event_id>",
        "nextSteps": [
          "Open https://github.com/Sweettreee/Odyssey-Cloud/actions/runs/<run> . It is mine only if I approved it and the time matches (UTC = KST - 9 h).",
          "Otherwise run E9 now, follow ADR 0005 \"After each use\", and later look up the Event ID.",
          "A broken link or a time mismatch is itself an E9 trigger; the session name is a clue, not evidence."
        ]
      }
    }
  EOT

  aa_paths = {
    resource      = "$.detail.resource"
    resource_type = "$.detail.resourceType"
    principal_aws = "$.detail.principal.AWS"
    principal_fed = "$.detail.principal.Federated"
    public        = "$.detail.isPublic"
    error         = "$.detail.error"
    finding_id    = "$.detail.id"
    region        = "$.region"
  }

  aa_template = <<-EOT
    {
      "version": "1.0",
      "source": "custom",
      "content": {
        "textType": "client-markdown",
        "title": ":mag: Access Analyzer: external access found",
        "description": "*Resource:* <resource>\n*Resource type:* <resource_type>\n*Principal (AWS):* <principal_aws>\n*Principal (Federated):* <principal_fed>\n*Public:* <public>\n*Error:* <error>\n*Finding ID:* <finding_id>\n*Region:* <region>",
        "nextSteps": [
          "Expected at E4: findings for pipeline-plan and pipeline-apply (they trust the GitHub OIDC provider).",
          "Any other finding: check who changed the policy in CloudTrail and whether the access is intended."
        ]
      }
    }
  EOT

  messages = {
    "bootstrap-g1-root"          = { paths = local.ct_paths, template = replace(local.ct_template, "__TITLE__", ":rotating_light: G1 Root activity") }
    "bootstrap-g2-apply-assumed" = { paths = local.g2_paths, template = local.g2_template }
    "bootstrap-g3-iam"           = { paths = local.ct_paths, template = replace(local.ct_template, "__TITLE__", ":rotating_light: G3 IAM change") }
    "bootstrap-g4-logging-path"  = { paths = local.ct_paths, template = replace(local.ct_template, "__TITLE__", ":rotating_light: G4 Logging or alert path change") }
    "bootstrap-g5-budget"        = { paths = local.ct_paths, template = replace(local.ct_template, "__TITLE__", ":rotating_light: G5 Budget change") }
    "bootstrap-access-analyzer"  = { paths = local.aa_paths, template = local.aa_template }
  }
}

resource "aws_cloudwatch_event_target" "seoul" {
  for_each = local.messages
  rule     = aws_cloudwatch_event_rule.seoul[each.key].name
  arn      = aws_sns_topic.alerts.arn

  input_transformer {
    input_paths    = each.value.paths
    input_template = each.value.template
  }
}
