from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .simple_yaml import load_yaml


@dataclass(frozen=True)
class Panel:
    key: str
    description: str
    length: float
    width: float
    thickness: float
    nominal_voltage: float


@dataclass(frozen=True)
class BuildConfig:
    path: Path
    data: dict[str, Any]
    panel: Panel

    @property
    def name(self) -> str:
        project = self.data.get("project", {})
        return str(project.get("name", "EXA Collar"))

    @property
    def revision(self) -> str:
        project = self.data.get("project", {})
        return str(project.get("revision", "V3"))


def load_config(path: str | Path) -> BuildConfig:
    config_path = Path(path)
    data = load_yaml(config_path)
    solar = data["solar"]
    panel_catalog_path = (config_path.parent / solar["panel_catalog"]).resolve()
    if not panel_catalog_path.exists():
        panel_catalog_path = (Path.cwd() / solar["panel_catalog"]).resolve()
    catalog = load_yaml(panel_catalog_path)
    selected = solar["selected_panel"]
    panel_data = catalog["panels"][selected]
    panel = Panel(
        key=selected,
        description=str(panel_data.get("description", selected)),
        length=float(panel_data["length"]),
        width=float(panel_data["width"]),
        thickness=float(panel_data["thickness"]),
        nominal_voltage=float(panel_data.get("nominal_voltage", 0)),
    )
    _validate(data, panel)
    return BuildConfig(path=config_path, data=data, panel=panel)


def _validate(data: dict[str, Any], panel: Panel) -> None:
    strap = data["strap"]
    if strap["width"] not in strap["supported_widths"]:
        raise ValueError("strap.width must be one of strap.supported_widths")
    link = data.get("flexible_link")
    if link:
        if link["selected_variant"] not in link["available_variants"]:
            raise ValueError("flexible_link.selected_variant must be available_variants")
        if int(link["link_count"]) < 3:
            raise ValueError("flexible_link.link_count must be at least 3")
    chain = data.get("cable_chain")
    if chain and chain.get("enabled", False):
        if int(chain["link_count"]) < 3:
            raise ValueError("cable_chain.link_count must be at least 3")
        if float(chain["internal_channel_width_mm"]) >= float(chain["link_width_mm"]):
            raise ValueError("cable_chain internal channel width must fit inside link width")
        if float(chain["internal_channel_height_mm"]) >= float(chain["link_height_mm"]):
            raise ValueError("cable_chain internal channel height must fit inside link height")
        if float(chain["max_bend_angle_deg"]) <= 0:
            raise ValueError("cable_chain.max_bend_angle_deg must be positive")
    cw = data.get("counterweight", {})
    if "profiles" in cw and cw["selected_profile"] not in cw["profiles"]:
        raise ValueError("counterweight.selected_profile must exist in counterweight.profiles")

    for module_name, module in data["modules"].items():
        border = float(data["solar"]["protective_border"])
        gap = float(data["solar"]["adhesive_gap"])
        required_length = panel.length + 2 * (border + gap)
        required_width = panel.width + 2 * (border + gap)
        if required_length > float(module["outer_length"]):
            raise ValueError(f"{module_name} is too short for selected solar panel")
        if required_width > float(module["outer_width"]):
            raise ValueError(f"{module_name} is too narrow for selected solar panel")
