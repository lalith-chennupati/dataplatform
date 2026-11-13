# A04 - Tiering hot -> cold

| Tier | Time | Domains | Prerequisites |
|---|---|---|---|
| SIM (partial) / HW | 3 h | STO, FIN | A01; an S3 endpoint for CloudPools (ObjectScale, or the lab S3 from L01) |

The simulator has a single node type, so it cannot show a real flash -> HDD move. You can still build and run the policies. On hardware with two node pools (e.g. F-series + A-series) the data really moves.

## Steps

### Step 1 - Inspect tiers and pools
```bash
ssh root@$PS
isi storagepool nodepools list
isi storagepool tiers list
isi filepool default-policy view
```
On hardware, create a tier per performance class:
```bash
isi storagepool tiers create hot  --children=<f-series-nodepool>
isi storagepool tiers create cold --children=<a-series-nodepool>
```

### Step 2 - File pool policy for old checkpoints
```bash
isi filepool policies create ckpt-to-cold \
  --description="Checkpoints not changed for 30 days go to cold" \
  --begin-filter --path=/ifs/data/ai/checkpoints --and --changed-time=30D --operator=gt --end-filter \
  --data-storage-target=cold --snapshot-storage-target=cold
isi filepool policies list
```
In SIM, set `--data-storage-target` to the only node pool and lower the age to `--changed-time=1m` so the policy matches something.

### Step 3 - Run SmartPools and check placement
```bash
touch -d '40 days ago' /ifs/data/ai/checkpoints/*        # make files "old"
isi job jobs start SmartPools
isi job jobs list
isi get -D /ifs/data/ai/checkpoints/<file> | egrep "Disk pools|Storage pool"
```

### Step 4 - CloudPools to S3 (ObjectScale)
CloudPools needs a licence and a reachable S3 endpoint (`isi license list | grep -i cloud`). Use account type `ecs` for ObjectScale/ECS, or `amazons3` for other S3-compatible targets.
```bash
isi cloud accounts create --name=objectscale --type=ecs --uri=https://$OBJ_HOST:9021 --account-username=<s3-user> --key=<secret>
isi cloud pools create --name=archive --type=ecs --accounts=objectscale
isi filepool policies create stale-raw-to-cloud \
  --begin-filter --path=/ifs/data/ai/raw --and --accessed-time=90D --operator=gt --end-filter \
  --cloud-pool=archive --cloud-compression-enabled=yes --cloud-encryption-enabled=yes
isi job jobs start SmartPools
isi cloud jobs list
```
Archived files become *SmartLink* stubs. Reading one recalls the data inline. A permanent recall: `isi cloud recall /ifs/data/ai/raw/<file>`.

### Step 5 - Measure capacity and recall latency
1. `isi storagepool list` / `isi statistics drive` before and after.
2. `time cat /ifs/data/ai/raw/<stubbed-file> > /dev/null` (the first read recalls the data).

## Verify
- [ ] The policy matches the intended files (`isi filepool apply --path=<file> -n -v` dry-run shows the match).
- [ ] SmartPools job completed. On HW, placement changed to the target tier.
- [ ] CloudPools stubbing and recall work, or the reason they were not tested is recorded.

## Record for the standards
`STO-05` tier definitions and movement rules. `FIN-05` capacity triggers. Record the recall latency as an SLO caveat for archived data.

## Cleanup
`isi filepool policies delete ckpt-to-cold --force; isi filepool policies delete stale-raw-to-cloud --force`
