"""Lab D04 (SIM): LoRA fine-tune a small model on CPU, checkpoint to S3 (ObjectScale stand-in), crash, resume, register.

  python ai/lora_train.py --steps 60 --ckpt-every 10 --kill-at 35     # simulates a worker crash at step 35
  python ai/lora_train.py --steps 60 --ckpt-every 10 --resume         # continues from the latest checkpoint
The HW version of this lab runs the same loop with NeMo or PEFT on GPUs; only the model size and device change.
"""
import argparse, io, json, os, pathlib, random, boto3, torch
from peft import LoraConfig, get_peft_model, set_peft_model_state_dict, get_peft_model_state_dict
from transformers import AutoModelForCausalLM, AutoTokenizer

HERE = pathlib.Path(__file__).parent
env = dict(l.strip().split("=", 1) for l in open(HERE.parent / ".env") if "=" in l and not l.startswith("#"))
s3 = boto3.client("s3", endpoint_url=os.environ.get("S3_URL", "http://localhost:8333"), region_name=env["S3_REGION"],
                  aws_access_key_id=env["S3_ACCESS_KEY"], aws_secret_access_key=env["S3_SECRET_KEY"])
BUCKET = "checkpoints"

ap = argparse.ArgumentParser()
ap.add_argument("--model", default="HuggingFaceTB/SmolLM2-135M")
ap.add_argument("--run", default="lora-demo")
ap.add_argument("--steps", type=int, default=60)
ap.add_argument("--ckpt-every", type=int, default=10)
ap.add_argument("--kill-at", type=int, default=0)
ap.add_argument("--resume", action="store_true")
ap.add_argument("--register", action="store_true", help="log the final adapter to MLflow (http://localhost:5000)")
a = ap.parse_args()

torch.manual_seed(0); random.seed(0)
tok = AutoTokenizer.from_pretrained(a.model)
model = get_peft_model(AutoModelForCausalLM.from_pretrained(a.model),
                       LoraConfig(r=8, lora_alpha=16, lora_dropout=0.0, target_modules=["q_proj", "v_proj"], task_type="CAUSAL_LM"))
model.print_trainable_parameters()
opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=2e-4)
rows = [json.loads(l) for l in open(HERE / "finetune.jsonl")]
start = 0

if a.resume:
    keys = sorted(o["Key"] for o in s3.list_objects_v2(Bucket=BUCKET, Prefix=f"{a.run}/").get("Contents", []) if o["Key"].endswith(".pt"))
    if keys:
        ck = torch.load(io.BytesIO(s3.get_object(Bucket=BUCKET, Key=keys[-1])["Body"].read()), weights_only=False)
        set_peft_model_state_dict(model, ck["adapter"]); opt.load_state_dict(ck["opt"]); start = ck["step"]
        random.setstate(ck["rng"]); torch.set_rng_state(ck["torch_rng"])
        print(f"resumed from s3://{BUCKET}/{keys[-1]} at step {start}")

model.train()
for step in range(start + 1, a.steps + 1):
    r = random.choice(rows)
    batch = tok(f"Question: {r['prompt']}\nAnswer: {r['completion']}{tok.eos_token}", return_tensors="pt")
    loss = model(**batch, labels=batch["input_ids"]).loss
    opt.zero_grad(); loss.backward(); opt.step()
    if step % 5 == 0:
        print(f"step {step} loss {loss.item():.3f}", flush=True)
    if step % a.ckpt_every == 0:
        buf = io.BytesIO()
        torch.save({"step": step, "adapter": get_peft_model_state_dict(model), "opt": opt.state_dict(),
                    "rng": random.getstate(), "torch_rng": torch.get_rng_state()}, buf)
        s3.put_object(Bucket=BUCKET, Key=f"{a.run}/step-{step:06d}.pt", Body=buf.getvalue())
        print(f"checkpoint s3://{BUCKET}/{a.run}/step-{step:06d}.pt ({buf.tell() / 1e6:.1f} MB)", flush=True)
    if step == a.kill_at:
        print(f"simulated crash at step {step}", flush=True); os._exit(137)

out = HERE / "adapters" / a.run
model.save_pretrained(out)
print(f"adapter saved to {out}")
if a.register:
    import mlflow
    mlflow.set_tracking_uri(os.environ.get("MLFLOW_TRACKING_URI", "http://localhost:5000"))
    os.environ.update(AWS_ACCESS_KEY_ID=env["S3_ACCESS_KEY"], AWS_SECRET_ACCESS_KEY=env["S3_SECRET_KEY"],
                      MLFLOW_S3_ENDPOINT_URL=os.environ.get("S3_URL", "http://localhost:8333"))
    mlflow.set_experiment("d04-lora")
    with mlflow.start_run(run_name=a.run) as run:
        mlflow.log_params({"base_model": a.model, "r": 8, "steps": a.steps, "dataset": "ai/finetune.jsonl"})
        mlflow.log_metric("final_loss", loss.item())
        mlflow.log_artifacts(str(out), artifact_path="adapter")
        mv = mlflow.register_model(f"runs:/{run.info.run_id}/adapter", "d04-lora-adapter")
        print(f"registered d04-lora-adapter version {mv.version}")
