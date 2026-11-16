"""Lab C07: turn a GPU target into racks, IT kW, facility kW and heat load, and flag site gaps."""
import math, sys, yaml

s = yaml.safe_load(open(sys.argv[1] if len(sys.argv) > 1 else "facilities/site.yaml"))
site, gaps = s["site"], []
nodes = math.ceil(s["target_gpus"] / s["gpus_per_node"])
rack_kw = min(s["nodes_per_rack"], nodes) * s["node_max_kw"] + s["rack_extra_kw"]     # busiest compute rack
compute_racks = math.ceil(nodes / s["nodes_per_rack"])
it_max = compute_racks * s["rack_extra_kw"] + nodes * s["node_max_kw"] + s["storage_racks"] * s["storage_rack_kw"] + s["network_racks"] * s["network_rack_kw"]
it_typ = it_max - nodes * s["node_max_kw"] * (1 - s["node_typical_pct"] / 100)
print(f"{s['target_gpus']} GPUs -> {nodes} nodes in {compute_racks} compute racks + {s['storage_racks']} storage + {s['network_racks']} network")
print(f"compute rack: {rack_kw:.1f} kW max")
print(f"IT load: {it_max:.0f} kW max, {it_typ:.0f} kW typical; facility at PUE {site['pue']}: {it_max * site['pue']:.0f} kW")
print(f"heat to remove: {it_max * 3412:,.0f} BTU/h ({it_max / 3.517:.0f} tons of cooling)")
if rack_kw > site["max_kw_per_rack"]:
    fit = max(int((site["max_kw_per_rack"] - s["rack_extra_kw"]) // s["node_max_kw"]), 0)
    gaps.append(f"rack needs {rack_kw:.1f} kW but site delivers {site['max_kw_per_rack']} kW: fit {fit} node(s)/rack or upgrade power")
if site["cooling"] == "air" and rack_kw > site["air_cooling_limit_kw_per_rack"]:
    gaps.append(f"{rack_kw:.1f} kW/rack exceeds the air-cooling limit ({site['air_cooling_limit_kw_per_rack']} kW): plan rear-door or direct liquid cooling")
if it_max > site["available_it_kw"]:
    gaps.append(f"IT load {it_max:.0f} kW exceeds available {site['available_it_kw']} kW")
for g in gaps:
    print("GAP:", g)
print("site ready" if not gaps else f"{len(gaps)} gap(s) for the facilities team")
