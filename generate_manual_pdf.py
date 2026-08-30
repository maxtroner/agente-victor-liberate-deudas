from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Preformatted

source = Path(__file__).with_name("MANUAL_RESPALDO.md")
target = source.with_suffix(".pdf")
styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="SmallCode", parent=styles["Code"], fontSize=7.5, leading=9))
story = []
in_code = False
code = []

for raw in source.read_text(encoding="utf-8").splitlines():
    line = raw.rstrip()
    if line.startswith("```"):
        if in_code:
            story.append(Preformatted("\n".join(code), styles["SmallCode"]))
            story.append(Spacer(1, 3 * mm))
            code = []
        in_code = not in_code
        continue
    if in_code:
        code.append(line)
    elif line.startswith("# "):
        story.append(Paragraph(escape(line[2:]), styles["Title"]))
    elif line.startswith("## "):
        story.append(Paragraph(escape(line[3:]), styles["Heading2"]))
    elif line.startswith("- "):
        story.append(Paragraph("&#8226; " + escape(line[2:]), styles["BodyText"]))
    elif line:
        story.append(Paragraph(escape(line), styles["BodyText"]))
    story.append(Spacer(1, 1.5 * mm))

doc = SimpleDocTemplate(str(target), pagesize=A4, rightMargin=18 * mm, leftMargin=18 * mm, topMargin=16 * mm, bottomMargin=16 * mm)
doc.build(story)
print(target)
