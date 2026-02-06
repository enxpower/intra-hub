delimiters = set(' \t\r\n,.;:!?()[]{}<>"\'“”‘’、，。；：！？（）【】《》-–—_/\\|')
﻿import re, pathlib

DELIM = " \t\r\n,.;:!?()[]{}<>\"'“”‘’、，。；：！？（）【】《》-–—_/\\|"
def needs_patch(txt):
    return re.search(r"\bdelimiters\b", txt) and not re.search(r"^\s*delimiters\s*=", txt, re.M)

def patch_one(p: pathlib.Path):
    txt = p.read_text(encoding="utf-8", errors="ignore")
    if not needs_patch(txt): return False
    m = re.match(r"(?s)^((?:\s*(?:from|import)\s+[^\n]+\n)+)", txt)
    ins = f"delimiters = set({DELIM!r})\n"
    txt2 = (m.group(1) + ins + txt[m.end(1):]) if m else (ins + txt)
    p.write_text(txt2, encoding="utf-8", newline="\n")
    return True

root = pathlib.Path(".")
patched=[]
for p in root.rglob("*.py"):
    if patch_one(p): patched.append(str(p))
print("patched:", len(patched))
print("\n".join(patched))
