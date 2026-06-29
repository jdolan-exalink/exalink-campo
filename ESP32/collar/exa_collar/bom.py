from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from .params import BuildConfig


def base_bom(config: BuildConfig) -> list[dict[str, Any]]:
    data = config.data
    fasteners = data["fasteners"]
    seal = data["seal"]
    panel = config.panel
    chain = data.get("cable_chain", {})
    link = chain if chain.get("enabled", False) else data.get("flexible_link", data.get("bridge", {}))
    cw_profile = _counterweight_profile(data)
    return [
        {
            "part": "solar_panel",
            "qty": 2 if data["solar"]["layout"] == "dual" else 1,
            "material": panel.description,
            "notes": f"{panel.length} x {panel.width} x {panel.thickness} mm, bonded with VHB/silicone/structural adhesive",
        },
        {
            "part": "lid_screws",
            "qty": 8,
            "material": fasteners["lid_screw"],
            "notes": "Four screws per removable lid",
        },
        {
            "part": "heat_set_inserts",
            "qty": 8,
            "material": fasteners["insert"],
            "notes": "Metal threads in printed bosses",
        },
        {
            "part": "commercial_o_rings",
            "qty": 2,
            "material": f"{seal['o_ring_section']} mm section elastomer",
            "notes": f"Target compression {int(float(seal['target_compression']) * 100)} percent",
        },
        {
            "part": "cable_chain_pins",
            "qty": max(2, int(link.get("link_count", link.get("link_count_mm", 2))) + 1),
            "material": link.get("metal_pin_option", "A4 stainless removable pin"),
            "notes": "Removable articulation pins; printed pin option remains configurable",
        },
        {
            "part": "cable_chain_covers",
            "qty": int(link.get("link_count", 0)) if link.get("enabled", False) else 0,
            "material": "Same polymer as link or UV-stable ASA",
            "notes": "Openable top closures for cable replacement without destroying chain",
        },
        {
            "part": "cable_chain_end_mount_seals",
            "qty": 2,
            "material": f"{link.get('end_mount_oring_section_mm', 2.0)} mm O-ring plus rubber grommet",
            "notes": "Sealed cable-chain entry into module bodies; not attached to lids",
        },
        {
            "part": "internal_cable_bundle",
            "qty": 1,
            "material": "Battery +, battery -, battery sense, optional I2C/UART/GPIO spare conductors",
            "notes": "Routed through protected continuous cable-chain channel",
        },
        {
            "part": "counterweight_mass",
            "qty": 1,
            "material": cw_profile["material"],
            "notes": f"Configurable lower mass, target {cw_profile['mass_g']} g",
        },
    ]


def _counterweight_profile(data: dict[str, Any]) -> dict[str, Any]:
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


def write_bom(out_dir: Path, rows: list[dict[str, Any]]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "BOM.json"
    csv_path = out_dir / "BOM.csv"
    json_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["part", "qty", "material", "notes"])
        writer.writeheader()
        writer.writerows(rows)
