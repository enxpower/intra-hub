import pathlib, re

p = pathlib.Path("renderer/html_renderer.py")
txt = p.read_text(encoding="utf-8", errors="ignore")

anchor = "delimiters: ["
i = txt.find(anchor)
if i < 0:
    raise SystemExit("ERROR: 'delimiters: [' not found.")

# Find the opening bracket after "delimiters: ["
bracket_open = txt.find("[", i)
if bracket_open < 0:
    raise SystemExit("ERROR: '[' after delimiters not found.")

# Find the closing bracket for delimiters array (first ']' after bracket_open)
bracket_close = txt.find("]", bracket_open)
if bracket_close < 0:
    raise SystemExit("ERROR: closing ']' for delimiters array not found.")

replacement = (
    "delimiters: [\n"
    "                {left: '$$', right: '$$', display: true},\n"
    "                {left: '$', right: '$', display: false}\n"
    "            ]"
)

txt2 = txt[:i] + replacement + txt[bracket_close+1:]
p.write_text(txt2, encoding="utf-8")
print("OK: delimiters array force-repaired.")
