terraform {
  required_version = ">= 1.5.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.116"
    }
  }

  # --- HCP Terraform (VCS-driven), optional ---------------------------------
  # Uncomment and set your org/workspace to run this the same way as your
  # Linux lab. Leave commented to run locally with the Azure CLI.
  #
  # cloud {
  #   organization = "YOUR-ORG"
  #   workspaces {
  #     name = "ai-sec-win-lab"
  #   }
  # }
}

provider "azurerm" {
  features {}
  # Authentication: set ARM_SUBSCRIPTION_ID (and, for a service principal,
  # ARM_CLIENT_ID / ARM_CLIENT_SECRET / ARM_TENANT_ID) as environment variables,
  # or run `az login` locally before `terraform apply`.
}
