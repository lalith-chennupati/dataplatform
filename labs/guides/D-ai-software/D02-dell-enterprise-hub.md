# D02 - Dell Enterprise Hub on Hugging Face

| Tier | Time | Domains | Prerequisites |
|---|---|---|---|
| HW (PowerEdge GPU server) / DEMO (browse the Hub) | 4 h | MLO, PLT, SEC | D01 (for comparison), a Hugging Face account with access to Dell Enterprise Hub, Docker + NVIDIA container toolkit on the GPU node. |

Dell Enterprise Hub (`dell.huggingface.co`) is a Dell-curated catalog on Hugging Face: popular open models packaged in containers tested on specific PowerEdge GPU configurations, with ready-made `docker run` / Kubernetes snippets. The serving engine is Hugging Face Text Generation Inference (TGI), which also exposes an OpenAI-compatible API. **Untested here:** no GPU and no Hub access on my VM. Copy the exact command from the model page for your server; the image name and tag below are placeholders.

## Steps

### Step 1 - [DEMO] Pick a model for your platform
On the Hub, filter by your server (e.g. XE9680 with H100) and pick the same model family you served in D01. Record: model, licence (`MLO-01`), container image and tag, the GPU count Dell lists for the model, and whether the model is gated.

### Step 2 - [HW] Run it
```bash
export HF_TOKEN=hf_...                     # read-only token, never commit
docker login registry.dell.huggingface.co -u <hf-user> -p $HF_TOKEN
docker run -d --name deh --gpus 1 --shm-size 1g -p 8080:80 -e NUM_SHARD=1 -e MAX_BATCH_PREFILL_TOKENS=16182 \
  -e MAX_INPUT_TOKENS=8000 -e MAX_TOTAL_TOKENS=8192 \
  registry.dell.huggingface.co/enterprise-dell-inference-<model>:<tag>
docker logs -f deh | grep -i -E 'connected|ready'
curl -s localhost:8080/v1/chat/completions -H 'Content-Type: application/json' \
  -d '{"model":"tgi","messages":[{"role":"user","content":"Say hi"}],"max_tokens":20}'
```

### Step 3 - [HW] Same load test as D01
```bash
~/.venvs/aif/bin/python labs/env/ai/loadtest.py --url http://localhost:8080/v1 --model tgi --concurrency 1,8,32,64 | tee evidence/d02-deh.txt
```

### Step 4 - Compare
| | NIM (D01) | Dell Enterprise Hub / TGI |
|---|---|---|
| tok/s at 32 users | | |
| p95 TTFT | | |
| GPU memory used (`nvidia-smi`) | | |
| Image size, cold start | | |
| Licence / support (NVIDIA AI Enterprise vs Dell/HF) | | |
| Upgrade path, CVE patching | | |
| Air-gap install effort (`PLT-10`) | | |

### Step 5 - Supply chain checks
Before a model source is approved: scan the image (`trivy image <image>`), record the image digest, check the model card and licence, and decide whether weights must be mirrored into an internal registry/bucket (`SEC-08`, `PLT-07`).

## Verify
- [ ] Same model family served from Dell Enterprise Hub and NIM, measured with the same load test.
- [ ] Comparison table filled in.
- [ ] Image scanned; digest and licence recorded.

## Record for the standards
`MLO-01` permitted model sources. `MLO-02` model approval steps. `MLO-05` serving runtimes. `SEC-08` supply chain. `PLT-07` internal registry/mirror.

## Cleanup
`docker rm -f deh`, remove the image if disk is short, revoke the HF token if it was created for the lab.
