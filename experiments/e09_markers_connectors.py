"""E09: Groundwork for `connect`.

A. Do markers render in headless PNG/PDF export? orient="auto-start-reverse"? fill="context-stroke"?
B. Do Inkscape-native connectors (inkscape:connection-start/end) re-route headless when objects move?
C. Are custom-namespace attributes preserved through an Inkscape round-trip and plain-svg export?
D. Does the query-all bbox of a path include its markers?

Run: uv run python experiments/e09_markers_connectors.py
"""
from pathlib import Path

from lxml import etree

from inksmcp.document import Document
from inksmcp.engine import Engine

OUT = Path(__file__).parent / "out"
OUT.mkdir(exist_ok=True)
eng = Engine()

SVG = """<svg xmlns="http://www.w3.org/2000/svg" xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
  xmlns:x="https://example.org/inksmcp" width="300" height="160" viewBox="0 0 300 160">
  <defs>
    <marker id="red" viewBox="0 0 10 10" refX="0" refY="5" markerWidth="4" markerHeight="4" orient="auto-start-reverse">
      <path d="M0,0 L10,5 L0,10 z" style="fill:#d00"/>
    </marker>
    <marker id="ctx" viewBox="0 0 10 10" refX="0" refY="5" markerWidth="4" markerHeight="4" orient="auto">
      <path d="M0,0 L10,5 L0,10 z" style="fill:context-stroke"/>
    </marker>
  </defs>
  <rect id="a" x="10" y="10" width="60" height="40" style="fill:#eee;stroke:#333"/>
  <rect id="b" x="200" y="10" width="60" height="40" style="fill:#eee;stroke:#333"/>
  <path id="p1" d="M 70,30 L 180,30" style="stroke:#d00;stroke-width:2;fill:none;marker-end:url(#red);marker-start:url(#red)"
        x:from="a" x:to="b"/>
  <path id="p2" d="M 70,90 L 180,90" style="stroke:#08f;stroke-width:2;fill:none;marker-end:url(#ctx)"/>
  <path id="conn" d="M 70,140 L 200,140" style="stroke:#000;stroke-width:1;fill:none"
        inkscape:connector-type="polyline" inkscape:connection-start="#a" inkscape:connection-end="#b"/>
</svg>"""
doc = Document.from_bytes(SVG.encode())

print("A. marker rendering -> e09_markers.png / .pdf (look at them)")
eng.export(doc, OUT / "e09_markers.png", width=600, background="#ffffff")
eng.export(doc, OUT / "e09_markers.pdf")

print("D. bbox of p1 (line 70..180 at y=30, markers 8 long each side):", eng.bboxes(doc)["p1"])

print("B. native connector after moving b down 60px")
eng.run_actions(doc, ["select-clear", "select-by-id:b", "transform-translate:0,60"])
print("   conn d =", doc.get("conn").get("d"))

print("C. custom attributes after round-trip:", doc.get("p1").attrib.get("{https://example.org/inksmcp}from"))
plain = eng.export(doc, OUT / "e09_plain.svg", "plain-svg").read_text(encoding="utf-8")
print("   in plain-svg:", "example.org/inksmcp" in plain)
print("   marker orient kept:", etree.tostring(doc.root.xpath("//*[@id='red']")[0])[:160])
eng.close()
