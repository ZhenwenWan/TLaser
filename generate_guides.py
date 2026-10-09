"""Render the bilingual Markdown guides to PDF, preserving the original navy palette."""
from pathlib import Path
import re
from html import escape
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Paragraph, PageBreak, Preformatted, KeepTogether
from textwrap import dedent
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

ROOT = Path(__file__).resolve().parent
FONT_PATH = Path("C:/Windows/Fonts/simhei.ttf")
BG = "#0a192f"
PANEL = "#172a45"


def render(language):
    suffix = "_CN" if language == "CN" else ""
    source = ROOT / "Doc" / f"TLaser_User_Manual{suffix}.md"
    output = source.with_suffix(".pdf")
    if FONT_PATH.exists():
        pdfmetrics.registerFont(TTFont("Guide", str(FONT_PATH)))
        font = "Guide"
    elif language == "CN":
        raise RuntimeError("Install a TrueType Chinese font and configure FONT_PATH before rendering.")
    else:
        font = "Helvetica"
    styles = {
        "body": ParagraphStyle("body", fontName=font, fontSize=10, leading=15,
                               textColor=HexColor("#e6f1ff"), spaceAfter=8, wordWrap="CJK"),
        "h1": ParagraphStyle("h1", fontName=font, fontSize=24, leading=30,
                             textColor=HexColor("#64ffda"), spaceAfter=15, keepWithNext=True),
        "h2": ParagraphStyle("h2", fontName=font, fontSize=15, leading=21,
                             textColor=HexColor("#64ffda"), spaceBefore=10, spaceAfter=10, keepWithNext=True),
        "h3": ParagraphStyle("h3", fontName=font, fontSize=11, leading=17,
                             textColor=HexColor("#64ffda"), spaceBefore=7, spaceAfter=7, keepWithNext=True),
        "code": ParagraphStyle("code", fontName="Courier", fontSize=8.4, leading=12,
                               textColor=HexColor("#64ffda"), backColor=HexColor(PANEL),
                               borderPadding=8, spaceBefore=5, spaceAfter=12),
    }

    def inline(text):
        text = text.replace(r"\frac{d^2P}{dz^2}", "d²P/dz²")
        text = re.sub(r"\\text\{([^}]+)\}", r"\1", text)
        for before, after in [(r"\Gamma", "Gamma"), (r"\alpha_i", "alpha_i"),
                              (r"\mu", "micro"), (r"\in", "in"), (r"\,", " "), ("$", "")]:
            text = text.replace(before, after)
        text = escape(text)
        text = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", text)
        text = re.sub(r"`([^`]+)`", r"<font color='#64ffda'>\1</font>", text)
        return text

    story, code, in_code = [], [], False
    for line in source.read_text(encoding="utf-8").splitlines():
        if line.lstrip().startswith("```"):
            if in_code:
                story.append(KeepTogether([Preformatted(dedent("\n".join(code)), styles["code"])]))
                code = []
            in_code = not in_code
        elif in_code:
            code.append(line)
        elif line == "<!-- pagebreak -->":
            story.append(PageBreak())
        elif line.startswith("### "):
            story.append(Paragraph(inline(line[4:]), styles["h3"]))
        elif line.startswith("## "):
            story.append(Paragraph(inline(line[3:]), styles["h2"]))
        elif line.startswith("# "):
            story.append(Paragraph(inline(line[2:]), styles["h1"]))
        elif line.strip() and line.strip() not in ("---", "$$", "> [!NOTE]"):
            story.append(Paragraph(inline(line.removeprefix("> ")), styles["body"]))

    for index, element in enumerate(story):
        if isinstance(element, Paragraph) and element.getPlainText() in ("Troubleshooting and limits", "问题排查与限制"):
            story = story[:index] + [KeepTogether(story[index:])]
            break

    def decorate(pdf, doc):
        pdf.saveState()
        pdf.setFillColor(HexColor(BG)); pdf.rect(0, 0, *doc.pagesize, fill=1, stroke=0)
        pdf.setFont(font, 8); pdf.setFillColor(HexColor("#8892b0"))
        pdf.drawString(44, 810, "TLaser | " + ("用户使用手册" if language == "CN" else "User guide"))
        pdf.drawString(44, 25, "2026-10-09 | Local ridge-device release")
        pdf.drawRightString(551, 25, str(doc.page))
        pdf.restoreState()

    doc = SimpleDocTemplate(str(output), pagesize=(595, 842), leftMargin=44, rightMargin=44,
                            topMargin=52, bottomMargin=48, title="TLaser User Guide", author="TLaser")
    doc.build(story, onFirstPage=decorate, onLaterPages=decorate)
    return output


if __name__ == "__main__":
    for language in ("EN", "CN"):
        print(render(language))
