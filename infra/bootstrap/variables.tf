variable "alert_email" {
  description = "Email address that receives budget notifications (ADR 0006)."
  type        = string
  sensitive   = true
}

variable "slack_team_id" {
  description = "Slack workspace ID authorized in E10 (ADR 0006)."
  type        = string
  sensitive   = true
}

variable "slack_channel_id" {
  description = "Private Slack channel ID that receives alerts (ADR 0006)."
  type        = string
  sensitive   = true
}
