# A05 - PowerScale automation as code

| Tier | Time | Domains | Prerequisites |
|---|---|---|---|
| SIM (OneFS Simulator) / HW | 3 h | PLT, ARC | A01, A02; L01 Step 7 (Ansible collections, Terraform) |

Goal: one tenant definition file creates the zone, export, share and quota, and re-running it changes nothing.

## Steps

### Step 1 - Explore the OneFS Platform API (PAPI)
```bash
export PS_USER=root PS_PASS='<root password>'
curl -sk -u $PS_USER:$PS_PASS https://$PS:8080/platform/latest | head        # highest API version
curl -sk -u $PS_USER:$PS_PASS https://$PS:8080/platform/latest/cluster/config | python3 -m json.tool | head -20
curl -sk -u $PS_USER:$PS_PASS https://$PS:8080/platform/latest/zones | python3 -m json.tool | grep '"name"'
```
For production, create a dedicated API user with an RBAC role instead of `root`, and use session auth (`POST /session/1/session`).

### Step 2 - Tenant definition
Create `labs/evidence/a05/tenant-ml.yaml`:
```yaml
tenant: bu-ml
zone_path: /ifs/bu-ml
dataset_path: /ifs/bu-ml/datasets
nfs_clients: ["10.10.10.0/24"]
quota_hard_gb: 5
quota_soft_gb: 4
```

### Step 3 - Ansible playbook
`labs/evidence/a05/tenant.yml`:
```yaml
- hosts: localhost
  gather_facts: false
  vars_files: [tenant-ml.yaml]
  module_defaults:
    group/dellemc.powerscale.powerscale:
      onefs_host: "{{ lookup('env','PS') }}"
      port_no: "8080"
      api_user: "{{ lookup('env','PS_USER') }}"
      api_password: "{{ lookup('env','PS_PASS') }}"
      verify_ssl: false
  tasks:
    - name: Access zone
      dellemc.powerscale.accesszone:
        az_name: "{{ tenant }}"
        path: "{{ zone_path }}"
        create_path: true
        state: present
    - name: Dataset directory
      dellemc.powerscale.filesystem:
        path: "{{ dataset_path }}"
        access_zone: System
        owner: {name: root, provider_type: local}
        recursive: true
        state: present
    - name: NFS export
      dellemc.powerscale.nfs:
        path: "{{ dataset_path }}"
        access_zone: "{{ tenant }}"
        client_type: clients
        clients: "{{ nfs_clients }}"
        client_state: present-in-export
        state: present
    - name: Quota
      dellemc.powerscale.smartquota:
        path: "{{ zone_path }}"
        quota_type: directory
        access_zone: System
        quota:
          hard_limit_size: "{{ quota_hard_gb }}"
          soft_limit_size: "{{ quota_soft_gb }}"
          soft_grace_period: 1
          period_unit: days
          cap_unit: GB
          container: true
        state: present
```
Run it twice:
```bash
cd labs/evidence/a05
ansible-playbook tenant.yml      # first run: changed=4
ansible-playbook tenant.yml      # second run: changed=0  (idempotent)
```
Parameter names differ between collection versions. If a task fails, run `ansible-doc dellemc.powerscale.<module>` and adjust.

### Step 4 - Same tenant with Terraform
`labs/evidence/a05/tf/main.tf`:
```hcl
terraform {
  required_providers { powerscale = { source = "dell/powerscale" } }
}
provider "powerscale" {
  endpoint = "https://${var.ps}:8080"
  username = var.ps_user
  password = var.ps_pass
  insecure = true
}
variable "ps" {}
variable "ps_user" {}
variable "ps_pass" { sensitive = true }

resource "powerscale_filesystem" "ds" {
  directory_path = "/ifs/bu-tf"
  name           = "datasets"
  recursive      = true
  owner          = { id = "UID:0", name = "root", type = "user" }
}
resource "powerscale_accesszone" "tenant" {
  name       = "bu-tf"
  path       = "/ifs/bu-tf"
  groupnet   = "groupnet0"
  depends_on = [powerscale_filesystem.ds]
}
resource "powerscale_nfs_export" "ds" {
  paths   = ["/ifs/bu-tf/datasets"]
  zone    = powerscale_accesszone.tenant.name
  clients = ["10.10.10.0/24"]
}
resource "powerscale_quota" "tenant" {
  path       = "/ifs/bu-tf"
  type       = "directory"
  zone       = "System"
  container  = true
  thresholds = { hard = 5368709120, soft = 4294967296, soft_grace = 86400 }
}
```
```bash
cd tf && terraform init && terraform apply -var ps=$PS -var ps_user=$PS_USER -var ps_pass=$PS_PASS
terraform plan -var ps=$PS -var ps_user=$PS_USER -var ps_pass=$PS_PASS     # "No changes."
```
Attribute names follow the `dell/powerscale` provider docs on the Terraform Registry. Check them against the provider version you install.

### Step 5 - Detect drift
1. Change the quota by hand: `ssh root@$PS isi quota quotas modify /ifs/bu-tf directory --hard-threshold=10G`.
2. `terraform plan`. Expected: Terraform reports the drift and offers to change the quota back to 5 GiB.
3. `ansible-playbook tenant.yml --check --diff` does the same for the Ansible-managed tenant.

### Step 6 - Time it
Destroy and re-create a tenant with each tool and record the wall-clock time.

## Verify
- [ ] The tenant is created from code with Ansible and with Terraform.
- [ ] The second run is a no-op.
- [ ] A manual change is detected as drift.
- [ ] Tenant creation takes under 5 minutes.

## Record for the standards
`PLT-04` IaC toolchain (Ansible vs. Terraform for storage). `PLT-05` GitOps. `ARC-07` standards enforcement (drift detection).

## Cleanup
`terraform destroy ...`, then remove the Ansible tenant: set `state: absent` in the playbook (reverse order) or delete it by hand with `isi`.
