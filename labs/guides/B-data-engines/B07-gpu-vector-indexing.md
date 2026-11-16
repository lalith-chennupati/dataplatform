# B07 - GPU-accelerated vector indexing

| Tier | Time | Domains | Prerequisites |
|---|---|---|---|
| **HW** (NVIDIA GPU, CUDA 12) for GPU numbers. CPU baseline runs in SIM. | 3 h | RAG, CMP | C04 (driver + CUDA on the node) for the GPU part |

## Prerequisites
```bash
python3 -m venv ~/.venvs/vec && . ~/.venvs/vec/bin/activate
pip install numpy faiss-cpu                                         # CPU baseline
pip install cupy-cuda12x cuvs-cu12 --extra-index-url=https://pypi.nvidia.com   # HW only (check the cuVS docs for your CUDA version)
nvidia-smi                                                           # HW: GPU visible
```

## Steps

### Step 1 - Save the benchmark script
`labs/evidence/b07/bench.py`:
```python
import sys, time, numpy as np
N, D, Q, K = int(sys.argv[1]), 768, 1000, 10
rng = np.random.default_rng(0)
def clustered(n):                                  # embeddings cluster by topic; pure random vectors are unrealistically hard
    c = centers[rng.integers(0, len(centers), n)]
    x = c + 0.6 * rng.standard_normal((n, D), dtype=np.float32) / np.sqrt(D)
    return x / np.linalg.norm(x, axis=1, keepdims=True)
centers = rng.standard_normal((1000, D), dtype=np.float32) / np.sqrt(D)
xb, xq = clustered(N), clustered(Q)

import faiss
flat = faiss.IndexFlatIP(D); flat.add(xb); _, truth = flat.search(xq, K)        # exact ground truth
def recall(ids): return np.mean([len(set(a) & set(b)) / K for a, b in zip(ids, truth)])

t = time.time(); hnsw = faiss.IndexHNSWFlat(D, 32, faiss.METRIC_INNER_PRODUCT); hnsw.hnsw.efConstruction = 100; hnsw.add(xb); build = time.time() - t
hnsw.hnsw.efSearch = 64; t = time.time(); _, ids = hnsw.search(xq, K); qps = Q / (time.time() - t)
print(f"CPU HNSW  N={N:>9} build={build:7.1f}s recall@10={recall(ids):.3f} QPS={qps:8.0f}")

try:
    import cupy as cp
    from cuvs.neighbors import cagra
    db, dq = cp.asarray(xb), cp.asarray(xq)
    t = time.time(); idx = cagra.build(cagra.IndexParams(metric="inner_product", graph_degree=32), db); cp.cuda.Stream.null.synchronize(); build = time.time() - t
    sp = cagra.SearchParams(itopk_size=64)
    cagra.search(sp, idx, dq, K)                                                 # warm-up
    t = time.time(); _, n = cagra.search(sp, idx, dq, K); cp.cuda.Stream.null.synchronize(); qps = Q / (time.time() - t)
    print(f"GPU CAGRA N={N:>9} build={build:7.1f}s recall@10={recall(cp.asnumpy(n)):.3f} QPS={qps:8.0f}")
except ImportError:
    print("cuVS not installed - GPU part skipped")
```

### Step 2 - [SIM] CPU baseline at small scale
```bash
cd labs/evidence/b07
python bench.py 100000
python bench.py 300000
```
Record the build time and QPS. Build time grows faster than linearly, so extrapolate to your real corpus size.

### Step 3 - [HW] CPU vs GPU at scale
On the GPU node (C04), run with 1M, 5M and 10M vectors. 10M x 768 float32 is about 31 GB, so the GPU needs enough memory. Otherwise use IVF-PQ (`cuvs.neighbors.ivf_pq`) or fewer dimensions.
```bash
for n in 1000000 5000000 10000000; do python bench.py $n | tee -a results.txt; done
nvidia-smi --query-gpu=name,memory.used,utilization.gpu --format=csv -l 5 > gpu.csv &      # in parallel during the run
```

### Step 4 - Tune recall vs. speed
- CPU: raise `efSearch` (64 -> 128 -> 256) and note recall and QPS.
- GPU: raise `itopk_size` (64 -> 128 -> 256).
Pick the setting where recall@10 >= your target (e.g. 0.95).

### Step 5 - Sizing note
Fill in the table for your corpus size:

| Index tier | When to use | Build time | QPS @ recall 0.95 | Memory | Rebuild cadence |
|---|---|---|---|---|---|
| CPU HNSW (in the Search Engine) | < ~5M vectors, modest QPS | | | | |
| GPU CAGRA build + CPU serve (HNSW export) | large corpora, frequent rebuilds | | | | |
| GPU build + GPU serve | very high QPS / low latency | | | | |

## Verify
- [ ] CPU baseline numbers are recorded.
- [ ] *(HW)* GPU build time, recall@10 and QPS are recorded at three sizes.
- [ ] The sizing note is written.

## Record for the standards
`RAG-06` vector index tiers and sizing. `CMP-03` whether GPUs are reserved for indexing/retrieval.

## Cleanup
`deactivate; rm -rf ~/.venvs/vec`
