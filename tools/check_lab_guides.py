"""Check lab guides and architecture docs: every cited questionnaire ID exists and every relative Markdown link resolves.

  python3 tools/check_lab_guides.py
"""
import pathlib, re, sys
import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
q = yaml.safe_load((ROOT / "questionnaire/questions.yaml").read_text())
ids = {f"{d['code']}-{i:02d}" for d in q["domains"] for i, _ in enumerate(d["questions"], 1)}
codes = {d["code"] for d in q["domains"]}

errors = []
for md in sorted([*(ROOT / "labs").rglob("*.md"), *(ROOT / "architecture").rglob("*.md")]):
    text = md.read_text()
    for qid in set(re.findall(r"`([A-Z]{3}-\d{2})`", text)):
        if qid.split("-")[0] in codes and qid not in ids:
            errors.append(f"{md.relative_to(ROOT)}: unknown question ID {qid}")
    for target in re.findall(r"\]\(([^)#\s]+)(?:#[^)]*)?\)", text):
        if not re.match(r"[a-z]+://", target) and not (md.parent / target).exists():
            errors.append(f"{md.relative_to(ROOT)}: broken link {target}")

print("\n".join(errors) or "lab guides OK")
sys.exit(1 if errors else 0)
