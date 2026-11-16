# D09 - AI PC and edge inference *(optional)*

| Tier | Time | Domains | Prerequisites |
|---|---|---|---|
| SIM (any laptop with Ollama) / HW (Dell AI PC with NPU or RTX GPU, Dell Pro AI Studio) | 3 h | CMP, PRV, SEC, DAT | L01 core profile reachable from the laptop (for the sync step). |

Some AI runs better on the client: private notes, offline field work, low-latency assistants. The standard has to say which models may run on devices, which data they may see, and how results come back to the core platform. Steps 1-3 work on any laptop. **Untested here:** Dell Pro AI Studio and NPU runtimes (no AI PC on my VM); check Dell's documentation for the current tool set and supported models.

## Steps

### Step 1 - [SIM] Run a small model locally
```bash
ollama pull qwen2.5:0.5b            # or a 3-4B model on a laptop with 16 GB+ RAM
python labs/env/ai/loadtest.py --model qwen2.5:0.5b --concurrency 1 --requests 4 --max-tokens 64
```
Record tok/s and TTFT for one user and the RAM used (Activity Monitor / Task Manager). Disconnect the network and confirm it still answers.

### Step 2 - [HW] NPU / GPU on a Dell AI PC
Install Dell Pro AI Studio (or the vendor runtime: OpenVINO for Intel NPU, Ryzen AI / ONNX Runtime for AMD NPU, Qualcomm AI Hub, or CUDA/TensorRT-LLM on an RTX laptop). Run the same model in a quantized format (INT4/INT8) on the NPU and on the GPU/CPU. Record tok/s, TTFT, battery drain over 10 minutes, and fan noise. Note which models Dell has validated for the device.

### Step 3 - [SIM] Sync results to the core
The device writes feedback (question, answer, rating) locally and uploads only the fields allowed by the classification standard:
```bash
cat > feedback.jsonl <<'J'
{"device": "lap-042", "ts": "2026-11-16T10:00:00Z", "rating": 4, "question_len": 52, "model": "qwen2.5:0.5b"}
J
labs/env/bin/s3 s3 cp feedback.jsonl s3://bu-research/edge-feedback/lap-042/$(date +%F).jsonl
```
Note what is **not** uploaded: the question text and answer (they may contain personal or confidential data). If the full text is needed for evaluation, it must be classified first and go to a restricted bucket (A09 tenant isolation), and the user must be told.

### Step 4 - Device controls
Answer with your endpoint team: how models are distributed and updated (MDM/Intune, signed packages), whether users may download models themselves, disk encryption, prompt/response logging on the device, and how to remotely wipe models and caches.

## Verify
- [ ] Local model measured online and offline.
- [ ] *(HW)* NPU vs GPU/CPU measured on a Dell AI PC.
- [ ] Only approved fields synced to the core bucket.
- [ ] Client/edge AI standard drafted.

## Record for the standards
`CMP-11` client and edge AI. `PRV-02` data classes allowed on devices. `MLO-01` approved models (including on-device). `SEC-08` model package signing and distribution.

## Cleanup
`ollama rm qwen2.5:0.5b`; `labs/env/bin/s3 s3 rm --recursive s3://bu-research/edge-feedback/`; `rm feedback.jsonl`.
