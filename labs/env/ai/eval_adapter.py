"""Lab D07: evaluate one registered LoRA adapter version against its base model (default promotion gate).

  python ai/eval_adapter.py --model-uri models:/d04-lora-adapter/2
Downloads that exact version from MLflow, computes the mean loss of base and base+adapter on ai/finetune.jsonl and
passes if the adapter is better by at least --min-gain. Use a held-out set in real pipelines; this lab reuses the
training pairs so the run stays small.
"""
import argparse, json, os, pathlib, sys, tempfile, boto3, torch
from mlflow.tracking import MlflowClient
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer

HERE = pathlib.Path(__file__).parent
ARTIFACT_BUCKET, ARTIFACT_ROOT = "model-registry", "mlflow"   # --artifacts-destination in docker-compose.yml
env = dict(l.strip().split("=", 1) for l in open(HERE.parent / ".env") if "=" in l and not l.startswith("#"))
os.environ.setdefault("MLFLOW_TRACKING_URI", "http://localhost:5000")
os.environ.update(AWS_ACCESS_KEY_ID=env["S3_ACCESS_KEY"], AWS_SECRET_ACCESS_KEY=env["S3_SECRET_KEY"],
                  MLFLOW_S3_ENDPOINT_URL=os.environ.get("S3_URL", "http://localhost:8333"))
ap = argparse.ArgumentParser(); ap.add_argument("--model-uri", required=True); ap.add_argument("--min-gain", type=float, default=0.0)
a = ap.parse_args()

name, version = a.model_uri.removeprefix("models:/").split("/")
mv = MlflowClient().get_model_version(name, version)
base = MlflowClient().get_run(mv.run_id).data.params["base_model"]
# Read that version's adapter files straight from the artifact bucket: SeaweedFS's recursive listing returns nested
# keys with a duplicated prefix, so MLflow's own download finds nothing. On ObjectScale/S3 both ways work.
s3 = boto3.client("s3", endpoint_url=os.environ["MLFLOW_S3_ENDPOINT_URL"], region_name=env["S3_REGION"],
                  aws_access_key_id=env["S3_ACCESS_KEY"], aws_secret_access_key=env["S3_SECRET_KEY"])
prefix = mv.source.replace("mlflow-artifacts:/", ARTIFACT_ROOT + "/", 1)
path = pathlib.Path(tempfile.mkdtemp())
for f in ("adapter_config.json", "adapter_model.safetensors"):
    (path / f).write_bytes(s3.get_object(Bucket=ARTIFACT_BUCKET, Key=f"{prefix}/{f}")["Body"].read())
tok = AutoTokenizer.from_pretrained(base)
rows = [json.loads(l) for l in open(HERE / "finetune.jsonl")]


@torch.no_grad()
def mean_loss(m):
    m.eval(); out = []
    for r in rows:
        b = tok(f"Question: {r['prompt']}\nAnswer: {r['completion']}{tok.eos_token}", return_tensors="pt")
        out.append(m(**b, labels=b["input_ids"]).loss.item())
    return sum(out) / len(out)


base_loss = mean_loss(AutoModelForCausalLM.from_pretrained(base))
tuned_loss = mean_loss(PeftModel.from_pretrained(AutoModelForCausalLM.from_pretrained(base), path))
ok = base_loss - tuned_loss > a.min_gain
print(json.dumps({"model": a.model_uri, "base_loss": round(base_loss, 4), "adapter_loss": round(tuned_loss, 4)}),
      "-> gate", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
