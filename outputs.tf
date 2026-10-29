output "resource_group" {
  description = "Resource group the VM was deployed into."
  value       = data.azurerm_resource_group.rg.name
}

output "vm_name" {
  description = "Name of the Windows VM."
  value       = azurerm_windows_virtual_machine.vm.name
}

output "private_ip_address" {
  description = "Private IP of the VM (reach it over your own Bastion/peering/VPN)."
  value       = azurerm_network_interface.nic.private_ip_address
}

output "admin_username" {
  description = "Local administrator username."
  value       = var.admin_username
}

output "notes" {
  description = "Post-provision guidance."
  value       = <<-EOT
    The VM has NO public IP and NO inbound RDP rule. Reach it privately over a
    Bastion, VNet peering, or VPN that you attach to its VNet (${var.prefix}-vnet,
    10.60.0.0/16), then RDP to its private IP as ${var.admin_username}.

    Provisioning runs on first boot; C:\bootstrap.log shows progress. Chrome,
    Firefox, Python, Git${var.install_vscode ? ", VS Code" : ""} and Ollama (model
    ${var.ollama_model}) are installed by the bootstrap. If app_repo_url was set, a
    "Start Straiker Demo" desktop shortcut runs the dashboard at
    http://127.0.0.1:8800 (add your Straiker key to the app's .env first).
  EOT
}
