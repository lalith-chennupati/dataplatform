# D01 - Serve an LLM with NVIDIA NIM

| Tier | Time | Domains | Prerequisites |
|---|---|---|---|
| SIM (Ollama OpenAI-compatible API) / DEMO (NVIDIA API catalog, build.nvidia.com) / HW (GPU node + NVIDIA AI Enterprise licence) | 4 h | MLO, PLT, STO, CMP | L01 with the `ai` profile. HW: C04, an NGC API key, a PowerScale RWX StorageClass (A06). |

NIM packages a model with an optimised engine (TensorRT-LLM, vLLM or SGLang) behind an OpenAI-compatible API. Because Ollama, vLLM, TGI and NIM all speak `/v1/chat/completions`, the same load test (`labs/env/ai/loadtest.py`) measures each of them. In SIM you learn the API and the measurement method; the numbers come from a CPU and are not GPU numbers. **Untested here:** the NIM Helm/Operator steps (no GPU or NGC key on my VM). Check chart names, values and model profiles against the NIM documentation for your version.

## Steps

### Step 1 - [SIM] Call the API
```bash
cd labs/env && make up PROFILES="core ai"
docker compose exec ollama ollama pull qwen2.5:0.5b
curl -s localhost:11434/v1/models | python3 -m json.tool | grep '"id"'
curl -s localhost:11434/v1/chat/completions -H 'Content-Type: application/json' \
  -d '{"model":"qwen2.5:0.5b","messages":[{"role":"user","content":"Say hi in 3 words"}],"max_tokens":20}' | python3 -m json.tool
```
Expected: a `choices[0].message.content` answer and a `usage` block with `prompt_tokens` / `completion_tokens`. Record that the response shape is the OpenAI one; that is what makes runtimes interchangeable (`ARC-04`).

### Step 2 - [DEMO] Hosted NIM
Create an API key on build.nvidia.com and call a hosted NIM with the same client:
```bash
export NVIDIA_API_KEY=nvapi-...          # never commit it
curl -s https://integrate.api.nvidia.com/v1/chat/completions -H "Authorization: Bearer $NVIDIA_API_KEY" \
  -H 'Content-Type: application/json' -d '{"model":"meta/llama-3.1-8b-instruct","messages":[{"role":"user","content":"Say hi"}],"max_tokens":20}'
```

### Step 3 - [SIM/DEMO] Load test
```bash
~/.venvs/aif/bin/python ai/loadtest.py --model qwen2.5:0.5b --concurrency 1,4 --requests 8 --max-tokens 64 | tee ../evidence/d01-sim.txt
# DEMO: ai/loadtest.py --url https://integrate.api.nvidia.com/v1 --api-key $NVIDIA_API_KEY --model meta/llama-3.1-8b-instruct
```
Example SIM output on my VM (CPU only):
```
conc  req/s   tok/s  p50 s  p95 s p95 ttft s
   1   0.22    13.5   2.38  13.10       1.21
   4   1.79   105.1   2.16   2.34       1.81
```
Read it as: throughput (tok/s) rises with concurrency until the engine saturates; p95 latency and time-to-first-token (TTFT) are what users feel. The SLO needs both: e.g. "p95 TTFT < 1 s and > 30 tok/s per user at 20 concurrent users".

### Step 4 - [HW] Deploy a NIM on Kubernetes
```bash
kubectl create ns nim
kubectl -n nim create secret docker-registry ngc-secret --docker-server=nvcr.io --docker-username='$oauthtoken' --docker-password=$NGC_API_KEY
kubectl -n nim create secret generic ngc-api --from-literal=NGC_API_KEY=$NGC_API_KEY
# model cache on PowerScale (RWX) so replicas share one copy of the weights
kubectl -n nim apply -f - <<'YAML'
apiVersion: v1
kind: PersistentVolumeClaim
metadata: {name: nim-cache}
spec: {accessModes: [ReadWriteMany], storageClassName: powerscale-nfs, resources: {requests: {storage: 200Gi}}}
YAML
helm fetch https://helm.ngc.nvidia.com/nim/charts/nim-llm-<version>.tgz --username='$oauthtoken' --password=$NGC_API_KEY
helm install llama nim-llm-<version>.tgz -n nim \
  --set image.repository=nvcr.io/nim/meta/llama-3.1-8b-instruct --set image.tag=<tag> \
  --set model.ngcAPISecret=ngc-api --set imagePullSecrets[0].name=ngc-secret \
  --set persistence.enabled=true --set persistence.existingClaim=nim-cache --set resources.limits."nvidia\.com/gpu"=1
kubectl -n nim logs -f deploy/llama-nim-llm | grep -iE 'profile|ready|Uvicorn'    # which engine profile was selected
```
The NIM Operator (`NIMCache`, `NIMService` CRDs) is the alternative: it pre-caches models and manages scaling. Record which one you choose.

### Step 5 - [HW] Measure and scale
1. Port-forward the service and rerun `loadtest.py --url http://localhost:8000/v1 --model meta/llama-3.1-8b-instruct --concurrency 1,8,32,64`.
2. Record the first-start time with an empty cache and with a warm PowerScale cache.
3. Scale to 2 replicas (`kubectl scale` or an HPA on GPU KV-cache usage / queue depth metrics exposed by the NIM) and rerun at the highest concurrency.
4. Compare with another runtime (vLLM, TGI from D02, Triton) on the same GPU.

### Step 6 - Decide
Fill in: serving runtime per model class, SLO per tier (interactive, batch), replicas per GPU type, where weights are cached, how the endpoint is exposed (`NET-08`, behind the AI gateway `MLO-11`).

## Verify
- [ ] The same client and load test run against at least two OpenAI-compatible endpoints.
- [ ] tok/s, p50/p95 latency and p95 TTFT are recorded per concurrency level.
- [ ] *(HW)* Cold vs warm start time with the PowerScale model cache.
- [ ] Serving runtime and SLOs proposed.

## Record for the standards
`MLO-05` serving runtime. `MLO-06` inference SLOs. `STO` model cache placement (A06). `NET-08` endpoint exposure. `MLO-11` AI gateway. `ARC-04` OpenAI-compatible API as a mandatory interface.

## Cleanup
SIM: nothing to remove (`docker compose exec ollama ollama rm <model>` to free disk). HW: `helm uninstall llama -n nim && kubectl delete ns nim`.
