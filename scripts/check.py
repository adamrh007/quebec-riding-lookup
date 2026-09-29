"""Sanity checks on the built data. Run after build_data.py."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
R = json.load(open(ROOT / "build" / "ridings.json", encoding="utf-8"))["ridings"]
P = json.load(open(ROOT / "build" / "postal.json"))
names = [r["name"] for r in R]

def riding_for(code):
    fsa, ldu = code[:3], code[3:]
    usual, exc, _, known = P["pc"][fsa]
    for i in range(0, len(exc), 6):
        if exc[i:i + 3] == ldu:
            return names[int(exc[i + 3:i + 6])]
    return names[usual]

errors = []
if len(R) != 127:
    errors.append(f"expected 127 ridings, got {len(R)}")
for r in R:
    total = sum(r["shares"].values())
    if not 90 <= total <= 103:
        errors.append(f"{r['name']}: shares add up to {total}")
# postal codes with a known riding (public buildings / central addresses)
KNOWN = {"H2S2M6": "Gouin", "G1R4P5": "Taschereau", "J1H1A1": "Sherbrooke", "H1V3N7": "Hochelaga-Maisonneuve"}
for code, expected in KNOWN.items():
    got = riding_for(code)
    if got != expected:
        errors.append(f"{code}: expected {expected}, got {got}")

print("OK" if not errors else "\n".join(errors))
raise SystemExit(1 if errors else 0)
