terraform {
  required_version = "~> 1.16.0"

  # Pipeline roles may touch only this key and its lock file (ADR 0004 P2, P4).
  backend "s3" {
    bucket       = "odyssey-tfstate-186972156090"
    key          = "main/terraform.tfstate"
    region       = "ap-northeast-2"
    use_lockfile = true
  }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.23"
    }
  }
}
