"""E09b: Native Inkscape connectors in depth.

- Is routing computed on load from a dummy d="M 0,0"?
- polyline vs orthogonal routing; circle target (clip to shape or bbox?)
- target inside a transformed group; text target
- arrow tip placement with marker refX at the tip
- lxml-only move, then round-trip: rerouted?

Run: uv run python experiments/e09b_native_connectors.py
"""
from pathlib import Path

from inksmcp.document import Document
from inksmcp.engine import Engine

OUT = Path(__file__).parent / "out"
eng = Engine()
SVG = """<svg xmlns="http://www.w3.org/2000/svg" xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
  width="400" height="300" viewBox="0 0 400 300">
  <defs>
    <marker id="arrow" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="5" markerHeight="5"
            orient="auto-start-reverse" markerUnits="strokeWidth">
      <path d="M0,0 L10,5 L0,10 z" style="fill:context-stroke"/>
    </marker>
  </defs>
  <rect id="a" x="20" y="20" width="80" height="50" style="fill:#eef;stroke:#336;stroke-width:2"/>
  <circle id="c" cx="300" cy="60" r="40" style="fill:#fee;stroke:#633;stroke-width:2"/>
  <g id="g" transform="translate(150,180) scale(1.5)">
    <rect id="inner" x="0" y="0" width="40" height="30" style="fill:#efe;stroke:#363;stroke-width:1"/>
  </g>
  <text id="t" x="20" y="260" style="font-size:20px">Label</text>
  <path id="k1" d="M 0,0" style="fill:none;stroke:#000;stroke-width:1.5;marker-end:url(#arrow)"
        inkscape:connector-type="polyline" inkscape:connection-start="#a" inkscape:connection-end="#c"/>
  <path id="k2" d="M 0,0" style="fill:none;stroke:#06c;stroke-width:1.5;marker-end:url(#arrow)"
        inkscape:connector-type="orthogonal" inkscape:connection-start="#a" inkscape:connection-end="#inner"/>
  <path id="k3" d="M 0,0" style="fill:none;stroke:#c60;stroke-width:1.5;marker-end:url(#arrow)"
        inkscape:connector-type="polyline" inkscape:connection-start="#t" inkscape:connection-end="#inner"/>
</svg>"""
doc = Document.from_bytes(SVG.encode())
eng.run_actions(doc, [])  # plain round-trip: does load compute routes?
for k in ("k1", "k2", "k3"):
    print(k, doc.get(k).get("d"))
eng.export(doc, OUT / "e09b_1.png", width=800, background="#fff")

# move 'a' with lxml only, then round-trip
doc.update("a", {"x": 20, "y": 150})
eng.run_actions(doc, [])
print("after lxml move + round-trip:")
for k in ("k1", "k2", "k3"):
    print(k, doc.get(k).get("d"))
eng.export(doc, OUT / "e09b_2.png", width=800, background="#fff")
eng.close()
