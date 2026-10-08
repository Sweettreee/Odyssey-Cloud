provider "aws" {
  region              = "ap-northeast-2"
  allowed_account_ids = ["186972156090"]

  default_tags {
    tags = {
      ManagedBy = "terraform"
      Module    = "main"
    }
  }
}
