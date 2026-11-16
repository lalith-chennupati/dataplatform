"""Lab C06: check a back-end fabric design (design.yaml) for port budget, oversubscription and RoCE QoS policy."""
import math, sys, yaml

d = yaml.safe_load(open(sys.argv[1] if len(sys.argv) > 1 else "fabric/design.yaml"))
p, q, leaf, spine = d["policy"], d["qos"], d["leaf"], d["spine"]
errors, gpus = [], d["gpu_nodes"] * d["gpus_per_node"]
down = math.ceil(gpus / leaf["count"])                        # GPU-facing ports on the busiest leaf
up_ports = leaf["ports"] - down
up = min(up_ports, spine["count"] * (up_ports // spine["count"]))  # uplinks spread evenly over spines
over = (down * min(d["nic_gbps_per_gpu"], leaf["port_gbps"])) / max(up * spine["port_gbps"], 1)
spine_ports = leaf["count"] * up // spine["count"]
print(f"{d['name']}: {gpus} GPUs, {leaf['count']} leaves, {spine['count']} spines")
print(f"  per leaf: {down} down x {d['nic_gbps_per_gpu']}G, {up} up x {spine['port_gbps']}G -> oversubscription {over:.2f}:1")
print(f"  per spine: {spine_ports} ports used")
if d["rail_optimised"] and leaf["count"] % d["gpus_per_node"]:
    errors.append(f"rail-optimised needs leaf count to be a multiple of gpus_per_node ({d['gpus_per_node']})")
if down > leaf["ports"]:
    errors.append(f"leaf needs {down} GPU ports but has {leaf['ports']}")
if leaf["port_gbps"] < d["nic_gbps_per_gpu"]:
    errors.append(f"leaf ports ({leaf['port_gbps']}G) are slower than the GPU NICs ({d['nic_gbps_per_gpu']}G)")
if spine_ports > spine["ports"]:
    errors.append(f"each spine needs {spine_ports} ports but has {spine['ports']}")
if over > p["max_oversubscription"]:
    errors.append(f"oversubscription {over:.2f}:1 exceeds policy {p['max_oversubscription']}:1")
if p["require_pfc_priority"] not in q["pfc_priorities"]:
    errors.append(f"PFC not enabled on priority {p['require_pfc_priority']}")
if q["mtu"] < p["require_mtu_min"]:
    errors.append(f"MTU {q['mtu']} below {p['require_mtu_min']}")
if not (q["ecn"]["enabled"] and q["dcqcn"]):
    errors.append("ECN/DCQCN must be enabled for RoCEv2")
target = d["nic_gbps_per_gpu"] / 8 * p["nccl_busbw_target_pct_of_line_rate"] / 100
print(f"  NCCL all_reduce busbw target: >= {target:.1f} GB/s ({p['nccl_busbw_target_pct_of_line_rate']}% of {d['nic_gbps_per_gpu']}G line rate)")
for e in errors:
    print("FAIL:", e)
print("PASS" if not errors else f"{len(errors)} policy violation(s)")
sys.exit(1 if errors else 0)
