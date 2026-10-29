# AI Security Lab — Windows Server 2022 (Terraform)

Provisions a **Windows Server 2022 Datacenter, Azure Edition (Desktop Experience / full GUI)**
VM into an **existing resource group** (`RG_AI_Security_Demo`), with **no public IP**
and **no inbound RDP rule**, and installs every prerequisite for the Straiker demo,
unattended:

- **Google Chrome** and **Mozilla Firefox**
- **Python 3.12**, **Git**, **7-Zip**, and (optional) **VS Code**
- **Ollama** + the model pulled into a shared model directory
- Optionally clones and sets up the **demo dashboard** (under `app/`) with a
  desktop shortcut

Everything installs via a Custom Script Extension on first boot (logged to
`C:\bootstrap.log` on the VM). The PowerShell bootstrap is embedded in the
Terraform, so this works with a **private** repo — nothing is fetched from a
public raw URL.

## Layout

```
versions.tf              provider + optional HCP cloud block
variables.tf             all inputs
main.tf                  existing-RG data source, new VNet, NSG, private VM, bootstrap
outputs.tf               private IP, VM name
scripts/bootstrap.ps1    unattended install (Chrome, Firefox, Python, Git, Ollama, app)
terraform.tfvars.example copy to terraform.tfvars and edit
app/                     the demo dashboard (deployed when app_repo_url is set)
```

## Prerequisites

- An Azure subscription and either the **Azure CLI** (`az login`) locally, or
  **HCP Terraform** with Azure credentials (uncomment the `cloud {}` block in
  `versions.tf`).
- Terraform >= 1.5 (not needed if you run via HCP VCS-driven workspace).

## Run it (local)

```bash
az login
cp terraform.tfvars.example terraform.tfvars   # edit: password, your RDP IP, etc.
terraform init
terraform apply
```

The existing `RG_AI_Security_Demo` must already exist; this config reads it with a
data source and does not create or manage it. The outputs print the VM's **private
IP** (there is no public IP).

### Reaching the VM (no public IP, no inbound RDP)

This config creates a fresh VNet (`aisec-win-vnet`, `10.60.0.0/16`) with no
connectivity of its own. Attach access yourself, then RDP to the private IP:

- **VNet peering / VPN / ExpressRoute:** peer `aisec-win-vnet` to a hub you can
  already reach, then `mstsc /v:<private-ip>`.
- **Azure Bastion:** add a Bastion to the VNet (needs an `AzureBastionSubnet` and
  its own public IP) and connect from the portal — browser RDP over the private IP.

The NSG has no inbound allow rules; Azure's defaults permit intra-VNet traffic
(so Bastion/peering works) while denying inbound from the internet.

## Run it (HCP Terraform, like your Linux lab)

1. Uncomment and set the `cloud {}` block in `versions.tf`.
2. Push this repo to GitHub, connect the workspace to it (VCS-driven).
3. Set workspace variables: `admin_password` (sensitive), `resource_group_name`
   (defaults to `RG_AI_Security_Demo`), and the Azure credentials as environment
   variables (`ARM_SUBSCRIPTION_ID`, `ARM_CLIENT_ID`, `ARM_CLIENT_SECRET`, `ARM_TENANT_ID`).
4. Queue a plan/apply.

## After it comes up

1. RDP in as `admin_username`.
2. Provisioning continues in the background on first boot — watch `C:\bootstrap.log`.
   Chrome, Firefox, Python, Git, VS Code and Ollama (with the model) install there.
3. If you set `app_repo_url`, a **“Start Straiker Demo”** shortcut is on the
   desktop. Open the app's `.env`, paste your Straiker key
   (`STRAIKER_AGENT_API_KEY=sk_agt_…`), then launch the shortcut — it opens the
   dashboard at `http://127.0.0.1:8800`.

## Important notes

- **Performance:** `qwen2.5:7b` on a CPU VM works but is slow. For a live demo,
  either set `vm_size` to a GPU size (e.g. `Standard_NC4as_T4_v3`, which also
  needs the NVIDIA driver extension — ask and I'll add it) or set
  `ollama_model = "qwen2.5:3b"` for a much snappier CPU experience.
- **Access:** the VM is private (no public IP, no inbound RDP rule). It is not
  reachable until you peer the VNet or add a Bastion (see "Reaching the VM" above).
- **Secrets:** never commit `terraform.tfvars` with a real password. Use a
  `TF_VAR_admin_password` env var or an HCP sensitive variable. The Straiker key
  is added by you on the box (in the app's `.env`), so it never lands in
  Terraform state.
- **Ollama model sharing:** the bootstrap sets a machine-wide `OLLAMA_MODELS`
  (`C:\ollama-models`) so the model pulled during provisioning is the same one
  your RDP session sees. If `ollama` isn't serving right after login, run
  `ollama serve` once (or just launch the demo shortcut; the model is already
  cached).

## Teardown

```bash
terraform destroy
```
