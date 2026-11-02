"""Generate the SCANard brand SVGs. Usage: python3 -I assets/brand/gen_brand.py assets/brand"""
import sys, os
out = sys.argv[1]
DUCK = "12,56 28,64 64,64 72,56 72,36 80,28 96,28 104,36 104,40 120,40 124,44 120,48 104,48 104,52 96,60 96,64 104,72 104,84 96,92 40,92 24,76 12,64"
SCAN_Y = 81  # scan line centre (waterline)
def eye(c, cx=89, cy=38, r=5, w=2.4):
    import math
    a1, a2 = math.radians(-55), math.radians(235)
    p = lambda a, rr=r: (cx+rr*math.cos(a), cy+rr*math.sin(a))
    s, e = p(a1), p(a2)
    t = (-math.sin(a2), math.cos(a2)); n = (math.cos(a2), math.sin(a2))
    tip = (e[0]+3.2*t[0], e[1]+3.2*t[1])
    b1 = (e[0]+2.4*n[0], e[1]+2.4*n[1]); b2 = (e[0]-2.4*n[0], e[1]-2.4*n[1])
    f = lambda q: f"{q[0]:.2f} {q[1]:.2f}"
    return (f'<path d="M{f(s)} A{r} {r} 0 1 1 {f(e)}" fill="none" stroke="{c}" stroke-width="{w}"/>'
            f'<path d="M{f(tip)} L{f(b1)} L{f(b2)} Z" fill="{c}"/>')

def duck(pfx, solid, observed, eyec, scan, gap=2.5, shift=5, outline=True):
    """Duck: solid above the scan line (expected), shifted outline below (observed)."""
    lo = f'<polygon points="{DUCK}" transform="translate({shift} 0)" fill="{observed}" '
    lo += (f'fill-opacity="0.35" stroke="{observed}" stroke-width="3"/>' if outline else '/>')
    sc = f'<rect x="0" y="{SCAN_Y-1.5}" width="132" height="3" fill="{scan}"/>' if scan else ''
    return f'''<defs>
    <clipPath id="{pfx}a"><rect x="-20" y="0" width="170" height="{SCAN_Y-gap}"/></clipPath>
    <clipPath id="{pfx}b"><rect x="-20" y="{SCAN_Y+gap}" width="170" height="80"/></clipPath>
  </defs>
  <g clip-path="url(#{pfx}a)"><polygon points="{DUCK}" fill="{solid}"/>{eye(eyec)}</g>
  <g clip-path="url(#{pfx}b)">{lo}</g>
  {sc}'''

Y, INK, PAPER, STEEL, CYAN, GREEN, RED = "#F2B705", "#1E2329", "#F4F1EA", "#8A949E", "#22B8CF", "#2E9E5B", "#D64541"
GRID = f'<pattern id="grid" width="8" height="8" patternUnits="userSpaceOnUse"><path d="M8 0H0V8" fill="none" stroke="{STEEL}" stroke-opacity="0.13" stroke-width="0.5"/></pattern>'

# --- avatar -------------------------------------------------------------
open(os.path.join(out, "scanard-avatar.svg"), "w").write(f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128" width="512" height="512">
  <title>SCANard</title>
  <defs>{GRID}</defs>
  <rect width="128" height="128" fill="{INK}"/>
  <rect width="128" height="128" fill="url(#grid)"/>
  <g transform="translate(-4 4)">
  {duck("av", Y, Y, INK, CYAN)}
  </g>
</svg>
''')

# --- minimal mark (monochrome, follows light/dark) -----------------------
open(os.path.join(out, "scanard-mark.svg"), "w").write(f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="8 24 124 72" width="124" height="72">
  <title>SCANard</title>
  <style>
    .i {{ fill: {INK}; }} .p {{ fill: {PAPER}; stroke: {PAPER}; }}
    @media (prefers-color-scheme: dark) {{ .i {{ fill: {PAPER}; }} .p {{ fill: {INK}; stroke: {INK}; }} }}
  </style>
  {duck("mk", "INK", "INK", "PAPER", None, gap=3, shift=6, outline=False)
     .replace('fill="INK"', 'class="i"').replace('stroke="PAPER"', 'class="p"').replace('fill="PAPER"', 'class="p"')}
</svg>
''')

# --- README banner 1280x320 ---------------------------------------------
W, H = 1280, 320
BS = 2.7; BX = 24; BY = 160 - 60*BS
x0, cw, n = 470, 76, 10           # timing diagram: first column, cycle width, cycles
IN  = [0,1,1,0,0,1,1,1,0,0]
EXP = [0,1,0,0,0,1,0,0,0,0]       # R_TRIG on IN: pulse one cycle on each rising edge
OBS = [0,1,0,0,0,1,1,0,0,0]       # one cycle where the runtime keeps Q high: the canard
rows = [("IN", IN, STEEL, ""), ("Q expected", EXP, Y, ""), ("Q observed", OBS, CYAN, ' stroke-dasharray="6 4"')]
def wave(bits, y, h=22):
    pts, prev = [], None
    for i, b in enumerate(bits):
        yy = y - h*b; x = x0 + i*cw
        if prev is not None and prev != b: pts.append(f"{x},{y - h*prev}")
        pts.append(f"{x},{yy}"); pts.append(f"{x+cw},{yy}"); prev = b
    return " ".join(pts)
diag = []
for i in range(n):
    x = x0 + i*cw
    bad = EXP[i] != OBS[i]
    if bad:
        diag.append(f'<rect x="{x}" y="150" width="{cw}" height="138" fill="{RED}" fill-opacity="0.14"/>')
    diag.append(f'<line x1="{x}" y1="150" x2="{x}" y2="288" stroke="{STEEL}" stroke-opacity="0.25"/>')
    diag.append(f'<text x="{x+cw/2}" y="306" class="m s" text-anchor="middle">{"n" if i==0 else f"n+{i}"}</text>')
    cx, cy = x + cw/2, 136
    if bad:
        diag.append(f'<path d="M{cx-5} {cy-5}L{cx+5} {cy+5}M{cx+5} {cy-5}L{cx-5} {cy+5}" stroke="{RED}" stroke-width="2.5"/>')
    else:
        diag.append(f'<path d="M{cx-5} {cy}L{cx-1.5} {cy+4}L{cx+5} {cy-4}" fill="none" stroke="{GREEN}" stroke-width="2.5"/>')
diag.append(f'<line x1="{x0+n*cw}" y1="150" x2="{x0+n*cw}" y2="288" stroke="{STEEL}" stroke-opacity="0.25"/>')
for k, (lab, bits, col, dash) in enumerate(rows):
    y = 190 + k*44
    diag.append(f'<text x="{x0-16}" y="{y-4}" class="m s" text-anchor="end">{lab}</text>')
    diag.append(f'<polyline points="{wave(bits, y)}" fill="none" stroke="{col}" stroke-width="2.5"{dash}/>')

open(os.path.join(out, "scanard-banner.svg"), "w").write(f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">
  <title>SCANard — IEC 61131-3 conformance traces</title>
  <style>
    .m {{ font-family: "IBM Plex Mono", "JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }}
    .s {{ font-size: 13px; fill: {STEEL}; }}
  </style>
  <defs>{GRID}
    <linearGradient id="beam" x1="0" x2="1"><stop offset="0" stop-color="{CYAN}"/><stop offset="1" stop-color="{CYAN}" stop-opacity="0"/></linearGradient>
  </defs>
  <rect width="{W}" height="{H}" fill="{INK}"/>
  <rect width="{W}" height="{H}" fill="url(#grid)"/>
  <rect x="{BX+130*BS}" y="{BY+(SCAN_Y-1.5)*BS}" width="{380-(BX+130*BS)}" height="{3*BS}" fill="url(#beam)"/>
  <g transform="translate({BX} {BY}) scale({BS})">
  {duck("bn", Y, Y, INK, CYAN)}
  </g>
  <text x="{x0-6}" y="78" class="m" font-size="58" font-weight="700" fill="{PAPER}">SCAN<tspan font-weight="400" fill="{Y}">ard</tspan></text>
  <text x="{x0-4}" y="106" class="m" font-size="17" fill="{STEEL}">IEC 61131-3 conformance traces · expected vs. observed, one scan at a time</text>
  {"".join(diag)}
</svg>
''')
