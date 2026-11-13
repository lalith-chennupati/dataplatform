# A02 - Multi-tenancy with access zones & quotas

| Tier | Time | Domains | Prerequisites |
|---|---|---|---|
| SIM (OneFS Simulator) / HW | 3 h | STO, SEC, FIN | A01 |

## Prerequisites
- An authentication source per tenant. The simplest lab setup is the OneFS **local** provider of each zone, which is created automatically. If you have a lab AD or LDAP, use it for one of the zones.
- Spare IPs on the external subnet for a per-tenant IP pool (optional but recommended).

## Steps

### Step 1 - Create two tenant zones
```bash
ssh root@$PS
isi zone zones create bu-finance  --path=/ifs/bu-finance  --create-path
isi zone zones create bu-research --path=/ifs/bu-research --create-path
isi zone zones list -v | egrep "Name|Path|Auth Providers"
```

### Step 2 - Give each zone its own network entry point
```bash
isi network pools create groupnet0.subnet0.finance  --ranges=10.10.10.61-10.10.10.63 --ifaces=1-3:ext-1 --access-zone=bu-finance  --sc-dns-zone=finance.ps-lab.local
isi network pools create groupnet0.subnet0.research --ranges=10.10.10.71-10.10.10.73 --ifaces=1-3:ext-1 --access-zone=bu-research --sc-dns-zone=research.ps-lab.local
```
Interface names vary on the simulator; check `isi network interfaces list` and adjust `--ifaces`.

### Step 3 - Tenant users and groups (local provider)
```bash
isi auth groups create fin-data-scientists --zone=bu-finance  --provider=local
isi auth users  create alice --zone=bu-finance  --provider=local --enabled=yes --password='Lab#2026' --primary-group=fin-data-scientists
isi auth groups create res-data-scientists --zone=bu-research --provider=local
isi auth users  create bob   --zone=bu-research --provider=local --enabled=yes --password='Lab#2026' --primary-group=res-data-scientists
```
Optional with AD: `isi auth ads create lab.local administrator` and then `isi zone zones modify bu-research --add-auth-providers=lsa-activedirectory-provider:LAB.LOCAL`.

### Step 4 - Exports per zone
```bash
mkdir -p /ifs/bu-finance/datasets /ifs/bu-research/datasets
isi nfs exports create /ifs/bu-finance/datasets  --zone=bu-finance  --clients=10.10.10.0/24
isi nfs exports create /ifs/bu-research/datasets --zone=bu-research --clients=10.10.10.0/24
isi smb shares create datasets /ifs/bu-finance/datasets  --zone=bu-finance
isi smb shares create datasets /ifs/bu-research/datasets --zone=bu-research
```

### Step 5 - Prove isolation
From the client:
```bash
sudo mount -t nfs finance.ps-lab.local:/ifs/bu-finance/datasets /mnt/fin        # works
sudo mount -t nfs finance.ps-lab.local:/ifs/bu-research/datasets /mnt/x          # expect: access denied / no such export
smbclient //finance.ps-lab.local/datasets -U bob%'Lab#2026' -c ls                # expect: logon failure (bob is not in bu-finance)
smbclient //finance.ps-lab.local/datasets -U alice%'Lab#2026' -c ls              # works
```

### Step 6 - Quotas (SmartQuotas)
```bash
isi quota quotas create /ifs/bu-finance directory --zone=bu-finance \
  --advisory-threshold=1G --soft-threshold=2G --soft-grace=1D --hard-threshold=3G --container=yes
isi quota quotas create /ifs/bu-research directory --zone=bu-research --hard-threshold=2G --container=yes
isi quota quotas list
```
`--container=yes` makes clients see the hard limit as the share size.

### Step 7 - Exceed the quota
From the client (finance mount):
```bash
dd if=/dev/zero of=/mnt/fin/fill.bin bs=1M count=2200 status=progress   # passes soft, stays under hard
dd if=/dev/zero of=/mnt/fin/fill2.bin bs=1M count=1500                    # expect: Disk quota exceeded
df -h /mnt/fin                                                            # shows 3.0G size
```
On the cluster: `isi quota quotas view /ifs/bu-finance directory --zone=bu-finance` shows usage over soft. `isi event events list` shows the quota event if notifications are configured.

### Step 8 - Delegate zone administration (RBAC)
```bash
isi auth roles create FinanceZoneAdmin --zone=bu-finance --description="Finance storage admin"
isi auth roles modify FinanceZoneAdmin --zone=bu-finance --add-priv-write=ISI_PRIV_NFS --add-priv-write=ISI_PRIV_SMB --add-priv-read=ISI_PRIV_QUOTA --add-user=alice
isi auth roles view FinanceZoneAdmin --zone=bu-finance
```
Privilege names and flags vary by OneFS release. Use `isi auth privileges list` and `isi auth roles modify --help`. Log in to the WebUI as `alice` with the zone-specific login and confirm she only sees `bu-finance`.

### Step 9 - Clean up the fill files
`rm /mnt/fin/fill*.bin`

## Verify
- [ ] Neither tenant can mount, list or log in to the other's zone.
- [ ] Soft and hard quota behaviour was observed. `df` shows the container quota.
- [ ] A zone-scoped admin role works and cannot see the other zone.

## Record for the standards
- `STO-06` tenant isolation model (zone per BU / per project). `STO-07` quota standard: default thresholds, grace and container settings.
- `SEC-02` authorisation model. `FIN-03`: the zone/quota naming carries the cost-centre tag.

## Cleanup
```bash
ssh root@$PS 'isi zone zones delete bu-research --force; isi zone zones delete bu-finance --force'
```
Deleting a zone does not delete its data. Remove `/ifs/bu-*` explicitly if you want it gone.
