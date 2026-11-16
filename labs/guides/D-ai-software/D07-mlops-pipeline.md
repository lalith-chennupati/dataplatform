# D07 - MLOps pipeline: register, gate, promote, roll back

| Tier | Time | Domains | Prerequisites |
|---|---|---|---|
| SIM (MLflow + S3 + the D04/D05 scripts) / HW (same pipeline driving GPU training and NIM deployment) | 3 h | MLO, OPS, SEC | D04 (registered `d04-lora-adapter` v1) and D05 (`guard_eval.py`). |

The pipeline is: **train** (D04, logs params, metrics, dataset hash and artefacts) -> **register** a new version -> **gate** (`ai/promote.py` runs `ai/eval_adapter.py` on that exact version: it downloads the version's adapter, compares its loss with the base model's, and the result is tagged on the version) -> **promote** by moving the MLflow alias `champion` -> **deploy** whatever `champion` points to -> **roll back** by moving the alias back. Serving reads `models:/d04-lora-adapter@champion`, so promotion and rollback are metadata changes, not rebuilds. Steps 1-4 were run on my VM.

## Steps

### Step 1 - A second version
```bash
cd labs/env && PY=~/.venvs/aif/bin/python
$PY ai/lora_train.py --steps 40 --resume --register      # resumes at the last checkpoint and registers the adapter again
```
Expected: `registered d04-lora-adapter version 2`. In MLflow (`http://localhost:5000` -> Models) the model has versions 1 and 2, each linked to its run.

### Step 2 - Gate and promote
```bash
$PY ai/promote.py --name d04-lora-adapter --version 1
$PY ai/promote.py --name d04-lora-adapter --version 2
```
Observed for v2:
```
d04-lora-adapter v2 passed the gate and is champion (previous v1): {"model": "models:/d04-lora-adapter/2", "base_loss": 4.4355, "adapter_loss": 3.8589} -> gate PASS
```
The gate must test the artefact being promoted, not whatever endpoint happens to be running. For an application release (prompt, index or guardrail change) use the D05 suite as the gate instead: `--gate "python ai/guard_eval.py"`. Real pipelines run both.
Each version gets tags `gate_result` and `gate_score`; aliases are `candidate`, `champion`, `previous-champion`.

### Step 3 - A failing gate does not promote
```bash
$PY ai/promote.py --name d04-lora-adapter --version 1 --gate "false {model_uri}"; echo "exit=$?"
```
Observed: `v1 FAILED the gate, champion stays v2`, `exit=1`. In CI the non-zero exit stops the pipeline.

### Step 4 - Roll back
```bash
$PY ai/promote.py --name d04-lora-adapter --rollback
```
Observed: `rolled back d04-lora-adapter: champion v2 -> v1`. Time it: this is your model rollback RTO (seconds), compared with a rebuild-and-redeploy.

### Step 5 - Wire it into CI
Example GitHub Actions job (not committed, to keep this repo's CI cheap):
```yaml
on: {push: {paths: ["labs/env/ai/finetune.jsonl", "labs/env/ai/redteam.jsonl"]}}
jobs:
  train-gate-promote:
    runs-on: [self-hosted, gpu]          # a runner inside the AI Factory, never a public runner for internal data
    steps:
      - uses: actions/checkout@v4
      - run: python labs/env/ai/lora_train.py --steps 200 --register
      - run: python labs/env/ai/promote.py --name d04-lora-adapter     # newest version; fails the job if the gate fails
```
Production promotion to `champion` usually also needs a human approval (environment protection rule) for high-risk models.

### Step 6 - [HW] Deploy what champion points to
Have the serving layer (KServe/NIM Operator/Helm) resolve `models:/d04-lora-adapter@champion` at deploy time (download adapter to the NIM LoRA directory on PowerScale, then rolling restart, or NIM dynamic LoRA loading). Run D01's load test after each promotion and compare against the previous champion; a latency regression is a gate failure too.

## Verify
- [ ] Two versions registered with lineage (run, params, dataset hash).
- [ ] Promotion only after a passing gate; failing gate leaves `champion` unchanged.
- [ ] Rollback measured in seconds.
- [ ] CI design agreed, including where human approval is required.

## Record for the standards
`MLO-03` registry and lineage. `MLO-04` mandatory metadata. `MLO-02` approval before promotion. `MLO-07` gate thresholds. `MLO-08` what is monitored after promotion. `MLO-12` versioning and rollback. `OPS` change management for models.

## Cleanup
Delete the model in MLflow UI (Models -> d04-lora-adapter -> Delete) or keep it for E03 (backup of AI assets).
