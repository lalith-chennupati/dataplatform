# C02 - Fleet management with OpenManage Enterprise

| Tier | Time | Domains | Prerequisites |
|---|---|---|---|
| DEMO / HW (OpenManage Enterprise appliance + iDRACs). Ansible part can be dry-run in SIM. | 4 h | PLT, OPS, CMP | C01; L01 Step 7 (`dellemc.openmanage` collection) |

## Prerequisites
- OpenManage Enterprise (OME) virtual appliance (OVA/VHD/KVM image from Dell Support) deployed, with its IP and admin password. A Dell Demo Center OME lab also works.
- At least two iDRACs reachable from OME. Their credentials.
- The validated driver/firmware matrix for your AI Factory release (from Dell's AI Factory documentation / your Dell team).
```bash
export OME=<ome-ip> OME_USER=admin OME_PASS='<password>'
O() { curl -sk -u "$OME_USER:$OME_PASS" "https://$OME/api$1" "${@:2}"; }
```

## Steps

### Step 1 - Discover the GPU nodes
UI: *Monitor > Discovery > Create*. Choose type *Server*, enter the iDRAC IP range, then the credentials.
API:
```bash
O /DiscoveryConfigService/DiscoveryConfigGroups -X POST -H 'Content-Type: application/json' -d '{
  "DiscoveryConfigGroupName": "ai-factory-gpu-nodes",
  "DiscoveryConfigModels": [{"DiscoveryConfigTargets": [{"NetworkAddressDetail": "10.20.0.11-10.20.0.20"}],
     "ConnectionProfile": "{\"profileName\":\"\",\"profileDescription\":\"\",\"type\":\"DISCOVERY\",\"credentials\":[{\"type\":\"REDFISH\",\"authType\":\"Basic\",\"modified\":false,\"credentials\":{\"username\":\"root\",\"password\":\"<idrac-pw>\",\"port\":443,\"retries\":3,\"timeout\":60}}]}",
     "DeviceType": [1000]}],
  "Schedule": {"RunNow": true}}'
O "/DeviceService/Devices?\$select=Id,DeviceName,Model,DeviceServiceTag" | python3 -m json.tool
```

### Step 2 - Static and query groups
1. Create a static group `AI-Factory/GPU-Nodes` with the discovered XE nodes.
2. Create a query group `AI-Factory/Non-Compliant`, rule *Firmware compliance != OK*.

### Step 3 - Firmware catalog and baseline
1. *Configuration > Firmware/Driver Compliance > Catalog Management*. Add a catalog: *Latest component versions on Dell.com*, or a network share with the catalog that matches the validated matrix.
2. *Create Baseline* `aif-baseline-<release>` from that catalog, targeting the `GPU-Nodes` group.
3. *Check compliance*, then export the report (CSV) to the evidence folder.
```bash
O /UpdateService/Baselines | python3 -c "import sys,json;[print(b['Id'], b['Name'], b['ComplianceSummary']) for b in json.load(sys.stdin)['value']]"
```

### Step 4 - Fix non-compliance with Ansible
`labs/evidence/c02/firmware.yml`:
```yaml
- hosts: localhost
  gather_facts: false
  tasks:
    - name: Compliance report for the AI baseline
      dellemc.openmanage.ome_firmware_baseline_compliance_info:
        hostname: "{{ lookup('env','OME') }}"
        username: "{{ lookup('env','OME_USER') }}"
        password: "{{ lookup('env','OME_PASS') }}"
        validate_certs: false
        baseline_name: aif-baseline-2026a
      register: compliance
    - debug: var=compliance.baseline_compliance_info
    - name: Update non-compliant components of the group (reboot handled by OME job)
      dellemc.openmanage.ome_firmware:
        hostname: "{{ lookup('env','OME') }}"
        username: "{{ lookup('env','OME_USER') }}"
        password: "{{ lookup('env','OME_PASS') }}"
        validate_certs: false
        baseline_name: aif-baseline-2026a
        device_group_names: ["GPU-Nodes"]
        schedule: RebootNow
      when: run_update | default(false) | bool
```
```bash
ansible-playbook labs/evidence/c02/firmware.yml                      # report only
ansible-playbook labs/evidence/c02/firmware.yml -e run_update=true   # during a maintenance window
```
Without OME, check the syntax with `ansible-playbook --syntax-check`, and read the options with `ansible-doc dellemc.openmanage.ome_firmware`.

### Step 5 - Deployment template
1. *Configuration > Templates > Create template > From reference device*. Pick the golden GPU node and select BIOS, iDRAC, NIC and RAID.
2. Deploy the template to a second node, then run *Configuration compliance* against it.
3. Change one BIOS value by hand on the second node and run compliance again. Expected: the node shows as non-compliant.

### Step 6 - Alert policies
*Alerts > Alert policies > Create*: category *Storage, System Health, Updates*, severity *Critical/Warning*, targets `GPU-Nodes`. Actions: email, syslog to your SIEM, or SNMP trap. Generate a test alert (for example, remove a redundant PSU cable on a test node, or send a test event from iDRAC) and confirm that it arrives.

### Step 7 - Plugins and integrations
Check which OME plugins you use: Power Manager (rack power/thermal, C07), Services (SupportAssist case creation), and the APEX AIOps connection (C08). Record the decision for each.

## Verify
- [ ] All GPU nodes are discovered and grouped.
- [ ] A firmware compliance report against the validated matrix exists.
- [ ] A non-compliant node is detected and fixed (by OME job or Ansible).
- [ ] Template drift is detected.
- [ ] A test alert reaches its destination.

## Record for the standards
`PLT-03` driver/firmware matrix and how compliance is reported. `OPS-02` infrastructure management tooling. `CMP-09` configuration baseline. `PLT-06` patch/upgrade policy and windows. `OPS-06` vendor support model (SupportAssist).

## Cleanup
Delete the test baseline, template and discovery job if the appliance is shared.
