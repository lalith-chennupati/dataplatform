# A03 - Snapshots, replication & WORM

| Tier | Time | Domains | Prerequisites |
|---|---|---|---|
| SIM (two OneFS Simulator clusters) / HW | 3 h | STO, BCR | A01; second cluster `ps-dr` from L01 Step 6.7 |

## Steps

### Step 1 - Seed a training dataset
```bash
ssh root@$PS
mkdir -p /ifs/data/ai/train-v1
for i in $(seq 1 200); do head -c 1048576 /dev/urandom > /ifs/data/ai/train-v1/shard-$i.bin; done
du -sh /ifs/data/ai/train-v1
```

### Step 2 - Snapshot schedule (SnapshotIQ)
```bash
isi snapshot schedules create ai-hourly /ifs/data/ai "ai_%Y-%m-%d_%H-%M" "every 1 hours" --duration=2D
isi snapshot snapshots create /ifs/data/ai --name=before-change --expires=1D
isi snapshot snapshots list
```

### Step 3 - Simulate damage and restore
```bash
rm -f /ifs/data/ai/train-v1/shard-1*.bin                     # "accidental" delete
ls /ifs/data/ai/.snapshot/before-change/train-v1 | wc -l     # 200 files still in the snapshot
cp -p /ifs/data/ai/.snapshot/before-change/train-v1/shard-1*.bin /ifs/data/ai/train-v1/   # file-level restore
ls /ifs/data/ai/train-v1 | wc -l                              # back to 200
```
Directory-level revert (rolls the whole path back): create a SnapRevert domain, then run the job:
```bash
isi job jobs start DomainMark --root=/ifs/data/ai --dm-type=SnapRevert
isi job jobs start SnapRevert --snapid=$(isi snapshot snapshots view before-change | awk '/^ *ID/ {print $2}')
```

### Step 4 - Replicate to the DR cluster (SyncIQ)
On `ps-dr` (`$PSDR`), make sure SyncIQ is enabled: `isi services isi_migrate enable` / `isi sync settings modify --service=on`.
On the source:
```bash
isi sync settings modify --service=on
isi sync policies create ai-to-dr sync /ifs/data/ai $PSDR /ifs/data/ai-replica --schedule="every 1 hours"
isi sync jobs start ai-to-dr
isi sync jobs list ; isi sync reports list --policy-name=ai-to-dr
```
Expected: the report shows the job finished and the file count matches.

### Step 5 - Measure RPO
1. Write a timestamp file: `date > /ifs/data/ai/rpo-marker.txt`.
2. Run `isi sync jobs start ai-to-dr` and note the start and finish times.
3. On `ps-dr`: `cat /ifs/data/ai-replica/rpo-marker.txt`.
4. RPO = schedule interval + job duration. Record both. Change the policy to `--schedule=when-source-modified` and measure again.

### Step 6 - WORM for golden training sets (SmartLock)
```bash
isi worm domains create /ifs/data/golden --mode=enterprise --default-retention=1D --autocommit-offset=1m --create-path
cp /ifs/data/ai/train-v1/shard-2.bin /ifs/data/golden/
sleep 70                                      # wait for autocommit
rm /ifs/data/golden/shard-2.bin               # expect: Read-only file system / Operation not permitted
isi worm files view /ifs/data/golden/shard-2.bin
```
Compliance mode (SEC 17a-4 style) needs a cluster installed in compliance mode. The simulator uses enterprise mode.

## Verify
- [ ] A file-level restore from a snapshot works and the restore time is recorded.
- [ ] The SyncIQ replica is consistent (same file count and checksums for a sample).
- [ ] The RPO for scheduled and change-triggered replication is measured.
- [ ] Deleting a committed WORM file is refused.

## Record for the standards
`STO-08` snapshot/replication RPO/RTO per data class. `STO-09` immutability rules. `BCR-02` RPO/RTO tiers. `BCR-01` protection scope.

## Cleanup
```bash
isi snapshot schedules delete ai-hourly --force
isi sync policies delete ai-to-dr --force
```
The WORM domain cannot be deleted until retention expires (1 day in this lab).
