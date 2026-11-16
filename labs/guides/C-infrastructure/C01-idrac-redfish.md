# C01 - PowerEdge lifecycle with iDRAC & Redfish

| Tier | Time | Domains | Prerequisites |
|---|---|---|---|
| SIM (DMTF Redfish Mockup Server) / HW (iDRAC9 or newer) | 3 h | CMP, SEC, PLT | L01 with the `infra` profile |

SIM: `export IDRAC=localhost:8000 AUTH=""`. The mockup serves a generic Redfish system (`/redfish/v1/Systems/437XR1138R2`) without authentication. It accepts PATCH and POST but does not apply them, and it has no Dell OEM extensions.
HW: `export IDRAC=<idrac-ip> AUTH="-k -u root:<password>"`. Use HTTPS, and the Dell system ID `System.Embedded.1`.
```bash
cd labs/env && make up PROFILES="core infra"
R() { curl -s $AUTH "${PROTO:-http}://$IDRAC/redfish/v1$1" "${@:2}"; }        # HW: export PROTO=https
SYS=$(R /Systems | python3 -c "import sys,json;print(json.load(sys.stdin)['Members'][0]['@odata.id'].split('/')[-1])"); echo $SYS
```

## Steps

### Step 1 - Walk the service root
```bash
R / | python3 -m json.tool | grep '@odata.id'      # Systems, Chassis, Managers, UpdateService, EventService, TelemetryService, AccountService
R /Managers | python3 -m json.tool                 # HW: iDRAC.Embedded.1
```

### Step 2 - Hardware inventory
```bash
R /Systems/$SYS | python3 -c "
import sys, json; d = json.load(sys.stdin)
print({k: d.get(k) for k in ['Manufacturer', 'Model', 'SerialNumber', 'PowerState', 'BiosVersion']})
print('CPU', d['ProcessorSummary']['Count'], 'x', d['ProcessorSummary']['Model'], '| RAM GiB', d['MemorySummary']['TotalSystemMemoryGiB'])"
R /Systems/$SYS/Processors | python3 -m json.tool | grep '@odata.id'
R /Systems/$SYS/EthernetInterfaces | python3 -m json.tool | grep '@odata.id'
```
[HW] GPUs show up as `Processors` with `ProcessorType: GPU`, and as PCIe devices under `/Chassis/System.Embedded.1/PCIeDevices`. List them:
```bash
for p in $(R /Systems/$SYS/Processors | python3 -c "import sys,json;[print(m['@odata.id']) for m in json.load(sys.stdin)['Members']]"); do
  curl -s $AUTH "$PROTO://$IDRAC$p" | python3 -c "import sys,json;d=json.load(sys.stdin);print(d.get('Id'), d.get('ProcessorType'), d.get('Model'))"; done
```
Save the inventory as JSON in the evidence folder. This is the asset record.

### Step 3 - Firmware inventory
```bash
for f in $(R /UpdateService/FirmwareInventory | python3 -c "import sys,json;[print(m['@odata.id']) for m in json.load(sys.stdin)['Members']]"); do
  curl -s $AUTH "${PROTO:-http}://$IDRAC$f" | python3 -c "import sys,json;d=json.load(sys.stdin);print(d.get('Name'), d.get('Version'))"; done
```
Compare the result with the validated driver/firmware matrix (C02).

### Step 4 - Update firmware (HW for real, SIM shows the API call)
```bash
R /UpdateService | python3 -m json.tool | grep -A3 SimpleUpdate
R /UpdateService/Actions/UpdateService.SimpleUpdate -X POST -H 'Content-Type: application/json' \
  -d '{"ImageURI": "http://repo.lab/firmware/BIOS_XXXX.EXE", "TransferProtocol": "HTTP", "@Redfish.OperationApplyTime": "OnReset"}'
```
[HW] The call returns a job (`Location: /redfish/v1/Managers/iDRAC.Embedded.1/Jobs/JID_...`). Poll the job until `JobState` is `Completed`. In production, use OME catalogs/baselines (C02) instead of one-off updates.

### Step 5 - Configuration as a template (BIOS + Server Configuration Profile)
```bash
R /Systems/$SYS/Bios | python3 -c "import sys,json;a=json.load(sys.stdin)['Attributes'];[print(k,'=',v) for k,v in sorted(a.items())[:15]]"
R /Systems/$SYS/Bios/Settings -X PATCH -H 'Content-Type: application/json' -d '{"Attributes": {"PowerProfile": "MaxPerf"}}' -w "%{http_code}\n"
```
[HW] Export the whole server configuration (BIOS, iDRAC, NIC, RAID) as a Server Configuration Profile from a "golden" node, then import it on a new node:
```bash
R /Managers/iDRAC.Embedded.1/Actions/Oem/EID_674_Manager.ExportSystemConfiguration -X POST -H 'Content-Type: application/json' \
  -d '{"ExportFormat": "JSON", "ShareParameters": {"Target": ["ALL"]}}' -D - | grep -i location
# poll the task, save the JSON as golden-xe9680.json, review it, then:
R /Managers/iDRAC.Embedded.1/Actions/Oem/EID_674_Manager.ImportSystemConfiguration -X POST -H 'Content-Type: application/json' \
  -d "{\"ImportBuffer\": $(python3 -c 'import json;print(json.dumps(open("golden-xe9680.json").read()))'), \"ShareParameters\": {\"Target\": [\"ALL\"]}, \"ShutdownType\": \"Graceful\"}"
```
Ansible equivalent: `dellemc.openmanage.idrac_server_config_profile` (`command: export` / `import`).

### Step 6 - Power and reset
```bash
R /Systems/$SYS | python3 -c "import sys,json;print(json.load(sys.stdin)['Actions'])"
R /Systems/$SYS/Actions/ComputerSystem.Reset -X POST -H 'Content-Type: application/json' -d '{"ResetType": "GracefulRestart"}' -w "%{http_code}\n"
```

### Step 7 - Events and telemetry streaming
```bash
R /EventService/Subscriptions -X POST -H 'Content-Type: application/json' \
  -d '{"Destination": "https://collector.lab:9000/events", "Protocol": "Redfish", "EventFormatType": "Event"}' -w "%{http_code}\n"
R /EventService/Subscriptions | python3 -m json.tool | grep -c '@odata.id'
R /TelemetryService | python3 -m json.tool | head -20
```
[HW] On iDRAC9 with the Datacenter licence, enable telemetry reports (e.g. `GPUStatistics`, `PowerStatistics`, `ThermalSensor`) and stream them with an SSE subscription (`/redfish/v1/SSE?$filter=EventFormatType eq MetricReport`), or point the open-source iDRAC Telemetry Reference Tools at Prometheus. C08 uses the result.

### Step 8 - Security baseline
```bash
R /Systems/$SYS/SecureBoot | python3 -m json.tool | grep SecureBootEnable
R /AccountService | python3 -m json.tool | egrep "MinPasswordLength|AccountLockoutThreshold"
```
[HW] Check and record each item:
1. Secure Boot enabled: `PATCH /Systems/System.Embedded.1/SecureBoot {"SecureBootEnable": true}` (applies on the next reboot).
2. Default `root/calvin` removed or changed. Local accounts limited. LDAP/AD for admins.
3. iDRAC on the isolated OOB management network only (NET-05). TLS certificate from your CA.
4. **System Lockdown mode**: `PATCH /Managers/iDRAC.Embedded.1/Attributes {"Attributes": {"Lockdown.1.SystemLockdown": "Enabled"}}`. After that, configuration and firmware changes are refused until lockdown is disabled.
5. Firmware signature verification and Silicon Root of Trust status (iDRAC Lifecycle log).

### Step 9 - Script it
Combine Steps 2, 3 and 8 into one script that prints a pass/fail line per baseline item for every node in an inventory file, and run it on a schedule. Ansible equivalent: `dellemc.openmanage.idrac_info`, `idrac_bios`, `idrac_attributes`, `redfish_info`.

## Verify
- [ ] The inventory and firmware lists come only from the API.
- [ ] A configuration template (BIOS/SCP) is exported and applied *(HW)*. In SIM, the API calls return 2xx.
- [ ] An event subscription exists.
- [ ] The security baseline checklist is recorded per node.

## Record for the standards
`SEC-12` hardware/firmware security baseline (Secure Boot, lockdown, accounts, certs). `CMP-09` node configuration baseline (SCP golden profile). `PLT-03` firmware matrix. `NET-05` OOB segmentation.

## Cleanup
SIM: `docker compose --profile infra restart redfish` resets the mockup. HW: delete the test event subscription and set lockdown back to its agreed state.
