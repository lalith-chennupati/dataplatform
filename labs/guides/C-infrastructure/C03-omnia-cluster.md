# C03 - Bare-metal AI cluster with Omnia

| Tier | Time | Domains | Prerequisites |
|---|---|---|---|
| SIM (3+ VMs on one host) / HW (PowerEdge control node + 2 GPU nodes) | 1 day | PLT, CMP, NET | C01. A host with 32 GB RAM and KVM for SIM. |

Dell Omnia is open source (`github.com/dell/omnia`). It provisions bare-metal nodes over PXE and then deploys Kubernetes and/or Slurm, GPU drivers and fabric software with Ansible. **Untested here:** my VM has no nested virtualisation or PXE network, so the steps below follow the Omnia documentation and were not run. Omnia changes its input files between releases (1.5 -> 1.6 -> 1.7 -> 2.x). Open `docs/` for your release and check every file name and key before you run anything.

SIM layout: one Rocky Linux / Ubuntu VM as the **control node** (2 NICs: public + an isolated "PXE" network), and two or more empty VMs on the PXE network set to boot from network. Use libvirt/virt-manager or VirtualBox; give each compute VM 4 vCPU / 8 GB.
HW layout: control node with an OOB/iDRAC NIC, an admin/PXE NIC and a public NIC. Compute nodes reachable over iDRAC (Omnia can discover them via BMC) and the admin network.

## Steps

### Step 1 - Write the cluster design before touching Omnia
Fill in and commit `cluster-design.md` (it is your PLT-04 evidence):
- Node roles: control/head, login, Kubernetes control plane, Kubernetes workers, Slurm controller, Slurm compute.
- Networks: admin/PXE CIDR, BMC CIDR, public, back-end fabric (C06). DNS domain and host naming (`NET-09`, `ARC-03`).
- OS image and version, GPU driver/CUDA version, Kubernetes version, Slurm version (`PLT-03`).
- Which scheduler(s): Kubernetes only, Slurm only, or both on separate node groups (`CMP-06`).

### Step 2 - Prepare the control node
```bash
sudo dnf -y install git || sudo apt -y install git
git clone https://github.com/dell/omnia.git && cd omnia
git checkout <release-tag>          # pin a release, never run from main
./prereq.sh                         # installs Ansible and the Python venv Omnia needs (path printed at the end)
ls input/                           # the input files for this release
```
Expected: `prereq.sh` ends without errors. Record the release tag in the evidence log.

### Step 3 - Software and provisioning inputs
Edit the files your release documents. In 1.6/1.7 they are:
- `input/software_config.json`: OS (`cluster_os_type`, `cluster_os_version`), `repo_config` (`always`/`partial`/`never` for local mirrors - use a local repo if you need air-gap, `PLT-10`), and the software list (e.g. `k8s`, `slurm`, `cuda`, `ofed`, `nfs`, `openldap`).
- `input/network_spec.yml`: `admin_network` (NIC, CIDR, DHCP range) and `bmc_network`.
- `input/provision_config.yml` / `provision_config_credentials.yml`: discovery mechanism (`switch_based`, `mapping`, `bmc`), timezone, language, node name prefix, credentials.
For SIM use the **mapping** discovery: list each VM's PXE MAC, hostname and admin IP in a mapping file, so no switch or BMC is needed.

Keep credentials out of Git. Omnia can encrypt the credentials file with Ansible Vault.

### Step 4 - Build local repositories
```bash
ansible-playbook local_repo/local_repo.yml          # downloads packages/images for the chosen software
```
Expected: the playbook completes and the repo path holds the OS, CUDA and Kubernetes packages. Record download size and time. This step decides how long an air-gapped rebuild takes.

### Step 5 - Discover and provision nodes
```bash
ansible-playbook discovery_provision.yml
```
Then power on the compute VMs (HW: Omnia can power them on through iDRAC). They PXE-boot, install the OS and register.
```bash
# xCAT is used by Omnia 1.x for provisioning
lsdef -t node                                   # nodes discovered
nodestat all                                    # 'sshd' when the OS is installed
```
Expected: each node shows `sshd` and is reachable by hostname. Record the time from power-on to `sshd` for one node.

### Step 6 - Deploy Kubernetes and Slurm
Write the inventory (group names differ by release; 1.6/1.7 use the groups below):
```ini
[slurm_control_node]
node001
[slurm_node]
node002
[login]
[kube_control_plane]
node001
[kube_node]
node002
node003
[auth_server]
node001
```
```bash
ansible-playbook omnia.yml -i inventory        # or scheduler.yml for scheduler-only runs
```
Verify:
```bash
ssh node001 kubectl get nodes -o wide          # all Ready
ssh node001 sinfo                              # partition up, node002 idle
ssh node001 srun -N1 hostname
# HW only:
ssh node002 nvidia-smi
ssh node002 ibstat || ssh node002 rdma link    # IB/RoCE ports active (C06)
```

### Step 7 - Add a node and rebuild one
1. Add `node004` to the mapping file, rerun `discovery_provision.yml`, add it to the inventory and run `omnia.yml` again.
2. Check that the new node joins Kubernetes/Slurm and that existing nodes are unchanged (no unplanned reboots, same versions).
3. Wipe `node003` (reinstall from PXE) and rerun the playbooks. Compare its package/driver versions with `node002`:
```bash
for n in node002 node003; do ssh $n 'uname -r; rpm -qa | sort | md5sum; nvidia-smi --query-gpu=driver_version --format=csv,noheader 2>/dev/null'; done
```
Expected: identical output. A difference means the build is not reproducible.

### Step 8 - Compare with your alternative
Write one paragraph comparing Omnia with the toolchain you would otherwise use (Canonical MAAS, Foreman, Metal3, Bright/Base Command Manager, OpenShift bare-metal IPI, or OME + Ansible from C02): day-0 time, day-2 upgrades, support model, air-gap support.

## Verify
- [ ] Nodes are provisioned from bare metal by the toolchain without manual OS installs.
- [ ] Kubernetes and/or Slurm run a test job.
- [ ] A new node joins with one rerun of the playbooks.
- [ ] A rebuilt node is identical to its peers.
- [ ] Release tag, input files (without secrets) and timings are recorded.

## Record for the standards
`PLT-04` provisioning toolchain (Omnia or alternative) and the release pinning rule. `PLT-03` OS/driver/Kubernetes/Slurm baseline. `CMP-06` scheduler(s). `PLT-10` local-repo / air-gap capability. `NET-09` addressing and naming. `PLT-06` how upgrades are rolled (rerun playbooks per node group).

## Cleanup
SIM: delete the VMs and the PXE network. HW: return the nodes to their owners or leave them in the agreed state. Keep the input files (without credentials) in Git.
