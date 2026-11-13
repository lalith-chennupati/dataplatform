# A09 - ObjectScale S3 fundamentals

| Tier | Time | Domains | Prerequisites |
|---|---|---|---|
| DEMO (ObjectScale) / SIM (lab S3 stand-in) | 3 h | STO, SEC | L01 |

The same S3 API calls work against ObjectScale and the lab S3. Account / IAM administration differs:
- **ObjectScale**: accounts, IAM users, groups and policies are managed in the ObjectScale Portal or its IAM API.
- **SIM (SeaweedFS)**: identities and per-bucket actions are defined in `labs/env/seaweedfs/s3.json`.

Run the steps against ObjectScale if you can. On SIM, write down which steps the stand-in could not show.

## Prerequisites
- DEMO: an ObjectScale account, the S3 endpoint (`$OBJ`, e.g. `https://<objectscale>:9021`), and admin rights to create IAM users and policies.
- SIM: `make up` running. Use `bin/s3` (labadmin) and `S3_USER=finance bin/s3` / `S3_USER=research bin/s3`.

For DEMO, define a helper the same way:
```bash
s3() { aws --endpoint-url "$OBJ" --no-verify-ssl "$@"; }      # with AWS_ACCESS_KEY_ID/SECRET of the IAM user
```

## Steps

### Step 1 - [DEMO] Account, namespace and IAM users
In the ObjectScale Portal: create the account `ai-factory`, then IAM users `finance-svc` and `research-svc`, and generate access keys for both. Attach this policy to `finance-svc` (and the equivalent for research):
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {"Effect": "Allow", "Action": ["s3:ListBucket"], "Resource": ["arn:aws:s3:::bu-finance"]},
    {"Effect": "Allow", "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"], "Resource": ["arn:aws:s3:::bu-finance/*"]}
  ]
}
```
[SIM] This is already modelled in `seaweedfs/s3.json`: `finance` can only `Read/Write/List` `bu-finance`.

### Step 2 - Buckets per tenant
```bash
bin/s3 s3 ls                        # SIM: warehouse bu-finance bu-research model-registry checkpoints documents
# DEMO: s3 s3 mb s3://bu-finance ; s3 s3 mb s3://bu-research ; s3 s3 mb s3://model-registry
```

### Step 3 - Prove least privilege
```bash
cd labs/env && echo "q3 forecast" > forecast.csv
S3_USER=finance  bin/s3 s3 cp /work/forecast.csv s3://bu-finance/forecast.csv      # upload: ok
S3_USER=finance  bin/s3 s3 cp /work/forecast.csv s3://bu-research/forecast.csv     # AccessDenied
S3_USER=research bin/s3 s3 cp s3://bu-finance/forecast.csv -                       # AccessDenied
S3_USER=finance  bin/s3 s3 ls s3://bu-research/                                    # AccessDenied
```

### Step 4 - Versioning
```bash
bin/s3 s3api put-bucket-versioning --bucket model-registry --versioning-configuration Status=Enabled
bin/s3 s3api get-bucket-versioning --bucket model-registry               # "Status": "Enabled"
echo v1 > model.txt && bin/s3 s3 cp /work/model.txt s3://model-registry/llm/model.txt
echo v2 > model.txt && bin/s3 s3 cp /work/model.txt s3://model-registry/llm/model.txt
bin/s3 s3api list-object-versions --bucket model-registry --prefix llm/model.txt --query 'Versions[].{v:VersionId,latest:IsLatest}'
```
Expected: two versions. Fetch the old one with `s3api get-object --version-id <id> /work/old.txt`.

### Step 5 - Object lock (immutability)
```bash
bin/s3 s3api create-bucket --bucket locked-models --object-lock-enabled-for-bucket
bin/s3 s3api put-object-lock-configuration --bucket locked-models \
  --object-lock-configuration '{"ObjectLockEnabled":"Enabled","Rule":{"DefaultRetention":{"Mode":"GOVERNANCE","Days":1}}}'
bin/s3 s3 cp /work/model.txt s3://locked-models/golden/model.txt
VID=$(bin/s3 s3api list-object-versions --bucket locked-models --prefix golden/model.txt --query 'Versions[0].VersionId' --output text)
bin/s3 s3api delete-object --bucket locked-models --key golden/model.txt --version-id "$VID"      # expect AccessDenied (retention)
```
On ObjectScale, also try `COMPLIANCE` mode on a separate bucket: even the account admin cannot shorten the retention.
SIM note: SeaweedFS accepts object-lock configuration. Record whether the delete was refused, because enforcement depends on the stand-in's version.

### Step 6 - Lifecycle rules
```bash
cat > lifecycle.json <<'JSON'
{"Rules": [
  {"ID": "expire-temp-checkpoints", "Status": "Enabled", "Filter": {"Prefix": "tmp/"}, "Expiration": {"Days": 7}},
  {"ID": "noncurrent-cleanup", "Status": "Enabled", "Filter": {"Prefix": ""}, "NoncurrentVersionExpiration": {"NoncurrentDays": 30}}
]}
JSON
bin/s3 s3api put-bucket-lifecycle-configuration --bucket checkpoints --lifecycle-configuration file:///work/lifecycle.json
bin/s3 s3api get-bucket-lifecycle-configuration --bucket checkpoints
```

### Step 7 - Encryption and TLS
- [DEMO] Enable server-side encryption at the namespace/bucket level in ObjectScale, and confirm that `head-object` shows `ServerSideEncryption`. Confirm the endpoint presents a certificate from your CA: `openssl s_client -connect <host>:9021 </dev/null | openssl x509 -noout -issuer -subject`.
- [SIM] The lab S3 is plain HTTP. Note this as a SIM limitation; E01 covers TLS.

### Step 8 - Bucket policy (resource-based)
[DEMO] Add a bucket policy on `bu-finance` that denies every request not sent over TLS (`"Condition": {"Bool": {"aws:SecureTransport": "false"}}`), then show that a plain HTTP request is refused.

## Verify
- [ ] Cross-tenant read, write and list are all denied.
- [ ] Versioning keeps the previous model version and it can be retrieved.
- [ ] A locked object version cannot be deleted before retention ends (or the SIM limitation is noted).
- [ ] Lifecycle rules are stored on the bucket.

## Record for the standards
`STO-06` bucket-per-tenant model and naming. `STO-09` object-lock modes per data class. `SEC-02`/`SEC-03` IAM model and encryption at rest. `DAT-09` lifecycle/retention.

## Cleanup
```bash
rm -f forecast.csv model.txt lifecycle.json
S3_USER=finance bin/s3 s3 rm s3://bu-finance/forecast.csv
```
