# D08 - Red Hat OpenShift AI on Dell *(optional)*

| Tier | Time | Domains | Prerequisites |
|---|---|---|---|
| DEMO (Red Hat Developer Sandbox / OpenShift AI trial) / HW (OpenShift on PowerEdge with GPUs) | 1 day | PLT, MLO, CMP, STO | D07 done on upstream Kubernetes (you need the comparison baseline). A Red Hat account. HW: OpenShift 4.x cluster, Dell CSM PowerScale operator. |

The question this lab answers is `PLT-01`: upstream Kubernetes (plus your own MLflow, Kueue, GPU Operator) or a supported platform such as OpenShift AI. You repeat D07's flow on OpenShift AI and score both. **Untested here:** I have no OpenShift cluster or Red Hat account on my VM; menu names follow the OpenShift AI documentation and change between releases.

## Steps

### Step 1 - [DEMO] Workbench
Open the OpenShift AI dashboard -> Data Science Projects -> Create project `d08-lab` -> Create workbench (Jupyter, PyTorch image, small size). Add a data connection of type S3 pointing to your bucket (in a sandbox, any S3-compatible endpoint you control; on HW, ObjectScale `checkpoints` bucket). Clone this repo in the workbench terminal.

### Step 2 - [DEMO] Run D04 in the workbench
```bash
pip install peft transformers boto3
S3_URL=https://<objectscale-endpoint> python labs/env/ai/lora_train.py --steps 40 --ckpt-every 10
```
(Create a `.env` with S3 keys from the data connection, as in `labs/env/.env`. Do not commit it.)

### Step 3 - [DEMO] Data science pipeline
Data Science Pipelines -> Configure pipeline server (S3 storage for artefacts). Build a two-step pipeline (Elyra in the workbench, or KFP SDK): `train` -> `evaluate`, with evaluate failing on the D05 gate. Run it and check the run graph, logs and artefacts.

### Step 4 - [DEMO/HW] Model serving
Models -> Deploy model (single-model serving / KServe, vLLM runtime) from the S3 data connection. Call the endpoint with D01's load test:
```bash
python labs/env/ai/loadtest.py --url https://<route>/v1 --api-key $TOKEN --model <name> --concurrency 1,8
```

### Step 5 - [HW] Platform pieces on Dell
1. Install the NVIDIA GPU Operator from OperatorHub (C04 steps) and run a GPU workbench.
2. Install Dell Container Storage Modules (CSM) operator from OperatorHub, create a PowerScale StorageClass (A06) and use it for workbench PVCs and model storage.
3. Configure GPU quotas per project (Kueue is part of recent OpenShift AI releases; otherwise ResourceQuota) and repeat C05's borrowing test.

### Step 6 - Score both platforms
| Criterion | Upstream K8s (C04/C05/D07) | OpenShift AI |
|---|---|---|
| Time to a working pipeline | | |
| GPU Operator / CSM install and upgrade | | |
| Multi-tenancy and quotas | | |
| Notebooks / self-service for data scientists | | |
| Serving (runtimes, autoscaling) | | |
| Security baseline out of the box (E01) | | |
| Support model, licence cost per node | | |
| Skills in your team | | |

## Verify
- [ ] D04 training and D05 gate run on OpenShift AI.
- [ ] A model served and load-tested.
- [ ] *(HW)* GPU Operator and Dell CSM PowerScale working on OpenShift.
- [ ] Comparison table completed and a `PLT-01` recommendation written.

## Record for the standards
`PLT-01` Kubernetes distribution / AI platform. `PLT-02` operators allowed. `MLO-03` registry. `MLO-05` serving. `CMP-05` GPU sharing on the chosen platform.

## Cleanup
Delete the `d08-lab` project (removes workbenches, pipelines and served models). Remove the S3 test objects.
