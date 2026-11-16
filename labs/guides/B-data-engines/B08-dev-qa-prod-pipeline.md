# B08 - Deploy an AIDP pipeline dev → QA → prod

| Tier | Time | Domains | Prerequisites |
|---|---|---|---|
| SIM (Spark + Iceberg + Trino + S3 stand-ins) / DEMO / HW (Dell Data Processing and Data Analytics Engines) | 3 h | PLT, ING, DAT, LAK, SEC | [B02](B02-iceberg-lakehouse.md) (`iceberg.curated.orders` exists), [B03](B03-lakehouse-governance.md), [B04](B04-data-processing-spark.md); `make up PROFILES="core spark"` |

This lab takes the [B04](B04-data-processing-spark.md) orders pipeline (raw → cleaned "silver" → aggregated "gold", with a data-quality gate) and deploys it to three separate environments. The same Git commit is promoted from dev to QA to prod. Gates decide whether it may move on, and every deployment leaves a release record as evidence.

This is a **data pipeline**. For promoting a **model** through the same stages, see [D07](../D-ai-software/D07-mlops-pipeline.md); Step 13 shows how to chain the two.

## Prerequisites
- The SIM stack from [L01](../00-foundations/L01-lab-environment.md) with the `core` and `spark` profiles.
- `iceberg.curated.orders` from B02. It is the "operational source" that feeds all three environments.
- The L01 Python virtual environment (`~/.venvs/aif`).
- A Git clone of this repo in which you can create branches and commits.

## Steps

### Step 1 - Understand the design
Each environment gets its own storage, its own catalog schemas, its own service identity and its own data:

| | dev | QA | prod |
|---|---|---|---|
| Storage (ObjectScale bucket or PowerScale S3 path) | `aidp-dev` | `aidp-qa` | `aidp-prod` |
| Iceberg schemas | `dev_raw`, `dev_curated`, `dev_consumption`, `dev_meta` | `qa_*` | `prod_*` |
| Service account (Trino user + S3 identity) | `svc-dev` | `svc-qa` | `svc-prod` |
| Input data | 5% sample plus injected duplicates and bad rows | full volume, `customer_id` pseudonymised | full volume |
| Quarantine threshold / minimum rows | 5% / 100 | 1% / 10 000 | 1% / 10 000 |
| Can be deployed | from any commit, even uncommitted work | only a commit that **passed dev** | only a commit that **passed QA**, **approved by someone other than its author** |

Promotion rules that `pipeline.py` enforces:
1. **Build once, promote the same commit.** SQL and code are identical in every environment. Everything that differs lives in [environments.yaml](../../pipeline/environments.yaml).
2. **No skipping.** A commit enters QA only after a passed dev release, and prod only after a passed QA release.
3. **Four-eyes approval for prod.** The approver must not be the commit's author.
4. **Automatic restore on failure.** Before each deploy, the current Iceberg snapshot of every output table is recorded. If a transform or a data-quality check fails, the tables are rolled back to those snapshots, so consumers never see bad data.
5. **Versioned, immutable, additive schema migrations.** `migrations/V###__*.sql` files are applied once per environment and tracked in `<env>_meta.schema_migrations`. Editing a migration that was already applied is refused. Changes only add columns or tables, so rolling back to an older release stays safe.
6. **Every deploy writes a release record** to `s3://aidp-releases/<env>/`: commit, approver, migrations applied, input and output snapshot IDs, data-quality results, row counts.

**SIM vs. Dell AIDP.** The SIM uses one Spark, one Trino and one Iceberg catalog for all three environments and separates them by schema prefix, bucket and identity (logical separation). On the Dell platform you would normally go further, at least for prod: a separate ObjectScale namespace or PowerScale access zone, and a separate Data Analytics Engine catalog or cluster. Record which option you choose under `PLT-09`.

### Step 2 - Look at the repository layout
```
labs/pipeline/
├── environments.yaml            # promotion order and per-environment settings
├── migrations/V001__create_tables.sql   # Trino DDL, ${env}/${bucket} placeholders
├── transforms/10_silver.sql     # Spark SQL: dedupe, validate, quarantine, MERGE
├── transforms/20_gold.sql       # Spark SQL: daily revenue
├── dq.sql                       # Trino data-quality gate, thresholds from environments.yaml
├── changes/                     # a feature change used in Step 9
├── ci/github-actions.yml        # example CI/CD workflow (Step 12)
└── pipeline.py                  # seed | deploy | status | rollback | destroy
```
Transforms run on Spark (Data Processing Engine), migrations and checks run on Trino (Data Analytics Engine), and both read and write the same Iceberg tables on S3.

### Step 3 - Prepare the environments
The service identities are already in the lab config: `svc-dev`, `svc-qa` and `svc-prod` in `labs/env/seaweedfs/s3.json` (each may only use its own bucket), and matching rules in `labs/env/trino/governance/rules.json` (each may only use its own `<env>_*` schemas; `fin` and `ana` may read `prod_consumption` only). Load them and start Trino with the governance rules:
```bash
cd labs/env
make up PROFILES="core spark"
docker compose --profile core restart s3
docker compose -f docker-compose.yml -f docker-compose.governance.yml --profile core up -d trino
. ~/.venvs/aif/bin/activate && pip install trino boto3 pyyaml
cd ../pipeline
docker compose -f ../env/docker-compose.yml --profile core exec -T trino trino --execute "SELECT count(*) FROM iceberg.curated.orders"   # must be > 10000 (B02)
```

### Step 4 - Deploy to dev
Load dev's input data, then deploy:
```bash
python pipeline.py seed --env dev
python pipeline.py deploy --env dev
```
Expected (about 15 s per deploy on the SIM; the check order may differ):
```
migrations: V001__create_tables.sql
dev_raw.orders_events: 808 rows (sample)
deploying 4a986a0467c7 to dev as svc-dev
migrations: none pending
transforms: ok
  [PASS] silver has at least 100 rows
  [PASS] silver has no duplicate order_id
  [PASS] silver amounts positive
  [PASS] gold reconciles to silver
  [PASS] quarantine <= 5.0% of silver
release record: s3://aidp-releases/dev/2026-11-16T17:55:44.512301+00:00-4a986a0467c7.json  status=passed
```
Your commit ID differs. If you edit anything under `labs/pipeline/` and deploy without committing, the release is recorded as `<commit>-dirty`. Dev accepts that; QA and prod refuse it.

Check what dev produced:
```bash
docker compose -f ../env/docker-compose.yml --profile core exec -T trino trino --user svc-dev --execute "
SELECT reason, count(*) FROM iceberg.dev_curated.orders_quarantine GROUP BY reason;
SELECT count(*) FROM iceberg.dev_curated.orders_clean"
```
You should see one row each for `non-positive amount`, `future date` and `bad status`. The injected late updates are merged, not duplicated.

### Step 5 - Promote the same commit to QA
```bash
python pipeline.py seed --env qa       # 14637 rows (masked), from the operational source
python pipeline.py deploy --env qa
```
QA runs the identical SQL against full-volume, pseudonymised data with stricter thresholds. If you run `deploy --env qa` for a commit that has not passed dev, it stops with:
```
REFUSED: commit <sha> has no passed release in dev; promote through dev first.
```

### Step 6 - Promote to prod with approval
```bash
python pipeline.py seed --env prod
python pipeline.py deploy --env prod
#  REFUSED: prod needs --approved-by (the reviewer who approved the release).
python pipeline.py deploy --env prod --approved-by "$(git log -1 --format=%an)"
#  REFUSED: <author> wrote commit <sha>; a different person must approve prod.
python pipeline.py deploy --env prod --approved-by qa-lead@example.com
#  ... status=passed
python pipeline.py status
```
`status` shows the last three releases per environment, with the same commit in all three and the approver on the prod line.

In the lab, `seed --env prod` stands in for production ingestion (CDC or batch landing from the source systems). In a real platform prod data arrives through its own ingestion pipeline, not from a seed command.

### Step 7 - Check the consumers' view
`fin` (a business consumer) may read prod gold data but not silver, and may not change anything:
```bash
T="docker compose -f ../env/docker-compose.yml --profile core exec -T trino trino --user fin --execute"
$T "SELECT count(*) FROM iceberg.prod_consumption.daily_revenue"   # allowed
$T "SELECT count(*) FROM iceberg.prod_curated.orders_clean"        # Access Denied
$T "DELETE FROM iceberg.prod_consumption.daily_revenue"            # Access Denied
```

### Step 8 - Prove the environments are isolated
```bash
cd ../env
S3_USER=svc-dev bin/s3 s3 ls s3://aidp-dev/        # allowed
S3_USER=svc-dev bin/s3 s3 ls s3://aidp-prod/       # AccessDenied
echo x | S3_USER=svc-qa bin/s3 s3 cp - s3://aidp-prod/attack.txt   # AccessDenied
docker compose --profile core exec -T trino trino --user svc-dev --execute "SELECT count(*) FROM iceberg.prod_curated.orders_clean"    # Access Denied
docker compose --profile core exec -T trino trino --user svc-qa  --execute "DELETE FROM iceberg.prod_consumption.daily_revenue"      # Access Denied
# Spark running with dev's credentials cannot write prod data files:
bin/spark-sql --conf spark.sql.catalog.lake.s3.access-key-id=svc-dev --conf spark.sql.catalog.lake.s3.secret-access-key=svc-dev-secret \
  -e "INSERT INTO prod_raw.orders_events VALUES (999999999, 1, 1.0, current_date(), 'O', current_timestamp())" 2>&1 | grep -m1 -o "Access Denied.*Status Code: 403"
cd ../pipeline
```
**SIM limitation:** the lab's Trino has no authentication (see [E01](../E-operations/E01-zero-trust-baseline.md)), so anyone can claim to be `svc-prod`. On the real platform, each service account authenticates to the Data Analytics Engine with OAuth2/JWT or a certificate from your identity provider, over TLS. Also, the SIM passes the Spark S3 secret on the command line, where `ps` can see it; real jobs get it from the secrets manager.

### Step 9 - Ship a change through all three environments
Add a new gold table, `customer_ltv` (lifetime value per customer). It needs one migration and one transform:
```bash
git switch -c feature/customer-ltv
cp changes/V002__customer_ltv.sql migrations/
cp changes/30_customer_ltv.sql transforms/
git add migrations transforms && git commit -m "Add customer_ltv gold table"
python pipeline.py deploy --env dev
#  migrations: V002__customer_ltv.sql ... status=passed
python pipeline.py deploy --env prod --approved-by qa-lead@example.com
#  REFUSED: commit <new sha> has no passed release in qa; promote through qa first.
```
Now let QA catch bad data. Add 300 rows with a negative amount (about 2% of QA's volume, above its 1% threshold):
```bash
python pipeline.py seed --env qa --inject-bad 300
python pipeline.py deploy --env qa
```
Expected:
```
  [FAIL] quarantine <= 1.0% of silver
gate failed: restoring qa outputs to their pre-deploy snapshots
  restored qa_consumption.customer_ltv -> ...
  restored qa_consumption.daily_revenue -> ...
  restored qa_curated.orders_clean -> ...
  restored qa_curated.orders_quarantine -> ...
release record: s3://aidp-releases/qa/...  status=failed
```
The command exits with status 1, so a CI job stops here. QA's tables still hold the previous good release. Prod is untouched, and the new commit still cannot reach it. Fix the input and try again:
```bash
python pipeline.py seed --env qa
python pipeline.py deploy --env qa
python pipeline.py deploy --env prod --approved-by qa-lead@example.com
```

### Step 10 - Roll prod back
Suppose a consumer reports a problem with the new release:
```bash
python pipeline.py rollback --env prod --approved-by qa-lead@example.com
```
Expected:
```
rolling prod back from <new sha> to <previous sha>
  restored prod_consumption.daily_revenue -> ...
  restored prod_curated.orders_clean -> ...
  restored prod_curated.orders_quarantine -> ...
  kept prod_consumption.customer_ltv: not part of <previous sha> (additive migration, unused by that release)
release record: s3://aidp-releases/prod/...  status=rolled-back
```
Iceberg rollback is a metadata operation, so it takes about a second however big the tables are. The new table stays, because migrations are additive. Then fix forward with a new commit that goes through dev and QA again.

### Step 11 - Capture the evidence
```bash
mkdir -p ../evidence/b08
python pipeline.py status | tee ../evidence/b08/status.txt
(cd .. && env/bin/s3 s3 cp s3://aidp-releases/ evidence/b08/releases/ --recursive >/dev/null)   # bin/s3 mounts the current directory
ls ../evidence/b08/releases/*/
docker compose -f ../env/docker-compose.yml --profile core exec -T trino trino --user svc-prod --execute "
SELECT * FROM iceberg.prod_meta.schema_migrations ORDER BY version;
SELECT made_current_at, snapshot_id, is_current_ancestor FROM iceberg.prod_consumption.\"daily_revenue\$history\" ORDER BY 1" | tee ../evidence/b08/prod-lineage.txt
```
Each release JSON connects the commit, the approver, the input snapshot of `prod_raw.orders_events`, the output snapshots and the DQ results. That is the lineage chain `DAT-07` asks about, at table level.

### Step 12 - Automate it with CI/CD
[ci/github-actions.yml](../../pipeline/ci/github-actions.yml) is an example workflow: on a push to `main`, run tests, deploy to dev, then QA, then wait for a required reviewer on the `production` environment before deploying to prod. It runs on one self-hosted runner per environment, and takes each environment's endpoints (`AIDP_TRINO_HOST`, `AIDP_TRINO_PORT`, `AIDP_S3_ENDPOINT`) service-account secret (`AIDP_SVC_<ENV>_SECRET`) and the release-record identity (`AIDP_S3_ACCESS_KEY`, `AIDP_S3_SECRET_KEY`) from GitHub Environment variables and secrets. **Not tested in this repo**; it is a starting point.

The same gates in other CI/CD tools:

| Need | GitHub Actions | GitLab CI | Azure DevOps | Jenkins |
|---|---|---|---|---|
| Stage order | `needs:` | `stages:` / `needs:` | stages with `dependsOn` | sequential `stage` blocks |
| Prod approval, not by the author | Environment required reviewers + "Prevent self-review" | protected environment + deployment approvals | Environment "Approvals and checks" | `input` step with `submitter` |
| Per-environment secrets | Environment secrets | protected/environment-scoped variables | variable groups linked to Key Vault | credentials per folder |
| One promotion at a time | `concurrency:` | `resource_group:` | exclusive lock check | `lock` (Lockable Resources plugin) |

Whatever tool you use, keep `pipeline.py`'s own checks too. They also stop a person who runs the deploy by hand.

### Step 13 - [DEMO] / [HW] Run it on the Dell AI Data Platform
**Not run here** (no Dell platform access). Dell product names and APIs below are unverified; check them against your release with your Dell team.

| SIM piece | On Dell AIDP | What to change |
|---|---|---|
| SeaweedFS buckets `aidp-dev/qa/prod` | ObjectScale buckets in separate namespaces, or PowerScale S3 buckets in separate access zones | `bucket` in `environments.yaml`; `AIDP_S3_ENDPOINT` per environment; bucket policies limiting each service account to its bucket |
| Trino with file-based rules | Data Analytics Engine (Starburst-based), with its access control | `AIDP_TRINO_HOST/PORT` per environment; TLS and OAuth2/JWT for service accounts (needs a small change to `connect()` in `pipeline.py`); recreate the rules from Step 3 as roles |
| Spark container (`bin/spark-sql`) | Data Processing Engine | Replace `run_spark()` with a job submission to the engine (its UI/API, or `spark-submit` to its Kubernetes endpoint) that passes the rendered SQL and the environment's credentials |
| Iceberg REST catalog | The catalog/metastore the engines share | Catalog name and warehouse per environment |
| Lab secrets file | Vault/CyberArk (`SEC-05`) | Inject `AIDP_SVC_<ENV>_SECRET` at runtime |

On HW, also record the runtime and node-hours of a prod run (`FIN-02`), and whether QA's volume and hardware are close enough to prod to make QA's timings meaningful.

### Step 14 - Chain the data pipeline to model promotion (optional)
To promote a model that is trained on this data:
1. After a passed QA data release, train and evaluate the model on `qa_consumption` tables. Record the release's commit and output snapshot IDs as MLflow run tags.
2. Promote the model with the gates in [D07](../D-ai-software/D07-mlops-pipeline.md).
3. In prod, deploy the data release first, then the model. The model's tags tell you which data release it needs, and the release records let you roll both back to a matching pair.

## Verify
- [ ] Dev, QA and prod each have their own bucket, schemas and service account, and Step 8's cross-environment attempts are all denied.
- [ ] The same commit has a `passed` release in dev, QA and prod. The prod release names an approver who is not the commit author.
- [ ] `deploy` refuses to skip an environment, refuses prod without approval or with self-approval, and refuses uncommitted changes outside dev.
- [ ] A failed QA gate exits non-zero and restores QA's tables. Prod is not changed.
- [ ] `rollback` restores prod to the previous release in seconds and writes a `rolled-back` record.
- [ ] Release records, migration history and snapshot history are saved in `labs/evidence/b08/`.

## Record for the standards
`PLT-09` number of environments and how they are separated (schema/bucket/identity vs. separate clusters). `ING-06` pipeline code in Git with CI/CD and automated tests. `ING-03` orchestration and CI/CD tool. `ING-07` schema changes: versioned, additive migrations. `DAT-08` per-environment DQ thresholds as promotion gates. `DAT-07` release records as table-level lineage. `DAT-11` the gold tables as a data contract with consumers. `LAK-05` layer model per environment. `LAK-09` consumer access to prod gold only. `SEC-05` per-environment service-account secrets. `PLT-05` whether promotion is GitOps-driven. `OPS-05` how a prod approval maps to your change process. `ING-09` who is alerted when a gate fails.

## Cleanup
```bash
for e in dev qa prod; do python pipeline.py destroy --env $e; done
git switch - && git branch -D feature/customer-ltv
```
