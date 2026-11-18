"""Validate architecture/roles.yaml and generate the role matrix, the hierarchy diagram and the lab Trino policy.

  python3 tools/build_roles.py            # validate + write generated files
  python3 tools/build_roles.py --check    # CI: fail if roles.yaml is invalid or generated files are stale
"""
import argparse, json, pathlib, sys
import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
ARCH = ROOT / "architecture"
SPEC = yaml.safe_load((ARCH / "roles.yaml").read_text())
DOMAINS = [d["id"] for d in yaml.safe_load((ARCH / "data-products.yaml").read_text())["domains"]]
ENVS = SPEC["meta"]["environments"]
ROLES = {r["id"]: r for r in SPEC["roles"]}
STRENGTH = {"read": 1, "write": 2, "owner": 3}
PRIVS = {"read": ["SELECT"], "write": ["SELECT", "INSERT", "UPDATE", "DELETE"],
         "owner": ["SELECT", "INSERT", "UPDATE", "DELETE", "OWNERSHIP", "GRANT_SELECT"]}
TRINO_DIR = ROOT / "labs/env/trino/roles"


def envs_of(role):
    return role.get("envs", ENVS)


def ancestors(rid, seen=()):
    if rid in seen:
        raise ValueError(f"inheritance cycle through {rid}")
    out = []
    for parent in ROLES[rid]["inherits"]:
        out += [parent] + ancestors(parent, seen + (rid,))
    return list(dict.fromkeys(out))


def depth(rid):
    return 1 + max([depth(p) for p in ROLES[rid]["inherits"]], default=0)


def group_name(rid, env=None, domain=None):
    scope, g = ROLES[rid]["scope"], ROLES[rid].get("group", rid)
    return {"global": f"aidp-{g}", "env": f"aidp-{env}-{g}", "env-domain": f"aidp-{env}-{domain}-{g}"}[scope]


def all_groups():
    """group name -> (role, env or None, domain or None)"""
    out = {}
    for rid, r in ROLES.items():
        if r["scope"] == "global":
            out[group_name(rid)] = (rid, None, None)
        for env in envs_of(r):
            if r["scope"] == "env":
                out[group_name(rid, env)] = (rid, env, None)
            elif r["scope"] == "env-domain":
                for d in DOMAINS:
                    out[group_name(rid, env, d)] = (rid, env, d)
    return out


def grants(rid):
    """Effective trino grants of a role: its own plus every inherited role's."""
    return [g for x in [rid] + ancestors(rid) for g in ROLES[x].get("trino", [])]


def expand(group):
    """What a group may do at the query layer: schema -> access, plus flags."""
    rid, env, domain = GROUPS[group]
    out = {"schemas": {}, "system": False, "queries": set(), "unmasked": set(), "all": False}
    for g in grants(rid):
        if g.get("all"):
            out["all"] = True
        if g.get("system"):
            out["system"] = True
        out["queries"] |= set(g.get("queries", []))
        if g.get("unmasked") and domain:
            out["unmasked"].add(f"{env}_{domain}")
        if "layers" in g and domain and env in g["envs"]:
            for layer in g["layers"]:
                s = f"{env}_{domain}_{layer}"
                if STRENGTH[g["access"]] > STRENGTH.get(out["schemas"].get(s), 0):
                    out["schemas"][s] = g["access"]
    return out


def validate():
    errors = []
    for r in SPEC["roles"]:
        rid = r["id"]
        for k in ("tier", "scope", "kind", "inherits", "owner", "approver", "duration", "purpose"):
            if k not in r:
                errors.append(f"{rid}: missing {k}")
        for p in r.get("inherits", []):
            if p not in ROLES:
                errors.append(f"{rid}: inherits unknown role {p}")
            elif ROLES[p]["scope"] != r["scope"]:
                errors.append(f"{rid}: inherits {p} with a different scope")
            elif not set(envs_of(r)) <= set(envs_of(ROLES[p])):
                errors.append(f"{rid}: exists in environments where {p} does not")
        for c in r.get("privileges", {}):
            if c not in SPEC["meta"]["components"]:
                errors.append(f"{rid}: unknown component {c}")
        for e in envs_of(r):
            if e not in ENVS:
                errors.append(f"{rid}: unknown environment {e}")
    if len(ROLES) != len(SPEC["roles"]):
        errors.append("duplicate role ids")
    if errors:
        return errors
    for rid in ROLES:
        try:
            ancestors(rid)
        except ValueError as e:
            return [str(e)]
        if depth(rid) > SPEC["meta"]["max_depth"]:
            errors.append(f"{rid}: hierarchy deeper than {SPEC['meta']['max_depth']}")
        r = ROLES[rid]
        if r["kind"] == "human" and r["tier"] != "break-glass":
            for g in grants(rid):
                if "prod" in g.get("envs", []) and g["access"] != "read":
                    errors.append(f"{rid}: human role with {g['access']} access in prod (only service accounts write to prod)")
    for pair in SPEC["separation_of_duties"]:
        a, b = pair["roles"]
        for x in (a, b):
            if x not in ROLES:
                errors.append(f"separation_of_duties: unknown role {x}")
        for rid in ROLES:
            if {a, b} <= set([rid] + ancestors(rid)):
                errors.append(f"{rid}: holds both {a} and {b} through inheritance")
    for p in SPEC["personas"]:
        held = []
        for g in p["groups"]:
            if g not in GROUPS:
                errors.append(f"persona {p['user']}: unknown group {g}")
                continue
            rid = GROUPS[g][0]
            held += [rid] + ancestors(rid)
        for pair in SPEC["separation_of_duties"]:
            a, b = pair["roles"]
            if a in held and b in held:
                errors.append(f"persona {p['user']}: {a} and {b} together ({pair['why']})")
    for m in SPEC["masks"]:
        if m["product"].split(".")[0] not in DOMAINS:
            errors.append(f"mask: unknown domain in {m['product']}")
    return errors


def trino_rules():
    groups = {g: expand(g) for g in sorted(GROUPS)}
    by_strength = sorted(groups.items(), key=lambda kv: -max([STRENGTH[a] for a in kv[1]["schemas"].values()], default=0))
    catalogs = [{"group": g, "catalog": ".*", "allow": "all"} for g, x in groups.items() if x["all"]]
    for g, x in by_strength:
        if x["schemas"] and not x["all"]:
            write = any(a != "read" for a in x["schemas"].values())
            catalogs.append({"group": g, "catalog": "iceberg", "allow": "all" if write else "read-only"})
    catalogs += [{"group": g, "catalog": "system", "allow": "read-only"} for g, x in groups.items() if x["system"] and not x["all"]]
    catalogs.append({"catalog": ".*", "allow": "none"})

    schemas = [{"group": g, "owner": True} for g, x in groups.items() if x["all"]]
    schemas += [{"group": g, "schema": s, "owner": True} for g, x in groups.items() for s, a in sorted(x["schemas"].items()) if a == "owner"]

    tables = [{"group": g, "privileges": PRIVS["owner"]} for g, x in groups.items() if x["all"]]
    masked = {}
    for m in SPEC["masks"]:
        domain, table = m["product"].split(".")
        for env in ENVS:
            masked.setdefault((f"{env}_{domain}_{m['layer']}", table, f"{env}_{domain}"), []).append(
                {"name": m["column"], "mask": m["mask"]})
    for (schema, table, envdom), cols in sorted(masked.items()):
        rows = []
        for g, x in groups.items():
            if x["all"]:
                continue
            access = x["schemas"].get(schema)
            clear = envdom in x["unmasked"]
            if clear and not access:
                access = "read"
            if access:
                rows.append((not clear, -STRENGTH[access], g, access, clear))
        for _, _, g, access, clear in sorted(rows):
            rule = {"group": g, "catalog": "iceberg", "schema": schema, "table": table, "privileges": PRIVS[access]}
            if not clear:
                rule["columns"] = cols
            tables.append(rule)
    for g, x in by_strength:
        if not x["all"]:
            tables += [{"group": g, "catalog": "iceberg", "schema": s, "privileges": PRIVS[a]}
                       for s, a in sorted(x["schemas"].items(), key=lambda kv: -STRENGTH[kv[1]])]

    tables += [{"group": g, "catalog": "system", "privileges": ["SELECT"]} for g, x in groups.items() if x["system"] and not x["all"]]

    queries = [{"group": g, "allow": ["execute", "view", "kill"]} for g, x in groups.items() if x["all"]]
    queries += [{"group": g, "allow": ["execute"] + sorted(x["queries"], reverse=True)}
                for g, x in groups.items() if x["queries"] and not x["all"]]
    queries.append({"allow": ["execute"]})
    return {"catalogs": catalogs, "schemas": schemas, "tables": tables, "queries": queries}


def group_file():
    members = {}
    for p in SPEC["personas"]:
        for g in p["groups"]:
            members.setdefault(g, []).append(p["user"])
    return "".join(f"{g}:{','.join(u)}\n" for g, u in sorted(members.items()))


def nid(rid):
    return rid.replace("-", "_")


def diagram():
    tiers = {}
    for r in SPEC["roles"]:
        tiers.setdefault(r["tier"], []).append(r)
    lines = ["%% Generated by tools/build_roles.py from architecture/roles.yaml - do not edit by hand.",
             "%% Arrow: A --> B means B extends A (B has every privilege of A). Dotted: must not be held together.",
             "flowchart TB"]
    for tier, roles in tiers.items():
        lines.append(f'  subgraph tier_{nid(tier)}["{tier}"]')
        lines.append("    direction TB")
        for r in roles:
            env = "" if envs_of(r) == ENVS else f"<br/>{'/'.join(envs_of(r))} only"
            lines.append(f'    {nid(r["id"])}["{r["id"]}<br/><small>{r["scope"]}, {r["duration"].split(" (")[0].split(",")[0]}{env}</small>"]')
        lines.append("  end")
    for r in SPEC["roles"]:
        for p in r["inherits"]:
            lines.append(f"  {nid(p)} --> {nid(r['id'])}")
    for pair in SPEC["separation_of_duties"]:
        a, b = pair["roles"]
        lines.append(f"  {nid(a)} -. SoD .- {nid(b)}")
    return "\n".join(lines) + "\n"


def access_summary(rid):
    out = []
    for g in grants(rid):
        if g.get("all"):
            out.append("everything")
        if g.get("system"):
            out.append("system catalog read")
        if g.get("queries"):
            out.append("others' queries: " + "/".join(g["queries"]))
        if g.get("unmasked"):
            out.append("PII unmasked")
        if "layers" in g:
            envs = [e for e in g["envs"] if e in envs_of(ROLES[rid])]
            if envs:
                out.append(f"{g['access']} {'/'.join(g['layers'])} in {'/'.join(envs)}")
    return "; ".join(dict.fromkeys(out)) or "-"


def matrix():
    rows = ["<!-- Generated by tools/build_roles.py from roles.yaml - do not edit by hand. -->",
            "# AIDP role and privilege matrix (sample)", "",
            f"Generated from [`roles.yaml`](roles.yaml). Design and rationale: [roles-and-privileges.md](roles-and-privileges.md). "
            f"{len(ROLES)} roles, {len(GROUPS)} groups across {len(ENVS)} environments and {len(DOMAINS)} domains.", "",
            "## Roles", "",
            "| Role | Tier | Kind | Extends | Group | Environments | Approver | Duration | Purpose |",
            "|---|---|---|---|---|---|---|---|---|"]
    for r in SPEC["roles"]:
        example = group_name(r["id"], envs_of(r)[-1], "finance")
        rows.append(f"| `{r['id']}` | {r['tier']} | {r['kind']} | {', '.join(f'`{p}`' for p in r['inherits']) or '-'} | "
                    f"`{example}` | {', '.join(envs_of(r))} | {r['approver']} | {r['duration']} | {r['purpose']} |")
    rows += ["", "## Query layer (Data Analytics Engine) - effective grants", "",
             "Schemas are `iceberg.<env>_<domain>_<layer>`; grants include inherited roles. Enforced in the lab by the generated "
             "[Trino policy](../labs/env/trino/roles/rules.json).", "",
             "| Role | Effective grants |", "|---|---|"]
    rows += [f"| `{rid}` | {access_summary(rid)} |" for rid in ROLES]
    rows += ["", "## Privileges per component", "", "Inherited privileges are marked with the role they come from.", ""]
    for c in SPEC["meta"]["components"]:
        cells = []
        for rid in ROLES:
            own = ROLES[rid].get("privileges", {}).get(c)
            inherited = [f"{ROLES[a]['privileges'][c]} *(from `{a}`)*" for a in ancestors(rid) if ROLES[a].get("privileges", {}).get(c)]
            if own or inherited:
                cells.append(f"| `{rid}` | {'; '.join(([own] if own else []) + inherited)} |")
        if cells:
            rows += [f"### {c}", "", "| Role | Privileges |", "|---|---|"] + cells + [""]
    rows += ["## Separation of duties", "", "| Must not be held together | Why |", "|---|---|"]
    rows += [f"| `{p['roles'][0]}` + `{p['roles'][1]}` | {p['why']} |" for p in SPEC["separation_of_duties"]]
    rows += ["", "## Masked columns", "", "| Product | Layer | Column | Mask |", "|---|---|---|---|"]
    rows += [f"| `{m['product']}` | {m['layer']} | `{m['column']}` | `{m['mask']}` |" for m in SPEC["masks"]]
    return "\n".join(rows) + "\n"


GROUPS = all_groups()


def outputs():
    return {ARCH / "roles-matrix.md": matrix(),
            ARCH / "diagrams/11-role-hierarchy.mmd": diagram(),
            TRINO_DIR / "rules.json": json.dumps(trino_rules(), indent=1) + "\n",
            TRINO_DIR / "group.txt": group_file()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    errors = validate()
    if errors:
        sys.exit("roles.yaml invalid:\n  " + "\n  ".join(errors))
    files = outputs()
    if args.check:
        stale = [str(f.relative_to(ROOT)) for f, t in files.items() if not f.exists() or f.read_text() != t]
        if stale:
            sys.exit("stale (run tools/build_roles.py): " + ", ".join(stale))
        print(f"roles OK: {len(ROLES)} roles, {len(GROUPS)} groups")
        return
    TRINO_DIR.mkdir(parents=True, exist_ok=True)
    for f, t in files.items():
        f.write_text(t)
        print(f"wrote {f.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
