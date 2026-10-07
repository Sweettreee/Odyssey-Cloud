provider "aws" {
  region              = "ap-northeast-2"
  allowed_account_ids = [local.account_id]

  default_tags {
    tags = {
      ManagedBy = "terraform"
      Module    = "bootstrap"
    }
  }
}
