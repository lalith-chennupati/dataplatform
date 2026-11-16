# C06 - AI network fabric

| Tier | Time | Domains | Prerequisites |
|---|---|---|---|
| SIM (design-as-code checker; optional SONiC-VS in containerlab) / HW (2+ GPU nodes on a RoCE or InfiniBand back-end) | 4 h SIM, 1 day HW | NET, CMP | L01. HW: C03/C04 nodes, switch admin access, `nccl-tests`. |

The back-end fabric carries GPU-to-GPU traffic (all-reduce, all-gather) and decides how well multi-node training scales. Dell sells it as PowerSwitch with Dell Enterprise SONiC, or NVIDIA Spectrum-X Ethernet / Quantum InfiniBand with ConnectX/BlueField NICs. The SIM part checks the design and the lossless QoS settings as code; it does not move packets. **Untested here:** SONiC-VS, switch CLI and `nccl-tests` (no switches or GPUs on my VM). SONiC CLI syntax differs between community SONiC and Dell Enterprise SONiC releases; check yours.

## Steps

### Step 1 - [SIM] Design as code
Open `labs/env/fabric/design.yaml` and enter your design: GPU node count, GPUs per node, NIC speed per GPU, leaf and spine counts/ports, and the RoCEv2 QoS settings. The `policy` block holds the enterprise rules.
```bash
cd labs/env && python3 fabric/check_fabric.py
```
Expected with the shipped file: `256 GPUs, 8 leaves, 4 spines`, `oversubscription 1.00:1`, `NCCL all_reduce busbw target: >= 42.5 GB/s`, `PASS`.

### Step 2 - [SIM] Break the policy on purpose
```bash
sed 's/count: 4$/count: 2/' fabric/design.yaml > /tmp/two-spines.yaml && python3 fabric/check_fabric.py /tmp/two-spines.yaml   # FAIL: each spine needs 128 ports
sed 's/pfc_priorities: \[3\]/pfc_priorities: []/' fabric/design.yaml > /tmp/no-pfc.yaml && python3 fabric/check_fabric.py /tmp/no-pfc.yaml   # FAIL: PFC not enabled on priority 3
```
Run the checker in CI on every change to the design file. That is the "fabric config is in Git" control.

### Step 3 - [SIM] Rail-optimised layout on paper
Draw (or table) which NIC of which node goes to which leaf. In a rail-optimised design NIC *n* of every node goes to leaf *n*, so the GPUs with the same local rank talk over one switch hop. Record: max nodes per rail-group before you need a spine hop, and the cabling count (`gpu_nodes x gpus_per_node` back-end cables plus leaf-spine links).

### Step 4 - [SIM, optional] SONiC virtual switches
If your host can pull `docker-sonic-vs`, build a 2-leaf/1-spine topology with containerlab and apply the QoS intent from `design.yaml`:
```bash
# containerlab topology file sketch: kinds sonic-vs for leaf1, leaf2, spine1; links leaf1:eth1-spine1:eth1, leaf2:eth1-spine1:eth2
sudo containerlab deploy -t sonic-lab.clab.yml
docker exec -it clab-sonic-lab-leaf1 bash
config interface mtu Ethernet0 9100
config qos reload                                  # loads default lossless buffer/PFC templates
show pfc priority; show ecn; show interfaces status
```
SONiC-VS has no ASIC, so PFC/ECN commands configure the database but nothing is enforced. Use it to test automation (Ansible `dellemc.enterprise_sonic` collection or config_db JSON) - not performance.

### Step 5 - [HW] Verify host side of RoCE
On each GPU node:
```bash
ibv_devinfo | egrep 'hca_id|state|link_layer'        # PORT_ACTIVE, Ethernet (RoCE) or InfiniBand
rdma link
show_gids | grep -i v2                               # RoCEv2 GID present on the back-end IP (MLNX OFED tool)
mlnx_qos -i <iface>                                  # PFC enabled on priority 3, trust dscp
cat /sys/class/net/<iface>/mtu                       # 9000+ (host) - the switch MTU must be larger
```

### Step 6 - [HW] Switch side
Record from each leaf: PFC priority, ECN min/max thresholds, buffer profile, MTU, DSCP-to-queue map, and that the settings match `design.yaml`. Dell Enterprise SONiC example commands: `show running-configuration`, `show qos interface Eth1/1`, `show priority-flow-control statistics`. NVIDIA Spectrum-X uses `nv show qos` (Cumulus); InfiniBand uses the subnet manager (`sminfo`, `ibdiagnet`).

### Step 7 - [HW] NCCL bandwidth
```bash
git clone https://github.com/NVIDIA/nccl-tests && cd nccl-tests && make MPI=1 MPI_HOME=/usr/mpi/gcc/openmpi-* CUDA_HOME=/usr/local/cuda
# 2 nodes x 8 GPUs, one rank per GPU
mpirun -np 16 -H node002:8,node003:8 -x NCCL_DEBUG=INFO -x NCCL_IB_HCA=mlx5 -x NCCL_SOCKET_IFNAME=<mgmt-if> \
  ./build/all_reduce_perf -b 8 -e 8G -f 2 -g 1 | tee ../evidence/c06-nccl-2node.txt
grep -E 'NET/IB|NET/Socket' ../evidence/c06-nccl-2node.txt | head -3      # must say NET/IB (RDMA), not NET/Socket
```
Compare the `busbw` column at 1-8 GB message sizes with the target printed in Step 1. Repeat with 4 nodes and with one link down (Step 8). Slurm users: `srun -N2 --ntasks-per-node=8 --gpus-per-node=8 ./build/all_reduce_perf ...`.

### Step 8 - [HW] Failure and congestion
1. Shut one back-end port on a leaf during an `all_reduce_perf` loop. Record what NCCL does (hang, error, slow) and how long recovery takes after `no shutdown`.
2. Run two jobs on the same leaves and watch PFC pause and ECN-marked counters. Sustained pauses mean the ECN thresholds are too high or the buffer profile is wrong.
3. Feed the switch counters into C08.

## Verify
- [ ] `design.yaml` passes the checker and is in Git; the checker fails on a policy break.
- [ ] *(HW)* Host RoCE/IB state and switch QoS match the design.
- [ ] *(HW)* NCCL uses RDMA, and 2- and 4-node bus bandwidth meets the target.
- [ ] *(HW)* Behaviour on a link failure is recorded.

## Record for the standards
`NET-01` back-end fabric technology. `NET-02` bandwidth per GPU and the NCCL acceptance target. `NET-04` topology and oversubscription. `NET-03` storage on a separate network or not. `NET-07` DPU/SuperNIC use. `PLT-05` fabric config in Git with CI checks.

## Cleanup
SIM: `sudo containerlab destroy -t sonic-lab.clab.yml`. HW: restore shut ports, clear counters, remove test jobs.
