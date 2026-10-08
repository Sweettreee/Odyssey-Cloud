# Budget alerts and the shared alert path (ADR 0006). Security rules publish here too (ADR 0007).

resource "aws_sns_topic" "alerts" {
  name = "bootstrap-alerts"
}

resource "aws_sns_topic_policy" "alerts" {
  arn = aws_sns_topic.alerts.arn
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "AllowBudgetsPublish"
        Effect    = "Allow"
        Principal = { Service = "budgets.amazonaws.com" }
        Action    = "SNS:Publish"
        Resource  = aws_sns_topic.alerts.arn
        Condition = {
          StringEquals = { "aws:SourceAccount" = local.account_id }
          ArnLike      = { "aws:SourceArn" = "arn:aws:budgets::${local.account_id}:*" }
        }
      },
      {
        Sid       = "AllowBootstrapRulesPublish"
        Effect    = "Allow"
        Principal = { Service = "events.amazonaws.com" }
        Action    = "sns:Publish"
        Resource  = aws_sns_topic.alerts.arn
        Condition = {
          StringEquals = { "aws:SourceAccount" = local.account_id }
          ArnLike      = { "aws:SourceArn" = "arn:aws:events:ap-northeast-2:${local.account_id}:rule/bootstrap-*" }
        }
      },
    ]
  })
}

resource "aws_budgets_budget" "monthly" {
  name         = "bootstrap-monthly-cost"
  budget_type  = "COST"
  limit_amount = "20"
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  # false = credits are not subtracted, so credit-covered usage counts as cost (ADR 0006).
  cost_types {
    include_credit = false
  }

  dynamic "notification" {
    for_each = [50, 75, 90, 100, 125]
    content {
      comparison_operator        = "GREATER_THAN"
      threshold                  = notification.value
      threshold_type             = "PERCENTAGE"
      notification_type          = "ACTUAL"
      subscriber_email_addresses = [var.alert_email]
      subscriber_sns_topic_arns  = [aws_sns_topic.alerts.arn]
    }
  }
}

# Channel role with no permissions: the channel can show notifications but cannot act on AWS.
resource "aws_iam_role" "chatbot_channel" {
  name = "bootstrap-chatbot-channel"
  path = "/bootstrap/"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "chatbot.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

# The Amazon Q Developer API has no ap-northeast-2 endpoint; it is managed in us-east-2.
resource "aws_chatbot_slack_channel_configuration" "alerts" {
  region                = "us-east-2"
  configuration_name    = "bootstrap-alerts"
  iam_role_arn          = aws_iam_role.chatbot_channel.arn
  slack_team_id         = var.slack_team_id
  slack_channel_id      = var.slack_channel_id
  sns_topic_arns        = [aws_sns_topic.alerts.arn]
  guardrail_policy_arns = ["arn:aws:iam::aws:policy/AWSDenyAll"]
  logging_level         = "NONE"
}

# TEMPORARY (Step 4, exit criterion 3): remove through E7 after all five alerts arrive (ADR 0006).
resource "aws_budgets_budget" "test" {
  name         = "bootstrap-test-alerts"
  budget_type  = "COST"
  limit_amount = "0.0001"
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  cost_types {
    include_credit = false
  }

  dynamic "notification" {
    for_each = [50, 75, 90, 100, 125]
    content {
      comparison_operator        = "GREATER_THAN"
      threshold                  = notification.value
      threshold_type             = "PERCENTAGE"
      notification_type          = "ACTUAL"
      subscriber_email_addresses = [var.alert_email]
      subscriber_sns_topic_arns  = [aws_sns_topic.alerts.arn]
    }
  }
}
