variable "resource_group_name" {
  description = "Existing resource group to deploy into (not created by this config)."
  type        = string
  default     = "RG_AI_Security_Demo"
}

variable "prefix" {
  description = "Name prefix for the resources this config creates."
  type        = string
  default     = "aisec-win"
}

variable "vm_size" {
  description = <<-EOT
    VM size. qwen2.5:7b on CPU is usable but slow; for a snappy live demo prefer a
    GPU size (e.g. Standard_NC4as_T4_v3) or use a smaller model (ollama_model).
    Default is a balanced CPU size with 16 GB RAM.
  EOT
  type        = string
  default     = "Standard_D4s_v5"
}

variable "admin_username" {
  description = "Local administrator username for the Windows VM."
  type        = string
  default     = "azureuser"
}

variable "admin_password" {
  description = <<-EOT
    Local administrator password. Must meet Windows complexity: 12-123 chars with
    3 of {lowercase, uppercase, digit, symbol}. Set it via a TF_VAR / HCP variable,
    not in version control.
  EOT
  type        = string
  sensitive   = true
}

variable "ollama_model" {
  description = "Ollama model to pull during provisioning. Use qwen2.5:3b for faster CPU demos."
  type        = string
  default     = "qwen2.5:7b"
}

variable "app_repo_url" {
  description = <<-EOT
    Optional git URL to clone onto the VM and set up (the demo app lives under
    /app in this repo). Set it to THIS repository's clone URL to auto-deploy the
    dashboard. Leave empty to install only the prerequisites.
  EOT
  type        = string
  default     = ""
}

variable "install_vscode" {
  description = "Also install Visual Studio Code."
  type        = bool
  default     = true
}

variable "os_disk_size_gb" {
  description = "OS disk size in GB."
  type        = number
  default     = 128
}
