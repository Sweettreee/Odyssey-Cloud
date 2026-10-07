# External access analyzer for Seoul resources and all IAM roles (ADR 0007 (c)). No archive rules.
resource "aws_accessanalyzer_analyzer" "external" {
  analyzer_name = "bootstrap-external-access"
  type          = "ACCOUNT"
}
