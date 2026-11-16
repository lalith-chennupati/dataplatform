# A10 - S3 for AI workloads

| Tier | Time | Domains | Prerequisites |
|---|---|---|---|
| SIM / HW (ObjectScale, S3 over RDMA where available) | 3 h | STO, MLO | A09 |

## Steps

### Step 1 - Training container with S3 access
```bash
cd labs/env && set -a && . ./.env && set +a
docker run -d --name trainer --network aifactory-lab_default \
  -e AWS_ACCESS_KEY_ID=$S3_ACCESS_KEY -e AWS_SECRET_ACCESS_KEY=$S3_SECRET_KEY -e AWS_REGION=$S3_REGION \
  -e AWS_REQUEST_CHECKSUM_CALCULATION=when_required -e AWS_RESPONSE_CHECKSUM_VALIDATION=when_required \
  -e S3_ENDPOINT=http://s3:8333 mirror.gcr.io/library/python:3.12-slim sleep infinity
docker exec trainer pip install -q torch --index-url https://download.pytorch.org/whl/cpu
docker exec trainer pip install -q boto3 numpy
```
DEMO/HW: run the same on a GPU node with `S3_ENDPOINT=$OBJ` and the IAM user's keys.

### Step 2 - Train and checkpoint to S3
```bash
docker exec -i trainer python - <<'PY'
import io, os, time, boto3, torch, torch.nn as nn
s3 = boto3.client("s3", endpoint_url=os.environ["S3_ENDPOINT"])
model = nn.Sequential(nn.Linear(1024, 4096), nn.ReLU(), nn.Linear(4096, 1024))   # ~32 MiB of weights; ~96 MiB checkpoint with AdamW state
opt = torch.optim.AdamW(model.parameters())
for step in range(1, 31):
    loss = model(torch.randn(64, 1024)).pow(2).mean(); opt.zero_grad(); loss.backward(); opt.step()
    if step % 10 == 0:
        buf = io.BytesIO(); torch.save({"step": step, "model": model.state_dict(), "opt": opt.state_dict()}, buf)
        t = time.time(); s3.put_object(Bucket="checkpoints", Key=f"run-001/step-{step:05d}.pt", Body=buf.getvalue())
        print(f"step {step} loss {loss.item():.4f} ckpt {len(buf.getvalue())/2**20:.0f} MiB in {time.time()-t:.2f}s")
PY
bin/s3 s3 ls s3://checkpoints/run-001/
```

### Step 3 - Resume from the latest checkpoint
```bash
docker exec -i trainer python - <<'PY'
import io, os, boto3, torch, torch.nn as nn
s3 = boto3.client("s3", endpoint_url=os.environ["S3_ENDPOINT"])
keys = sorted(o["Key"] for o in s3.list_objects_v2(Bucket="checkpoints", Prefix="run-001/")["Contents"])
ck = torch.load(io.BytesIO(s3.get_object(Bucket="checkpoints", Key=keys[-1])["Body"].read()))
model = nn.Sequential(nn.Linear(1024, 4096), nn.ReLU(), nn.Linear(4096, 1024)); model.load_state_dict(ck["model"])
print("resumed from", keys[-1], "at step", ck["step"])
PY
```

### Step 4 - Multipart tuning for large artefacts
```bash
docker exec trainer sh -c 'head -c 2147483648 /dev/urandom > /tmp/weights.bin'      # 2 GiB "model"
docker exec -i trainer python - <<'PY'
import os, time, boto3
from boto3.s3.transfer import TransferConfig
s3 = boto3.client("s3", endpoint_url=os.environ["S3_ENDPOINT"])
for chunk_mb, conc in [(8, 4), (64, 8), (128, 16)]:
    cfg = TransferConfig(multipart_chunksize=chunk_mb * 2**20, max_concurrency=conc)
    t = time.time(); s3.upload_file("/tmp/weights.bin", "model-registry", f"bench/w-{chunk_mb}-{conc}.bin", Config=cfg)
    dt = time.time() - t; print(f"chunk {chunk_mb} MiB x{conc}: {2048/dt:.0f} MiB/s")
PY
```
Record the best setting. On ObjectScale hardware, repeat from a GPU node. Results on the lab stand-in only show relative trends.

### Step 5 - Artefact layout convention
Agree a key layout and apply it:
```
s3://model-registry/<team>/<model-name>/<version>/{weights/,tokenizer/,model-card.md,eval/}
s3://checkpoints/<team>/<run-id>/step-<n>.pt          (lifecycle: tmp/ 7 days, runs 30 days)
```

### Step 6 - [HW] S3 over RDMA
If your ObjectScale release and client stack support S3 over RDMA, follow Dell's guide to enable the RDMA endpoint and install the client library. Repeat Step 4 and compare throughput and CPU use with TCP.

## Verify
- [ ] Checkpoints land in S3 and training resumes from the latest one.
- [ ] A throughput table for the multipart settings exists.
- [ ] The artefact key layout is agreed.

## Record for the standards
`MLO-04` mandatory artefact metadata/layout. `BCR-07` checkpoint policy. `STO-04` object throughput targets.

## Cleanup
```bash
docker rm -f trainer
bin/s3 s3 rm --recursive s3://checkpoints/run-001/ && bin/s3 s3 rm --recursive s3://model-registry/bench/
```
