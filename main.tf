locals {
  tags = {
    project = "ai-security-lab"
    stack   = "windows-demo"
  }
}

# Use the existing resource group (not created/managed by this config).
data "azurerm_resource_group" "rg" {
  name = var.resource_group_name
}

resource "azurerm_virtual_network" "vnet" {
  name                = "${var.prefix}-vnet"
  address_space       = ["10.60.0.0/16"]
  location            = data.azurerm_resource_group.rg.location
  resource_group_name = data.azurerm_resource_group.rg.name
  tags                = local.tags
}

resource "azurerm_subnet" "subnet" {
  name                 = "${var.prefix}-subnet"
  resource_group_name  = data.azurerm_resource_group.rg.name
  virtual_network_name = azurerm_virtual_network.vnet.name
  address_prefixes     = ["10.60.1.0/24"]
}

# NSG with no inbound allow rules: Azure defaults deny inbound from the internet
# and allow intra-VNet traffic, so a Bastion/peering you add later can reach RDP
# over the private network without any rule allowing RDP in from outside.
resource "azurerm_network_security_group" "nsg" {
  name                = "${var.prefix}-nsg"
  location            = data.azurerm_resource_group.rg.location
  resource_group_name = data.azurerm_resource_group.rg.name
  tags                = local.tags
}

# Private NIC only -- no public IP.
resource "azurerm_network_interface" "nic" {
  name                = "${var.prefix}-nic"
  location            = data.azurerm_resource_group.rg.location
  resource_group_name = data.azurerm_resource_group.rg.name
  tags                = local.tags

  ip_configuration {
    name                          = "ipcfg"
    subnet_id                     = azurerm_subnet.subnet.id
    private_ip_address_allocation = "Dynamic"
  }
}

resource "azurerm_network_interface_security_group_association" "nic_nsg" {
  network_interface_id      = azurerm_network_interface.nic.id
  network_security_group_id = azurerm_network_security_group.nsg.id
}

resource "azurerm_windows_virtual_machine" "vm" {
  name                = "${var.prefix}-vm"
  resource_group_name = data.azurerm_resource_group.rg.name
  location            = data.azurerm_resource_group.rg.location
  size                = var.vm_size
  admin_username      = var.admin_username
  admin_password      = var.admin_password
  provision_vm_agent  = true
  tags                = local.tags

  network_interface_ids = [azurerm_network_interface.nic.id]

  os_disk {
    caching              = "ReadWrite"
    storage_account_type = "Premium_LRS"
    disk_size_gb         = var.os_disk_size_gb
  }

  # Windows Server 2022 Datacenter, Azure Edition = Desktop Experience (full GUI).
  source_image_reference {
    publisher = "MicrosoftWindowsServer"
    offer     = "WindowsServer"
    sku       = "2022-datacenter-azure-edition"
    version   = "latest"
  }
}

# Bootstrap: decode the PowerShell script (embedded, so no public-repo dependency)
# to disk and run it with the chosen parameters, logging to C:\bootstrap.log.
# resource "azurerm_virtual_machine_extension" "bootstrap" {
#  name                       = "bootstrap"
#  virtual_machine_id         = azurerm_windows_virtual_machine.vm.id
#  publisher                  = "Microsoft.Compute"
#  type                       = "CustomScriptExtension"
#  type_handler_version       = "1.10"
#  auto_upgrade_minor_version = true

#  settings = jsonencode({
#    commandToExecute = join("", [
#      "powershell -ExecutionPolicy Bypass -NoProfile -Command \"",
#      "[IO.File]::WriteAllBytes('C:\\bootstrap.ps1',[Convert]::FromBase64String('",
#      base64encode(file("${path.module}/scripts/bootstrap.ps1")),
#      "')); ",
#      "powershell -ExecutionPolicy Bypass -File C:\\bootstrap.ps1 ",
#      "-Model '", var.ollama_model, "' ",
#      "-AppRepoUrl '", var.app_repo_url, "' ",
#      "-InstallVSCode '", tostring(var.install_vscode), "' ",
#      "*> C:\\bootstrap.log 2>&1\""
#    ])
#  })
3}
