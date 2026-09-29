"""Injects build/ridings.json and build/postal.json into src/template.html -> index.html"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
tpl = (ROOT / "src" / "template.html").read_text(encoding="utf-8")
ridings = (ROOT / "build" / "ridings.json").read_text(encoding="utf-8").replace("</", "<\\/")
postal = (ROOT / "build" / "postal.json").read_text(encoding="utf-8").replace("</", "<\\/")
(ROOT / "index.html").write_text(tpl.replace("__DATA__", ridings).replace("__PC__", postal), encoding="utf-8")
print("index.html written")
