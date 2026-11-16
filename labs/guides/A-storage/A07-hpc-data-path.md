# A07 - High-performance AI data path

| Tier | Time | Domains | Prerequisites |
|---|---|---|---|
| **HW** (PowerEdge GPU node + PowerScale all-flash + RDMA-capable network) | 4 h | STO, CMP, NET | A01; C04 (NVIDIA driver installed) |

## Prerequisites
- PowerScale F-series nodes with RDMA-capable front-end NICs, and a OneFS release that supports NFS over RDMA.
- GPU node with ConnectX/BlueField NICs, MLNX_OFED/DOCA drivers, NVIDIA driver + CUDA, `nvidia-fs` (GDS kernel module) and `gds-tools`.
- Lossless or RoCE-tuned network between them (see C06).
- `fio` installed on the GPU node.

## Steps

### Step 1 - Enable NFS over RDMA on OneFS
```bash
ssh root@$PS
isi nfs settings global modify --nfsv3-rdma-enabled=true     # flag name varies by release: check `isi nfs settings global modify --help | grep -i rdma`
isi nfs settings global view | grep -i rdma
isi network pools modify groupnet0.subnet0.pool0 --nfsv3-rroce-only=true    # optional: restrict pool to RoCE-capable ifaces
```

### Step 2 - Baseline over TCP
```bash
sudo mount -t nfs -o vers=3,proto=tcp,nconnect=1  ai.ps-lab.local:/ifs/data/ai /mnt/tcp1
sudo mount -t nfs -o vers=3,proto=tcp,nconnect=16 ai.ps-lab.local:/ifs/data/ai /mnt/tcp16
for m in tcp1 tcp16; do
  fio --name=seqread --directory=/mnt/$m --rw=read --bs=1M --size=8G --numjobs=8 --iodepth=32 --ioengine=libaio --direct=1 --group_reporting | egrep "READ:|lat \(usec\): min"
done
```

### Step 3 - NFS over RDMA
```bash
sudo modprobe xprtrdma
sudo mount -t nfs -o vers=3,proto=rdma,port=20049,nconnect=16 ai.ps-lab.local:/ifs/data/ai /mnt/rdma
fio --name=seqread --directory=/mnt/rdma --rw=read --bs=1M --size=8G --numjobs=8 --iodepth=32 --ioengine=libaio --direct=1 --group_reporting | egrep "READ:|lat"
```

### Step 4 - GPUDirect Storage
```bash
/usr/local/cuda/gds/tools/gdscheck -p        # NVMe/NFS RDMA support must show "Supported"
# -x 0 = GPUDirect (storage -> GPU memory), -x 1 = CPU only, -x 2 = CPU -> GPU (bounce buffer)
for x in 0 2; do
  /usr/local/cuda/gds/tools/gdsio -D /mnt/rdma/gds -d 0 -w 8 -s 8G -i 1M -x $x -I 0     # -I 0 = read, 1 = write
done
```
Record GiB/s and the CPU utilisation (`mpstat 1` in another shell) for each mode.

### Step 5 - Checkpoint write test
Write a model-sized checkpoint (e.g. 8 x 20 GB files, as an 8-GPU job saving shards would) and time it:
```bash
time (for g in 0 1 2 3 4 5 6 7; do /usr/local/cuda/gds/tools/gdsio -f /mnt/rdma/ckpt/shard-$g -d $g -w 4 -s 20G -i 4M -x 0 -I 1 & done; wait)
```
Run the same over `/mnt/tcp16` with `-x 1`.

### Step 6 - Watch the cluster side
`isi statistics client --protocols=nfs3 --long` and `isi statistics system --nodes=all` during the runs show whether load is spread over all nodes. If it isn't, check the SmartConnect policy.

## Verify
- [ ] A results table exists: GiB/s, p99 latency and CPU % for TCP x1, TCP x16, RDMA and GDS.
- [ ] Checkpoint write time is recorded for TCP vs. GDS.

## Record for the standards
`STO-03` (GDS / RDMA required?), `STO-04` (per-node throughput targets), `NET-03` (dedicated storage network), `BCR-07` (checkpoint frequency is feasible at the measured write speed).

## Cleanup
Unmount `/mnt/tcp1 /mnt/tcp16 /mnt/rdma` and delete `/ifs/data/ai/gds` and `/ifs/data/ai/ckpt`.
