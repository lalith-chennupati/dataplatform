#!/usr/bin/env python3
"""Build the AI Factory standards questionnaire (XLSX, DOCX, Markdown) from questionnaire/questions.yaml."""
from pathlib import Path

import yaml
from docx import Document
from docx.enum.section import WD_ORIENT
from docx.shared import Pt, RGBColor
from openpyxl import Workbook
from openpyxl.formatting.rule import CellIsRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "questionnaire" / "questions.yaml"
OUT = ROOT / "questionnaire"
STEM = "ai-factory-standards-questionnaire"

TYPE_LABEL = {"yn": "Yes / No / Partial", "choice": "Single choice", "multi": "Multi-select", "text": "Free text", "number": "Number"}
STATUS = ["Not started", "In progress", "Answered", "Needs follow-up", "N/A"]

HDR_FILL = PatternFill("solid", fgColor="0B3D91")
DOM_FILL = PatternFill("solid", fgColor="DCE6F5")
INPUT_FILL = PatternFill("solid", fgColor="FFF8E1")
HDR_FONT = Font(bold=True, color="FFFFFF")
THIN = Side(style="thin", color="B0B7C3")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
WRAP = Alignment(wrap_text=True, vertical="top")


def load():
    data = yaml.safe_load(SRC.read_text())
    for d in data["domains"]:
        for i, q in enumerate(d["questions"], 1):
            q["id"] = f"{d['code']}-{i:02d}"
            q.setdefault("o", data["meta"]["yn_options"] if q["t"] == "yn" else [])
    return data


def header(ws, row, cols, widths=None):
    for c, name in enumerate(cols, 1):
        cell = ws.cell(row=row, column=c, value=name)
        cell.fill, cell.font, cell.alignment, cell.border = HDR_FILL, HDR_FONT, WRAP, BORDER
    for c, w in enumerate(widths or [], 1):
        ws.column_dimensions[get_column_letter(c)].width = w
    ws.freeze_panes = ws.cell(row=row + 1, column=1)


def build_xlsx(data):
    meta = data["meta"]
    wb = Workbook()

    ws = wb.active
    ws.title = "Instructions"
    ws.column_dimensions["A"].width = 26
    ws.column_dimensions["B"].width = 110
    ws["A1"] = meta["title"]
    ws["A1"].font = Font(bold=True, size=16, color="0B3D91")
    rows = [
        ("Version", meta["version"]),
        ("Purpose", "Collect the decisions, constraints and current-state facts needed to write the enterprise standards (STD-01..STD-20) for the Dell AI Factory and AI Data Platform."),
        ("How to use", "1) Fill in 'Respondents'. 2) Filter 'Questionnaire' by Owner role and send each stakeholder their rows. 3) Answer in the yellow columns; pick from the drop-down where offered. 4) Rate current and target maturity per domain in 'Maturity'. 5) The standards author uses 'Standards Map' to turn answers into standard clauses."),
        ("Answer columns", "Response = the decision or fact. Evidence / link = existing policy, diagram or document. Status = progress. Notes / open issues = follow-ups, dependencies, risks."),
        ("Unknown answers", "Answer 'Unknown' or leave a note rather than guessing - unknowns become decisions for the AI steering committee."),
        ("Dell component names", "Product names reflect Dell's public portfolio at authoring time; verify with your Dell account team. See 'Dell Components'."),
        ("Source", "Generated from questionnaire/questions.yaml by tools/build_questionnaire.py - edit the YAML, not this workbook, for structural changes."),
    ]
    r = 3
    for k, v in rows:
        ws.cell(row=r, column=1, value=k).font = Font(bold=True)
        ws.cell(row=r, column=2, value=v).alignment = WRAP
        r += 1
    r += 1
    ws.cell(row=r, column=1, value="Priority").font = Font(bold=True, size=12)
    for k, v in meta["priorities"].items():
        r += 1
        ws.cell(row=r, column=1, value=k)
        ws.cell(row=r, column=2, value=v)
    r += 2
    ws.cell(row=r, column=1, value="Roles").font = Font(bold=True, size=12)
    for k, v in meta["roles"].items():
        r += 1
        ws.cell(row=r, column=1, value=k)
        ws.cell(row=r, column=2, value=v)

    ws = wb.create_sheet("Respondents")
    header(ws, 1, ["Role code", "Role", "Name", "Title", "Business unit", "Email", "Interview date", "Questions assigned"], [10, 42, 24, 24, 20, 28, 14, 12])
    for i, (k, v) in enumerate(meta["roles"].items(), 2):
        ws.cell(row=i, column=1, value=k)
        ws.cell(row=i, column=2, value=v)
        ws.cell(row=i, column=8, value=f'=COUNTIF(Questionnaire!$H:$H,A{i})')
        for c in range(3, 8):
            ws.cell(row=i, column=c).fill = INPUT_FILL
        for c in range(1, 9):
            ws.cell(row=i, column=c).border = BORDER

    ws = wb.create_sheet("Questionnaire")
    cols = ["ID", "Domain", "Question", "Answer type", "Options", "Standard clause it drives", "Target standard", "Owner", "Priority",
            "Response", "Evidence / link", "Status", "Notes / open issues"]
    header(ws, 1, cols, [9, 22, 60, 14, 38, 38, 30, 8, 8, 40, 26, 15, 34])
    status_dv = DataValidation(type="list", formula1='"' + ",".join(STATUS) + '"', allow_blank=True)
    ws.add_data_validation(status_dv)
    r = 2
    for d in data["domains"]:
        for q in d["questions"]:
            vals = [q["id"], d["name"], q["q"], TYPE_LABEL[q["t"]], "; ".join(q["o"]), q["std"], d["standard"], q["own"], q["p"],
                    None, None, "Not started", None]
            for c, v in enumerate(vals, 1):
                cell = ws.cell(row=r, column=c, value=v)
                cell.alignment, cell.border = WRAP, BORDER
                if c >= 10:
                    cell.fill = INPUT_FILL
            if q["t"] in ("yn", "choice"):
                opts = ",".join(o.replace(",", " ") for o in q["o"])
                if len(opts) <= 250:
                    dv = DataValidation(type="list", formula1=f'"{opts}"', allow_blank=True, showErrorMessage=False)
                    ws.add_data_validation(dv)
                    dv.add(ws.cell(row=r, column=10))
            status_dv.add(ws.cell(row=r, column=12))
            r += 1
    last = r - 1
    ws.auto_filter.ref = f"A1:{get_column_letter(len(cols))}{last}"
    red = PatternFill("solid", fgColor="F8D7DA")
    ws.conditional_formatting.add(f"I2:I{last}", CellIsRule(operator="equal", formula=['"P1"'], fill=red))

    ws = wb.create_sheet("Maturity")
    header(ws, 1, ["Code", "Domain", "Target standard", "Questions", "Answered", "% complete", "Current maturity (1-5)", "Target maturity (1-5)", "Gap", "Key gaps / decisions"],
           [8, 40, 46, 11, 11, 11, 14, 14, 8, 50])
    mat_dv = DataValidation(type="whole", operator="between", formula1="1", formula2="5", allow_blank=True)
    ws.add_data_validation(mat_dv)
    for i, d in enumerate(data["domains"], 2):
        ws.cell(row=i, column=1, value=d["code"])
        ws.cell(row=i, column=2, value=d["name"])
        ws.cell(row=i, column=3, value=d["standard"])
        ws.cell(row=i, column=4, value=f'=COUNTIF(Questionnaire!$B:$B,B{i})')
        ws.cell(row=i, column=5, value=f'=COUNTIFS(Questionnaire!$B:$B,B{i},Questionnaire!$L:$L,"Answered")')
        ws.cell(row=i, column=6, value=f'=IF(D{i}=0,0,E{i}/D{i})').number_format = "0%"
        ws.cell(row=i, column=9, value=f'=IF(OR(G{i}="",H{i}=""),"",H{i}-G{i})')
        for c in (7, 8, 10):
            ws.cell(row=i, column=c).fill = INPUT_FILL
        mat_dv.add(f"G{i}:H{i}")
        for c in range(1, 11):
            ws.cell(row=i, column=c).border, ws.cell(row=i, column=c).alignment = BORDER, WRAP
    n = len(data["domains"]) + 2
    ws.cell(row=n + 1, column=1, value="Maturity scale").font = Font(bold=True)
    for j, (k, v) in enumerate(meta["maturity"].items(), n + 2):
        ws.cell(row=j, column=1, value=k)
        ws.cell(row=j, column=2, value=v)

    ws = wb.create_sheet("Standards Map")
    header(ws, 1, ["Target standard", "Domain", "Intent", "P1 questions", "Clauses to write"], [46, 40, 60, 10, 90])
    for i, d in enumerate(data["domains"], 2):
        vals = [d["standard"], d["name"], d["intent"], sum(q["p"] == "P1" for q in d["questions"]),
                "\n".join(f"{q['id']}: {q['std']}" for q in d["questions"])]
        for c, v in enumerate(vals, 1):
            cell = ws.cell(row=i, column=c, value=v)
            cell.alignment, cell.border = WRAP, BORDER

    ws = wb.create_sheet("Dell Components")
    header(ws, 1, ["Layer", "Component", "Role in the AI Factory", "Questionnaire domains"], [16, 46, 80, 20])
    for i, c in enumerate(data["components"], 2):
        for j, v in enumerate([c["layer"], c["component"], c["role"], ", ".join(c["domains"])], 1):
            cell = ws.cell(row=i, column=j, value=v)
            cell.alignment, cell.border = WRAP, BORDER

    path = OUT / f"{STEM}.xlsx"
    wb.save(path)
    return path


def build_docx(data):
    meta = data["meta"]
    doc = Document()
    sec = doc.sections[0]
    sec.orientation = WD_ORIENT.LANDSCAPE
    sec.page_width, sec.page_height = sec.page_height, sec.page_width
    doc.styles["Normal"].font.name = "Calibri"
    doc.styles["Normal"].font.size = Pt(10)

    doc.add_heading(meta["title"], 0)
    doc.add_paragraph(f"Version {meta['version']}. Interview / workshop edition - record answers in the Response column. "
                      "The Excel edition has drop-downs, progress tracking and a maturity scorecard.")
    doc.add_heading("Priority legend", 2)
    for k, v in meta["priorities"].items():
        doc.add_paragraph(f"{k} - {v}", style="List Bullet")
    doc.add_heading("Respondent roles", 2)
    t = doc.add_table(rows=1, cols=2, style="Light Grid Accent 1")
    t.rows[0].cells[0].text, t.rows[0].cells[1].text = "Code", "Role"
    for k, v in meta["roles"].items():
        row = t.add_row().cells
        row[0].text, row[1].text = k, v

    for d in data["domains"]:
        doc.add_page_break()
        doc.add_heading(f"{d['code']} - {d['name']}", 1)
        p = doc.add_paragraph()
        p.add_run("Target standard: ").bold = True
        p.add_run(d["standard"])
        p = doc.add_paragraph()
        p.add_run("Intent: ").bold = True
        p.add_run(d["intent"])
        t = doc.add_table(rows=1, cols=6, style="Light Grid Accent 1")
        for c, h in enumerate(["ID", "Question", "Options", "Owner", "Pri.", "Response"]):
            t.rows[0].cells[c].text = h
        for q in d["questions"]:
            row = t.add_row().cells
            row[0].text = q["id"]
            row[1].text = q["q"]
            row[2].text = (" / ".join(q["o"]) if q["o"] else TYPE_LABEL[q["t"]])
            row[3].text = q["own"]
            row[4].text = q["p"]
            row[5].text = ""
            for cell in row[:5]:
                for para in cell.paragraphs:
                    for run in para.runs:
                        run.font.size = Pt(9)
            if q["p"] == "P1":
                row[4].paragraphs[0].runs[0].font.color.rgb = RGBColor(0xB0, 0x00, 0x20)
        p = doc.add_paragraph()
        p.add_run("Current maturity (1-5): ____    Target maturity (1-5): ____    Key gaps: ").bold = True

    doc.add_page_break()
    doc.add_heading("Maturity scale", 1)
    for k, v in meta["maturity"].items():
        doc.add_paragraph(f"{k} - {v}", style="List Bullet")
    doc.add_heading("Dell AI Factory component reference", 1)
    doc.add_paragraph("Verify product names and capabilities with your Dell account team.")
    t = doc.add_table(rows=1, cols=4, style="Light Grid Accent 1")
    for c, h in enumerate(["Layer", "Component", "Role", "Domains"]):
        t.rows[0].cells[c].text = h
    for c in data["components"]:
        row = t.add_row().cells
        row[0].text, row[1].text, row[2].text, row[3].text = c["layer"], c["component"], c["role"], ", ".join(c["domains"])

    path = OUT / f"{STEM}.docx"
    doc.save(path)
    return path


def build_md(data):
    meta = data["meta"]
    total = sum(len(d["questions"]) for d in data["domains"])
    p1 = sum(q["p"] == "P1" for d in data["domains"] for q in d["questions"])
    out = [f"# {meta['title']}", "",
           f"Version {meta['version']} - {total} questions across {len(data['domains'])} domains ({p1} are P1).",
           "", "> Generated from `questionnaire/questions.yaml` by `tools/build_questionnaire.py`. Do not edit by hand.", "",
           "**Priority:** " + " | ".join(f"**{k}** {v}" for k, v in meta["priorities"].items()), "",
           "**Roles:** " + ", ".join(f"`{k}` {v}" for k, v in meta["roles"].items()), "", "## Domains", ""]
    for d in data["domains"]:
        anchor = f"{d['code']} - {d['name']}".lower()
        anchor = "".join(ch for ch in anchor if ch.isalnum() or ch in " -").replace(" ", "-")
        out.append(f"- [{d['code']} - {d['name']}](#{anchor}) -> {d['standard']}")
    for d in data["domains"]:
        out += ["", f"## {d['code']} - {d['name']}", "", f"**Target standard:** {d['standard']}  ", f"**Intent:** {d['intent']}", "",
                "| ID | Question | Options | Owner | Pri. | Drives |", "|---|---|---|---|---|---|"]
        for q in d["questions"]:
            opts = " / ".join(q["o"]) if q["o"] else TYPE_LABEL[q["t"]]
            out.append(f"| {q['id']} | {q['q']} | {opts} | {q['own']} | {q['p']} | {q['std']} |".replace("\n", " "))
    out += ["", "## Maturity scale", ""] + [f"{k}. {v}" for k, v in meta["maturity"].items()]
    out += ["", "## Dell AI Factory component reference", "",
            "Verify names and capabilities with your Dell account team.", "",
            "| Layer | Component | Role | Domains |", "|---|---|---|---|"]
    out += [f"| {c['layer']} | {c['component']} | {c['role']} | {', '.join(c['domains'])} |" for c in data["components"]]
    path = OUT / f"{STEM}.md"
    path.write_text("\n".join(out) + "\n")
    return path


def main():
    data = load()
    for p in (build_xlsx(data), build_docx(data), build_md(data)):
        print(f"wrote {p.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
