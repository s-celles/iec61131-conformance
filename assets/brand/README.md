# SCANard

*Scan* (the PLC cycle) + *canard* (a duck, and in French a false note).
The duck that watches every cycle and spots the canards.

The duck is solid above the cyan scan line (**expected**) and shifted,
outlined, below it (**observed**). The eye is an open cycle arrow (one scan).

| File | Use |
|---|---|
| `scanard-avatar.svg` / `.png` (512 px) | GitHub avatar, social icon |
| `scanard-banner.svg` (1280×320) | README banner |
| `scanard-mark.svg` | monochrome mark, favicon; follows light/dark |

Regenerate with `python3 -I assets/brand/gen_brand.py assets/brand`
(PNG: `rsvg-convert -w 512 assets/brand/scanard-avatar.svg -o assets/brand/scanard-avatar.png`).

## Palette

| Role | Hex |
|---|---|
| Duck, accent (safety yellow) | `#F2B705` |
| Background, ink (anthracite) | `#1E2329` |
| Grid, secondary text (steel) | `#8A949E` |
| Light background (off-white) | `#F4F1EA` |
| Scan line (cyan) | `#22B8CF` |
| Conformant | `#2E9E5B` |
| Mismatch | `#D64541` |

Green and red carry the expected/observed verdict only, never decoration.

## Rules

- 8-unit grid; angles of 0°, 45° and 90° only. The open eye arc is the
  only curve.
- Wordmark: `SCAN` bold + `ard` regular in yellow, monospace
  (IBM Plex Mono, then the system monospace).
- Avoid: round cute shapes, glossy bath-toy rendering, anything that looks
  like an IEC or PLCopen logo or a certification seal.
