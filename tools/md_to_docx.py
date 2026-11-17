"""Convert an architecture Markdown document to Word, embedding the PNG render of each diagram.

  python3 tools/md_to_docx.py architecture/identity-keycloak.md

Supports the subset used in architecture/: headings, paragraphs, bullet and check lists, tables,
block quotes, fenced code, images, **bold** and `code`. Writes <name>.docx next to the source.
"""
import pathlib, re, sys
from docx import Document
from docx.shared import Pt, Inches, RGBColor

INLINE = re.compile(r"(\*\*[^*]+\*\*|`[^`]+`|\[[^\]]+\]\([^)]+\))")


def add_inline(par, text):
    for part in INLINE.split(text):
        if not part:
            continue
        if part.startswith("**"):
            par.add_run(part[2:-2]).bold = True
        elif part.startswith("`"):
            run = par.add_run(part[1:-1])
            run.font.name = "Consolas"
            run.font.size = Pt(9)
        elif part.startswith("["):
            par.add_run(re.match(r"\[([^\]]+)\]", part).group(1))
        else:
            par.add_run(part)


def cells(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def convert(src):
    doc = Document()
    doc.styles["Normal"].font.name = "Calibri"
    doc.styles["Normal"].font.size = Pt(10)
    lines = src.read_text().splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("```"):
            code = []
            i += 1
            while not lines[i].startswith("```"):
                code.append(lines[i])
                i += 1
            run = doc.add_paragraph().add_run("\n".join(code))
            run.font.name = "Consolas"
            run.font.size = Pt(8)
        elif m := re.match(r"(#{1,4}) (.*)", line):
            doc.add_heading(m.group(2), level=len(m.group(1)) - 1 if len(m.group(1)) > 1 else 0)
        elif m := re.match(r"!\[([^\]]*)\]\(([^)]+)\)", line):
            doc.add_picture(str(src.parent / m.group(2)), width=Inches(6.5))
            doc.add_paragraph(m.group(1)).italic = True
        elif line.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                if not re.match(r"^\|[\s:|-]+\|$", lines[i]):
                    rows.append(cells(lines[i]))
                i += 1
            table = doc.add_table(rows=len(rows), cols=len(rows[0]))
            table.style = "Light Grid Accent 1"
            for r, row in enumerate(rows):
                for c, text in enumerate(row[:len(rows[0])]):
                    par = table.cell(r, c).paragraphs[0]
                    add_inline(par, text)
                    for run in par.runs:
                        run.font.size = Pt(8.5)
                        run.bold = run.bold or r == 0
            continue
        elif line.startswith("> "):
            par = doc.add_paragraph(style="Intense Quote")
            add_inline(par, line[2:])
        elif m := re.match(r"\s*- (\[ \] )?(.*)", line):
            par = doc.add_paragraph(style="List Bullet")
            add_inline(par, ("☐ " if m.group(1) else "") + m.group(2))
        elif line.strip():
            add_inline(doc.add_paragraph(), line)
        i += 1
    out = src.with_suffix(".docx")
    doc.core_properties.title = lines[0].lstrip("# ")
    doc.save(out)
    print(f"wrote {out}")


if __name__ == "__main__":
    for arg in sys.argv[1:] or ["architecture/identity-keycloak.md"]:
        convert(pathlib.Path(arg).resolve())
