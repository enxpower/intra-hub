import pathlib

p = pathlib.Path("renderer/html_renderer.py")
txt = p.read_text(encoding="utf-8", errors="ignore")

s = txt.find("renderMathInElement(document.body")
if s < 0:
    raise SystemExit("ERROR: renderMathInElement anchor not found.")

ob = txt.find("{", s)
if ob < 0:
    raise SystemExit("ERROR: '{' after renderMathInElement not found.")

end = txt.find("});", ob)
if end < 0:
    raise SystemExit("ERROR: '});' after renderMathInElement not found.")

good = (
    "{\n"
    "            delimiters: [\n"
    "                {left: '$$', right: '$$', display: true},\n"
    "                {left: '$', right: '$', display: false}\n"
    "            ]\n"
    "        });"
)

txt2 = txt[:ob] + good + txt[end+3:]
p.write_text(txt2, encoding="utf-8")
print("OK: KaTeX renderMathInElement block repaired.")
