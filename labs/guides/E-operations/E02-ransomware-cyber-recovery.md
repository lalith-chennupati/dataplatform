# E02 - Ransomware and cyber recovery

| Tier | Time | Domains | Prerequisites |
|---|---|---|---|
| SIM (versioned S3) / DEMO (OneFS Simulator: snapshots, SmartLock) / HW (Ransomware Defender / Superna, PowerProtect Cyber Recovery vault) | 3 h | BCR, SEC, STO | L01 core profile; A03 for the OneFS snapshot and SmartLock steps. |

A ransomware attack on an AI Factory hits training data, model weights and vector indexes at once. This lab simulates mass encryption of a share, detects it from the file contents, restores clean versions and times the recovery. The detection rule (entropy) is deliberately simple; real products also use access patterns, user behaviour and canary files. **Untested here:** PowerScale ransomware detection and PowerProtect Cyber Recovery (no OneFS or vault on my VM).

## Steps

### Step 1 - [SIM] Seed a protected share
```bash
cd labs/env && PY=~/.venvs/aif/bin/python
$PY ops/ransomware_sim.py seed
$PY ops/ransomware_sim.py detect
```
Expected: `seeded 200 documents in s3://e02-share (versioning enabled)` and `0/200 objects have entropy > 7.5 bits/byte -> ok`. Versioning is the SIM stand-in for snapshots: every overwrite keeps the old version.

### Step 2 - [SIM] Attack
```bash
$PY ops/ransomware_sim.py attack
$PY ops/ransomware_sim.py detect
```
Expected: about 200 objects overwritten in under a second (I measured 541 writes/s), then `200/200 objects ... ALERT: likely encryption`. Note how fast a single compromised credential destroys a share: detection must be automatic.

### Step 3 - [SIM] Recover and verify
```bash
$PY ops/ransomware_sim.py recover
$PY ops/ransomware_sim.py verify
$PY ops/ransomware_sim.py detect
```
Expected: `restored 200/200 objects from earlier versions in ~1.3s`, `200/200 objects match their seed hash`, detect back to `ok`. Record the restore time as the RTO for this share size and scale it to your real share sizes (an object count and a TB figure).

### Step 4 - [SIM] Why the credential matters
The attack used the lab admin key, which can also delete old versions. Repeat the attack with a key that has `s3:PutObject` but not `s3:DeleteObjectVersion` and confirm the attacker cannot remove the clean versions; then look at the `locked-models` bucket from A09, whose COMPLIANCE-mode object lock even the admin cannot bypass. Standard: backup copies must be immutable to the credentials that can write production data.

### Step 5 - [DEMO] OneFS snapshots and SmartLock
On the OneFS Simulator: snapshot schedule on `/ifs/bu-finance` every hour (A03), then overwrite files in the share from a client, and restore from `/ifs/bu-finance/.snapshot/<name>/` or with `isi snapshot snapshots restore`. Create a SmartLock enterprise directory with a retention period and confirm `rm` fails before expiry. Record whether snapshots can be deleted by the storage admin role (they can, unless snapshot locking is enabled on your release).

### Step 6 - [HW] Detection and the isolated vault
- PowerScale ransomware detection (Ransomware Defender / Superna Eyeglass or the OneFS-native capability on your release): enable it on the share, rerun an attack from an SMB/NFS client and record time-to-detect and whether the user was locked out automatically.
- PowerProtect Cyber Recovery: copy the protected data into the vault over the air-gap link, lock it with retention, run CyberSense analytics, then perform a recovery test into a clean-room network. Record vault sync interval (RPO) and time to restore a 1 TB dataset (RTO).

## Verify
- [ ] Attack detected by the automatic check, not by a user.
- [ ] All objects restored and hash-verified; RTO recorded.
- [ ] Backup copies immutable to the production write credential.
- [ ] *(DEMO/HW)* Snapshot restore and SmartLock retention proven; vault recovery timed.

## Record for the standards
`BCR-04` isolated, immutable cyber-recovery vault. `BCR-02` RPO/RTO per asset. `BCR-06` recovery test frequency. `SEC-10` detection events sent to the SIEM. `STO-08` snapshot RPO/RTO per data class. `STO-09` immutability / WORM.

## Cleanup
`labs/env/bin/s3 s3 rb --force s3://e02-share` (versioned buckets also need old versions removed: `bin/s3 s3api delete-bucket` fails until `list-object-versions` is empty); `rm labs/env/ops/.e02-seed.json`.
