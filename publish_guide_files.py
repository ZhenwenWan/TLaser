"""Copy the six validated static publication files after checking source-page hashes."""
from pathlib import Path
import hashlib
import json
from shutil import copyfile
import argparse
import subprocess
parser = argparse.ArgumentParser()
parser.add_argument("--push", action="store_true", help="Commit and publish only the six staged static files")
args = parser.parse_args()
ROOT = Path(__file__).resolve().parent
STAGE = ROOT / "web_publish"
PAGES = ROOT.parent / "Lasers" / "Pages"
manifest = json.loads((STAGE/"source_manifest.json").read_text())
for name, digest in manifest.items():
    assert hashlib.sha256((PAGES/name).read_bytes()).hexdigest() == digest, f"Page changed since staging: {name}"
names = ["TLaser.html", "TLaser_CN.html", "TLaser_User_Manual.pdf", "TLaser_User_Manual_CN.pdf",
         "TLaser_User_Manual.md", "TLaser_User_Manual_CN.md"]
for name in ("TLaser.html", "TLaser_CN.html"):
    html = (STAGE/name).read_text(encoding="utf-8")
    assert html.count('id="device-model-release"') == 1
    assert "./run_tlaser.ps1" in html
for name in names:
    source, target = STAGE/name, PAGES/name
    copyfile(source, target)
    assert hashlib.sha256(source.read_bytes()).digest() == hashlib.sha256(target.read_bytes()).digest()
print("Copied and verified the six TLaser static page/guide files.")
if args.push:
    prefix = ["git", "-c", f"safe.directory={PAGES.as_posix()}", "-C", str(PAGES)]
    subprocess.run(prefix+["add", "--", *names], check=True)
    subprocess.run(prefix+["commit", "-m", "Restore validated shared device release sections on TLaser pages"], check=True)
    subprocess.run(prefix+["push", "origin", "main"], check=True)
