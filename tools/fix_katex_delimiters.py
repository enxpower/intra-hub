import pathlib, re

p = pathlib.Path("renderer/html_renderer.py")
s = p.read_text(encoding="utf-8")

pattern = r"delimiters:\s*\[\s*\n\s*\{.*?\}\s*,\s*\n\s*\{.*?\}\s*\n\s*\]"
m = re.search(pattern, s, flags=re.S)
if not m:
    raise SystemExit("ERROR: delimiters block not found")

block = m.group(0)
block2 = block.replace("True", "true").replace("False", "false")
block2 = block2.replace("{", "{{").replace("}", "}}")

s2 = s[:m.start()] + block2 + s[m.end():]
if s2 == s:
    print("No change needed.")
else:
    p.write_text(s2, encoding="utf-8")
    print("Patched:", p)
