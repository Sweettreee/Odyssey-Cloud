terraform {
  required_version = "~> 1.16.0"

  # E5: state moved into the bucket this module creates (ADR 0003 C-1). Backend blocks take literals only.
  backend "s3" {
    bucket       = "odyssey-tfstate-186972156090"
    key          = "bootstrap/terraform.tfstate"
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
