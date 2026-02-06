import re, pathlib

p = pathlib.Path("renderer/html_renderer.py")
txt = p.read_text(encoding="utf-8", errors="ignore")

pattern = r'onload="renderMathInElement\(document\.body,\s*\{\s*delimiters:\s*\[\s*[\s\S]*?\]\s*\}\s*\);\s*"'
repl = (
    'onload="renderMathInElement(document.body, {\\n'
    '            delimiters: [\\n'
    "                {left: '\\$\\$', right: '\\$\\$', display: true},\\n"
    "                {left: '\\$', right: '\\$', display: false}\\n"
    '            ]\\n'
    '        });"'
)

m = re.search(pattern, txt)
if not m:
    raise SystemExit("ERROR: KaTeX onload block not found; aborting.")

txt2 = re.sub(pattern, repl, txt, count=1)
p.write_text(txt2, encoding="utf-8")
print("OK: KaTeX delimiters block repaired.")
