from __future__ import annotations

import argparse
from pathlib import Path

from .bom import base_bom, write_bom
from .params import load_config


def main() -> int:
    parser = argparse.ArgumentParser(description="Build EXA Collar mechanical CAD outputs.")
    parser.add_argument("--config", default="configs/v3_default.yaml", help="YAML configuration path")
    parser.add_argument("--out", default="outputs/v3", help="Output directory")
    parser.add_argument("--no-cad", action="store_true", help="Only generate non-CAD deliverables")
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    config = load_config(args.config)

    rows = base_bom(config)
    if not args.no_cad:
        from .geometry import build_cad

        rows.extend(build_cad(config, out_dir))

    write_bom(out_dir, rows)
    _write_design_report(config, out_dir)
    _write_svg_render(config, out_dir)
    print(f"Generated EXA Collar outputs in {out_dir}")
    return 0


def _write_design_report(config, out_dir: Path) -> None:
    data = config.data
    chain = data.get("cable_chain", {})
    link = chain if chain.get("enabled", False) else data.get("flexible_link", data.get("bridge", {}))
    cw_profile = _counterweight_profile(data)
    report = f"""# {config.name} {config.revision} Mechanical Build

## Key Parameters

- Neck radius: {data['neck']['radius']} mm
- Strap width: {data['strap']['width']} mm
- Selected panel: {config.panel.description}
- Solar recess depth: {data['solar']['recess_depth']} mm
- O-ring channel: {data['seal']['channel_width']} mm wide x {data['seal']['channel_depth']} mm deep
- O-ring target compression: {int(float(data['seal']['target_compression']) * 100)} percent
- Cable chain enabled: {bool(chain.get('enabled', False))}
- Cable chain links: {link.get('link_count', 0)}
- Cable chain link size: {link.get('link_length_mm', link.get('pitch', 0))} x {link.get('link_width_mm', link.get('width', 0))} x {link.get('link_height_mm', link.get('thickness', 0))} mm
- Cable channel: {link.get('internal_channel_width_mm', link.get('cable_channel_width', 0))} x {link.get('internal_channel_height_mm', link.get('cable_channel_height', 0))} mm
- Max bend angle per link: {link.get('max_bend_angle_deg', 'configured')} deg
- Counterweight profile: {data['counterweight']['selected_profile']} ({cw_profile['mass_g']} g, {cw_profile['material']})

## Manufacturing Intent

- FDM first, with geometry organized for later injection-molded evolution.
- Top-only removable lids; no lower service openings.
- No clips and no permanent adhesive for service closures.
- O-ring channels, centering ribs, compression limiters and uniformly distributed M3 screws.
- Replaceable solar panels bonded into shallow protected lid recesses.
- Reinforced articulated cable chain protects internal conductors and limits bend angle before loads reach module walls.
- Cable-chain end mounts bolt to module bodies, not service lids.
- Each module remains an independent sealed volume.
"""
    (out_dir / "design_report.md").write_text(report, encoding="utf-8")


def _write_svg_render(config, out_dir: Path) -> None:
    data = config.data
    electronics = data["modules"]["electronics"]
    battery = data["modules"]["battery"]
    panel = config.panel
    strap_w = data["strap"]["width"]
    chain = data.get("cable_chain", {})
    link = chain if chain.get("enabled", False) else data.get("flexible_link", data.get("bridge", {}))
    link_w = link.get("link_width_mm", link.get("width", 28))
    cw_profile = _counterweight_profile(data)
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="900" height="520" viewBox="-450 -260 900 520">
  <rect x="-450" y="-260" width="900" height="520" fill="#f6f7f8"/>
  <path d="M -112 -55 C -70 -142 70 -142 112 -55" fill="none" stroke="#2f3437" stroke-width="{link_w}" stroke-linecap="round" stroke-dasharray="18 7"/>
  <path d="M -112 -55 C -70 -142 70 -142 112 -55" fill="none" stroke="#74a7c8" stroke-width="7" stroke-linecap="round"/>
  <rect x="-250" y="-40" width="{electronics['outer_length']}" height="{electronics['outer_width']}" rx="8" fill="#30363a"/>
  <rect x="132" y="-40" width="{battery['outer_length']}" height="{battery['outer_width']}" rx="8" fill="#30363a"/>
  <rect x="-231" y="-28" width="{panel.length}" height="{panel.width}" rx="2" fill="#1b4c7a"/>
  <rect x="151" y="-28" width="{panel.length}" height="{panel.width}" rx="2" fill="#1b4c7a"/>
  <rect x="-285" y="36" width="50" height="{strap_w + 10}" rx="6" fill="#4b5358"/>
  <rect x="-147" y="36" width="50" height="{strap_w + 10}" rx="6" fill="#4b5358"/>
  <rect x="97" y="36" width="50" height="{strap_w + 10}" rx="6" fill="#4b5358"/>
  <rect x="235" y="36" width="50" height="{strap_w + 10}" rx="6" fill="#4b5358"/>
  <rect x="-38" y="120" width="{cw_profile['carrier_length']}" height="{cw_profile['carrier_width']}" rx="5" fill="#6c7175"/>
  <text x="0" y="-210" text-anchor="middle" font-family="Arial" font-size="24" fill="#202326">{config.name} {config.revision}</text>
  <text x="0" y="205" text-anchor="middle" font-family="Arial" font-size="14" fill="#50565a">Top technical render: sealed modules, articulated cable carrier chain, solar lid panels, strap lugs, lower counterweight</text>
</svg>
"""
    (out_dir / "render_top_view.svg").write_text(svg, encoding="utf-8")


def _counterweight_profile(data):
    cw = data["counterweight"]
    if "profiles" not in cw:
        return {
            "mass_g": cw.get("mass_target_g", 0),
            "material": "configured_mass",
            "carrier_length": cw["carrier_length"],
            "carrier_width": cw["carrier_width"],
            "carrier_height": cw["carrier_height"],
        }
    return cw["profiles"][cw["selected_profile"]]


if __name__ == "__main__":
    raise SystemExit(main())
