# E03 - Backup and restore of AI assets

| Tier | Time | Domains | Prerequisites |
|---|---|---|---|
| SIM (lab stack) / HW (PowerProtect Data Manager with Kubernetes protection, PowerScale or ObjectScale target) | 3 h | BCR, MLO, RAG | D03 index `docs-chunks`, D04 checkpoints and MLflow model `d04-lora-adapter`, B02 Iceberg catalog. |

An AI application is more than its model file: the vector index, the registry database, the lakehouse catalog and the checkpoints all have to come back together and consistent. This lab backs them up to a vault bucket with a checksummed manifest, destroys the RAG index and the registry, restores them and proves the application works again. **Untested here:** PowerProtect Data Manager (no PPDM on my VM).

## Steps

### Step 1 - [SIM] Inventory what must be protected
| Asset | Where in the lab | Production equivalent |
|---|---|---|
| Vector / keyword index | Elasticsearch `docs-chunks` | Data Search Engine index, or rebuild from source + embedding model version |
| Model registry | MLflow DB in the `mlflow` container | registry DB (PostgreSQL) |
| Lakehouse catalog | `iceberg.db` in `iceberg-rest` | Data Analytics Engine / Iceberg catalog |
| Checkpoints | `s3://checkpoints` | PowerScale / ObjectScale path |
| Iceberg data, model artifacts | `s3://warehouse`, `s3://model-registry` | protected by replication + object lock (A03, A09), not copied every night |

Decide for each: back up, or rebuild from source (and how long a rebuild takes). Re-embedding 10 M chunks can take longer than the RTO allows.

### Step 2 - [SIM] Back up
```bash
cd labs/env && PY=~/.venvs/aif/bin/python
$PY ops/backup_restore.py backup
$PY ops/backup_restore.py list
```
Expected: `backup <timestamp>: 12 index docs, mlflow ... B, catalog ... B, 7 checkpoints in ~1s` and `s3://vault/<timestamp>/manifest.json` holding a sha256 per item. The index backup includes the stored vectors, so restore does not need the embedding model. MLflow and the Iceberg REST catalog are stopped for a few seconds while their SQLite files are copied, so the copy is consistent; production uses the database's own online backup (`pg_dump`, PITR) instead.

### Step 3 - [SIM] Disaster: delete the D03 index and break the registry
```bash
curl -XDELETE localhost:9200/docs-chunks
$PY search/rag_search.py search "hotel spend" --groups finance,all-staff    # expect: index_not_found_exception
```

### Step 4 - [SIM] Restore and verify
```bash
TS=$($PY ops/backup_restore.py list | tail -1)
time $PY ops/backup_restore.py restore $TS --only es,mlflow
$PY search/rag_search.py search "hotel spend" --groups finance,all-staff    # fin-001 Travel expense policy first
curl -s "localhost:5000/api/2.0/mlflow/registered-models/get?name=d04-lora-adapter" | head -c 300
```
Expected: `es: restored 12 docs`, `mlflow: restored /mlflow/mlflow.db with mlflow stopped`, total about 10 s, and the same top hit as before the deletion. Restore verifies each item's checksum first and refuses a tampered backup (try editing one object in `s3://vault` and rerun).

Rerun D03 Step 5 (restricted documents) after the restore: ACL fields must come back exactly, or the restore has created a data leak.

### Step 5 - [SIM] Consistency check
Register a new model version after the backup, then restore only the registry: the new version disappears from MLflow but its artifacts are still in `s3://model-registry`. Write down the rule your standard needs: restore registry and artifacts to the same point in time, or keep artifacts immutable and reconcile orphans afterwards.

### Step 6 - [HW] PowerProtect Data Manager for Kubernetes
Register the cluster as an asset source in PPDM, create a protection policy for the D03 namespace (namespaces, PVCs, CRDs) with a PowerProtect DD or object target, run it, `kubectl delete ns <d03-namespace>`, and restore to the original and to a new namespace. Record backup window, restore time and whether PVC data on PowerScale CSI volumes came back with the right ownership.

## Verify
- [ ] Every asset in Step 1 has a backup or rebuild decision and an owner.
- [ ] Index and registry restored; search and model lookups work; ACLs intact.
- [ ] Restore time recorded against the RTO.
- [ ] *(HW)* PPDM namespace restore proven.

## Record for the standards
`BCR-01` AI assets that must be backed up. `BCR-02` RPO/RTO per AI service. `BCR-05` standard backup software. `BCR-06` restore test frequency. `MLO-12` model versioning and rollback. `RAG-07` index freshness after restore.

## Cleanup
`labs/env/bin/s3 s3 rm --recursive s3://vault/` (keep one backup if E04 or X01 is next).
