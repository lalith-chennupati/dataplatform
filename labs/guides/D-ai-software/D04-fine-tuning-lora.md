# D04 - Fine-tune a model (LoRA)

| Tier | Time | Domains | Prerequisites |
|---|---|---|---|
| SIM (CPU, 135M-parameter model) / HW (multi-GPU node, NeMo or PEFT) | 2 h SIM, 1 day HW | MLO, BCR, STO, DAT | L01 with `core ai` (S3 + MLflow). Python venv with `torch` (CPU wheel), `transformers`, `peft`, `boto3`, `mlflow==2.22.0`. |

LoRA trains small adapter matrices instead of the full model, so the checkpoint is megabytes instead of gigabytes. `labs/env/ai/lora_train.py` runs the full loop on CPU: load base model -> LoRA -> train on `ai/finetune.jsonl` -> checkpoint adapter + optimizer + RNG state to S3 (ObjectScale stand-in) every N steps -> crash -> resume -> register in MLflow. On HW the loop is the same; the model, the dataset and the device change. Steps 1-4 were run on my VM.

```bash
python3 -m venv ~/.venvs/aif && . ~/.venvs/aif/bin/activate
pip install --index-url https://download.pytorch.org/whl/cpu torch && pip install transformers peft boto3 "mlflow==2.22.0"
cd labs/env && make up PROFILES="core ai"
```

## Steps

### Step 1 - Dataset under version control
`ai/finetune.jsonl` has 12 prompt/completion pairs about the lab's own standards. In production the curated dataset lives on PowerScale or as an Iceberg table, and its version (file hash or Iceberg snapshot ID, B02) is logged with the run. Record who approved the dataset and its classification (`MLO-10`, `PRV-02`).
```bash
sha256sum ai/finetune.jsonl | tee ../evidence/d04-dataset.sha256
```

### Step 2 - Train and crash
```bash
python ai/lora_train.py --steps 40 --ckpt-every 10 --kill-at 25; echo "exit=$?"
```
Expected (observed):
```
trainable params: 460,800 || all params: 134,975,808 || trainable%: 0.3414
checkpoint s3://checkpoints/lora-demo/step-000010.pt (5.7 MB)
checkpoint s3://checkpoints/lora-demo/step-000020.pt (5.7 MB)
simulated crash at step 25
exit=137
```
Steps 21-25 are lost work. The checkpoint interval trades lost work against checkpoint time and storage.

### Step 3 - Resume and register
```bash
python ai/lora_train.py --steps 40 --ckpt-every 10 --resume --register
bin/s3 s3 ls s3://checkpoints/lora-demo/
```
Expected: `resumed from s3://checkpoints/lora-demo/step-000020.pt at step 20`, checkpoints 30 and 40, then `registered d04-lora-adapter version 1`. Open MLflow (`http://localhost:5000`) -> experiment `d04-lora`: parameters (base model, rank, steps, dataset), final loss, and the adapter files as artifacts in `s3://model-registry/mlflow`.

### Step 4 - Use the adapter
```bash
python - <<'PY'
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer
base = "HuggingFaceTB/SmolLM2-135M"; tok = AutoTokenizer.from_pretrained(base)
m = PeftModel.from_pretrained(AutoModelForCausalLM.from_pretrained(base), "ai/adapters/lora-demo")
ids = tok("Question: What does XID 79 mean?\nAnswer:", return_tensors="pt")
print(tok.decode(m.generate(**ids, max_new_tokens=30)[0], skip_special_tokens=True))
PY
```
A 135M model after 40 CPU steps will not answer well. The point is the mechanics: base model + adapter, both versioned.

### Step 5 - [HW] Multi-GPU run
Run the same pattern with your framework (NeMo `llm.finetune` with a LoRA PEFT scheme, or Hugging Face `accelerate launch` / `torchrun --nproc_per_node 8` with PEFT) on an 8B-class model:
1. Dataset on PowerScale (NFS RWX, A06) and checkpoints to ObjectScale (A10) or PowerScale.
2. Measure: time per step, GPU utilisation (C04/C08), checkpoint size and write time, read throughput from storage during the first epoch.
3. Kill one worker pod/process mid-run (`kubectl delete pod` or `kill -9`) and resume. Record total lost time (lost steps + restart + checkpoint load).
4. Evaluate the adapter against the base model on a held-out set (D05) before registering it as a candidate.

### Step 6 - Write the policies
- Fine-tuning policy: who may fine-tune, approved base models, allowed data classes, approval before registering, where adapters may be deployed (`MLO-10`).
- Checkpoint policy: interval (minutes or steps) per job size, retention (keep last N + best), storage target, encryption (`BCR-07`).

## Verify
- [ ] Training resumed from the last S3 checkpoint after a crash.
- [ ] Adapter registered in MLflow with base model, dataset hash and parameters.
- [ ] *(HW)* Multi-GPU run measured, and lost time after a worker failure recorded.
- [ ] Fine-tuning and checkpoint policies drafted.

## Record for the standards
`MLO-10` fine-tuning policy. `BCR-07` checkpoint frequency. `MLO-03` registry and artefact layout. `MLO-04` mandatory model metadata (base model, dataset version, owner). `DAT` dataset versioning.

## Cleanup
```bash
bin/s3 s3 rm --recursive s3://checkpoints/lora-demo/
rm -rf ai/adapters/lora-demo
```
