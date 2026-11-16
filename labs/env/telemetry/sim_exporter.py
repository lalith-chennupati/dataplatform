"""Lab C08: one Prometheus exporter that stands in for iDRAC telemetry, DCGM, storage and switch metrics.

Real Redfish values come from the mockup (REDFISH_URL). GPU, storage and fabric values are simulated.
Inject faults with HTTP GET, e.g.:
  curl 'localhost:9101/fault?gpu=3&temp=96'        # throttle GPU 3 (temperature + clock drop)
  curl 'localhost:9101/fault?xid=79&gpu=5'         # GPU fell off the bus
  curl 'localhost:9101/fault?quota=0.97'           # storage quota 97% full
  curl 'localhost:9101/fault?link=rail2&up=0'      # flap a back-end link
  curl 'localhost:9101/fault?reset=1'              # clear all faults
"""
import json, os, random, urllib.parse, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

REDFISH = os.environ.get("REDFISH_URL", "http://redfish:8000/redfish/v1")
NODE, GPUS, RAILS = os.environ.get("NODE", "xe-node-01"), 8, ["rail0", "rail1", "rail2", "rail3"]
state = {}


def reset():
    state.clear()
    state.update(temp={}, xid={}, quota=0.62, links={r: 1 for r in RAILS}, pfc={r: 0 for r in RAILS})


def redfish(path):
    try:
        with urllib.request.urlopen(f"{REDFISH}{path}", timeout=3) as r:
            return json.load(r)
    except Exception:
        return None


def metrics():
    out = []

    def add(name, labels, v):
        lbl = ",".join('%s="%s"' % kv for kv in labels.items())
        out.append("%s{%s} %s" % (name, lbl, v))

    sysinfo = redfish("/Systems/437XR1138R2")
    add("redfish_up", {"node": NODE}, int(sysinfo is not None))
    if sysinfo:
        add("redfish_system_health_ok", {"node": NODE}, int(sysinfo["Status"]["Health"] == "OK"))
    thermal = redfish("/Chassis/1U/Thermal") or {}
    for t in thermal.get("Temperatures", []):
        if t.get("ReadingCelsius") is not None:
            add("redfish_temperature_celsius", {"node": NODE, "sensor": t["Name"]}, t["ReadingCelsius"])
    power = redfish("/Chassis/1U/Power") or {}
    for p in power.get("PowerControl", []):
        add("redfish_power_consumed_watts", {"node": NODE}, p.get("PowerConsumedWatts", 0))
    for g in range(GPUS):
        lab = {"node": NODE, "gpu": str(g), "modelName": "SIM-H100"}
        temp = state["temp"].get(g, random.randint(55, 68))
        add("DCGM_FI_DEV_GPU_TEMP", lab, temp)
        add("DCGM_FI_DEV_GPU_UTIL", lab, random.randint(70, 98))
        add("DCGM_FI_DEV_SM_CLOCK", lab, 1980 if temp < 90 else 1100)
        add("DCGM_FI_DEV_POWER_USAGE", lab, random.randint(480, 690))
        add("DCGM_FI_DEV_XID_ERRORS", lab, state["xid"].get(g, 0))
        add("DCGM_FI_DEV_ECC_DBE_VOL_TOTAL", lab, 0)
    add("storage_quota_used_ratio", {"path": "/ifs/ai/team-a"}, state["quota"])
    for r, up in state["links"].items():
        add("fabric_link_oper_up", {"switch": "leaf1", "port": r}, up)
        if not up:
            state["pfc"][r] += random.randint(1000, 5000)       # counter only grows, like a real switch counter
        add("fabric_pfc_pause_frames_total", {"switch": "leaf1", "port": r}, state["pfc"][r])
    return "\n".join(out) + "\n"


class H(BaseHTTPRequestHandler):
    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        q = {k: v[0] for k, v in urllib.parse.parse_qs(u.query).items()}
        if u.path == "/fault":
            if "reset" in q: reset()
            if "temp" in q: state["temp"][int(q.get("gpu", 0))] = int(q["temp"])
            if "xid" in q: state["xid"][int(q.get("gpu", 0))] = int(q["xid"])
            if "quota" in q: state["quota"] = float(q["quota"])
            if "link" in q and q["link"] not in RAILS:
                self.send_response(400); self.end_headers()
                self.wfile.write(f"unknown link {q['link']}; use one of {RAILS}\n".encode()); return
            if "link" in q: state["links"][q["link"]] = int(q.get("up", 0))
            body = json.dumps(state, default=str)
        else:
            body = metrics()
        self.send_response(200); self.send_header("Content-Type", "text/plain; version=0.0.4"); self.end_headers()
        self.wfile.write(body.encode())

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    reset()
    ThreadingHTTPServer(("0.0.0.0", 9101), H).serve_forever()
