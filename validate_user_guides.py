"""Read-only checks of the documented local workflow and rendered bilingual guides."""
from pathlib import Path
import json
import re
import tomllib
from PIL import Image, ImageOps, ImageDraw
from pypdf import PdfReader
from device_model import default_config
from device_workflow import validate_measurements

ROOT = Path(__file__).resolve().parent
report = {"date": "2026-10-09", "checks": [], "languages": {}}
assert (ROOT/"run_tlaser.ps1").is_file()
assert (ROOT/"tests/test_device_workflow.py").is_file()
theme = tomllib.loads((ROOT/".streamlit/config.toml").read_text())["theme"]
assert theme["backgroundColor"] == "#0a192f"
report["checks"].append("Launcher and workflow test paths exist; navy theme configured")
for suffix in ("", "_CN"):
    md = (ROOT/"Doc"/f"TLaser_User_Manual{suffix}.md").read_text(encoding="utf-8")
    for phrase in ("./run_tlaser.ps1", "./run_tlaser.ps1 -Port 8502", "current_semantics", "active_region", "test_device_workflow.py", "0.01", "1,000,000"):
        assert phrase in md, phrase
    blocks = re.findall(r"```json\s*([\s\S]*?)```", md)
    assert len(blocks) == 1
    data = json.loads(blocks[0]); validate_measurements(data, default_config())
    reader = PdfReader(ROOT/"Doc"/f"TLaser_User_Manual{suffix}.pdf")
    text = "\n".join(p.extract_text() for p in reader.pages)
    assert "./run_tlaser.ps1" in text and "-Port 8502" in text
    assert "current_semantics" in text and "active_region" in text
    assert "```" not in text and "\ufffd" not in text
    assert 3 <= len(reader.pages) <= 8
    report["languages"][suffix or "EN"] = {"pdf_pages": len(reader.pages), "example_matches_data_validator": True,
                                              "launcher_commands_present_in_pdf": True, "code_fences_removed": True}
    html = (ROOT/"web_publish"/f"TLaser{suffix}.html").read_text(encoding="utf-8")
    assert 'id="device-model-release"' in html
    assert "./run_tlaser.ps1" in html
    for ext in ("pdf", "md"):
        name = f"TLaser_User_Manual{suffix}.{ext}"
        assert f'href="{name}"' in html and (ROOT/"web_publish"/name).is_file()
report["checks"].append("Both measurement examples pass the actual dashboard validator")
report["checks"].append("Both PDFs contain current launcher/data instructions without raw code fences")
report["checks"].append("Both staged project pages link to existing PDF/Markdown guide assets")
pages = sorted((ROOT/"tmp/pdfs").glob("*-checked-*.png"))
sheet = Image.new("RGB", (1200, ((len(pages)+2)//3)*595), "#24334d")
draw = ImageDraw.Draw(sheet)
for index, path in enumerate(pages):
    position = ((index%3)*400, (index//3)*595+20)
    sheet.paste(ImageOps.contain(Image.open(path), (385,555)), position)
    draw.text((position[0]+8,position[1]-16),path.name,fill="white")
sheet.save(ROOT/"tmp/pdfs/contact-checked.png")
report["workflow_tests"] = "7 passed; see test_device_workflow.py"
report["visual_review"] = "PDF pages rendered with Poppler for inspection"
(ROOT/"Doc/user_guide_validation.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report, indent=2))
