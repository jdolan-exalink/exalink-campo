from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from .freecad_utils import App, Part, add_shape, cut_all, cylinder, export_shape, make_arc_points, require_freecad, rounded_box, v
from .params import BuildConfig


def build_cad(config: BuildConfig, out_dir: Path) -> list[dict[str, Any]]:
    require_freecad()
    data = config.data
    design_id = _design_id(config)
    _clean_cad_outputs(out_dir)
    doc = App.newDocument(design_id)
    parts: list[dict[str, Any]] = []

    electronics = _module(doc, config, "electronics", x_offset=-92)
    battery = _module(doc, config, "battery", x_offset=92)
    link_parts = _cable_chain_system(doc, config)
    counterweight = _counterweight(doc, config)

    for obj, meta in [*electronics, *battery, *link_parts, counterweight]:
        export_shape(obj, out_dir / "parts", obj.Name)
        parts.append(meta)

    doc.recompute()
    App.getDocument(doc.Name).saveAs(str(out_dir / f"{design_id}.FCStd"))
    for backup in out_dir.glob("*.FCBak"):
        backup.unlink()
    _export_assembly_step(doc, out_dir, design_id)
    _export_dxf_templates(config, out_dir)
    _export_pdf_summary(doc, out_dir, config, design_id)
    return parts


def _clean_cad_outputs(out_dir: Path) -> None:
    for pattern in ("*.FCStd", "*_assembly.step", "*_summary.pdf", "*.FCBak"):
        for path in out_dir.glob(pattern):
            path.unlink()
    parts_dir = out_dir / "parts"
    if parts_dir.exists():
        for pattern in ("*.step", "*.stl"):
            for path in parts_dir.glob(pattern):
                path.unlink()


def _design_id(config: BuildConfig) -> str:
    return f"{config.name}_{config.revision}".replace(" ", "_")


def _module(doc, config: BuildConfig, module_key: str, x_offset: float):
    data = config.data
    module = data["modules"][module_key]
    mfg = data["manufacturing"]
    seal = data["seal"]
    solar = data["solar"]
    fasteners = data["fasteners"]
    strap = data["strap"]

    length = float(module["outer_length"])
    width = float(module["outer_width"])
    body_h = float(module["body_height"])
    lid_h = float(module["lid_height"])
    wall = float(mfg["wall_thickness"])
    radius = float(mfg["corner_radius"])

    outer = rounded_box(length, width, body_h, radius)
    inner = rounded_box(length - 2 * wall, width - 2 * wall, body_h, max(radius - wall, 1))
    inner.translate(v(0, 0, wall))
    body = outer.cut(inner)

    body = body.fuse(_strap_lugs(length, width, body_h, strap))
    body = body.fuse(_flex_socket(length, width, body_h, side=1 if x_offset < 0 else -1, config=config))
    body = body.fuse(_screw_bosses(length, width, fasteners, body_h - 2))
    body = body.fuse(_component_posts(module))
    body.translate(v(x_offset, 0, 0))

    lid = rounded_box(length, width, lid_h, radius)
    recess = _solar_recess(config, z=lid_h - float(solar["recess_depth"]))
    gasket = _oring_channel(length, width, lid_h, seal, wall)
    lid = cut_all(lid, [recess, gasket])
    lid = lid.fuse(_lid_screw_tubes(length, width, fasteners, lid_h))
    lid = lid.fuse(_solar_protective_frame(config, lid_h))
    lid = lid.fuse(_centering_rib(length, width, seal, wall))
    lid = lid.fuse(_compression_limiters(length, width, seal, fasteners))
    lid.translate(v(x_offset, 0, body_h + 1.0))

    body_obj = add_shape(doc, f"{module_key}_body", body)
    lid_obj = add_shape(doc, f"{module_key}_lid", lid)

    body_meta = {
        "part": body_obj.Name,
        "qty": 1,
        "material": "ASA, PETG-CF or PA-CF for FDM prototype",
        "notes": f"Sealed {module_key} lower body with reinforced strap lugs, flexible-link socket, M3 insert bosses and service posts",
    }
    lid_meta = {
        "part": lid_obj.Name,
        "qty": 1,
        "material": "ASA, PETG-CF or PA-CF for FDM prototype",
        "notes": "Top-only removable lid with O-ring channel, centering rib, compression limiters and replaceable adhesive solar panel recess",
    }
    return [(body_obj, body_meta), (lid_obj, lid_meta)]


def _strap_lugs(length: float, width: float, height: float, strap: dict[str, Any]):
    lug_t = float(strap["lug_thickness"])
    slot_w = float(strap["width"]) + float(strap["slot_clearance"])
    lug_h = min(height * 0.7, slot_w + 12)
    lug_w = 14
    left = rounded_box(lug_w, lug_t, lug_h, float(strap["lug_radius"]))
    right = rounded_box(lug_w, lug_t, lug_h, float(strap["lug_radius"]))
    left.translate(v(-length / 2 - lug_w / 2 + 5, -width / 2 - lug_t / 2, 4))
    right.translate(v(length / 2 + lug_w / 2 - 5, -width / 2 - lug_t / 2, 4))
    slot_left = rounded_box(lug_w + 2, lug_t + 2, slot_w, 2)
    slot_right = rounded_box(lug_w + 2, lug_t + 2, slot_w, 2)
    slot_left.translate(v(-length / 2 - lug_w / 2 + 5, -width / 2 - lug_t / 2, 8))
    slot_right.translate(v(length / 2 + lug_w / 2 - 5, -width / 2 - lug_t / 2, 8))
    lug_shape = left.cut(slot_left).fuse(right.cut(slot_right))
    rib_count = int(strap.get("rib_count", 2))
    for i in range(rib_count):
        y = -width / 2 - lug_t - 1.5
        z = 5 + i * max(3, lug_h / max(rib_count, 1) / 1.4)
        left_rib = rounded_box(18, 3, 3, 0)
        right_rib = rounded_box(18, 3, 3, 0)
        left_rib.translate(v(-length / 2 - 4, y, z))
        right_rib.translate(v(length / 2 + 4, y, z))
        lug_shape = lug_shape.fuse(left_rib).fuse(right_rib)
    return lug_shape


def _flex_socket(length: float, width: float, height: float, side: int, config: BuildConfig):
    chain = config.data.get("cable_chain", {})
    if chain.get("enabled", False):
        overlap = float(chain["end_mount_length_mm"])
        link_width = float(chain["end_mount_flange_width_mm"])
        link_height = float(chain["end_mount_flange_height_mm"])
        gland_d = float(chain["grommet_outer_diameter_mm"])
    else:
        link = config.data.get("flexible_link", config.data.get("bridge"))
        overlap = float(link["attachment_overlap"])
        link_width = float(link["width"]) + 10
        link_height = float(link["thickness"]) + 8
        gland_d = float(link["seal_gland_diameter"])
    socket = rounded_box(overlap, link_width, link_height, 4)
    socket.translate(v(side * (length / 2 - overlap / 2), width / 2 + 1, height - link_height + 2))
    gland = cylinder(gland_d, overlap + 4, side * (length / 2 - overlap / 2), width / 2 + 1, height - link_height / 2 + 2)
    gland.rotate(v(side * (length / 2 - overlap / 2), width / 2 + 1, height - link_height / 2 + 2), v(0, 1, 0), 90)
    return socket.cut(gland)


def _screw_bosses(length: float, width: float, fasteners: dict[str, Any], height: float):
    boss_d = float(fasteners["insert_boss_diameter"])
    clearance = float(fasteners["screw_clearance_diameter"])
    boss_h = float(fasteners["boss_height"])
    margin = 12
    shape = None
    for x in (-length / 2 + margin, length / 2 - margin):
        for y in (-width / 2 + margin, width / 2 - margin):
            boss = cylinder(boss_d, boss_h, x, y, height - boss_h)
            hole = cylinder(clearance, boss_h + 2, x, y, height - boss_h - 1)
            boss = boss.cut(hole)
            shape = boss if shape is None else shape.fuse(boss)
    return shape


def _component_posts(module: dict[str, Any]):
    shape = None
    for post in module.get("component_posts", []):
        boss = cylinder(6.5, float(post.get("height", 10)), float(post["x"]), float(post["y"]), 3)
        pilot = cylinder(2.4, float(post.get("height", 10)) + 1, float(post["x"]), float(post["y"]), 3)
        boss = boss.cut(pilot)
        shape = boss if shape is None else shape.fuse(boss)
    return shape


def _solar_recess(config: BuildConfig, z: float):
    panel = config.panel
    solar = config.data["solar"]
    length = panel.length + 2 * float(solar["adhesive_gap"])
    width = panel.width + 2 * float(solar["adhesive_gap"])
    depth = float(solar["recess_depth"]) + 0.2
    cut = rounded_box(length, width, depth, 2)
    cut.translate(v(0, 0, z))
    return cut


def _solar_protective_frame(config: BuildConfig, lid_h: float):
    panel = config.panel
    solar = config.data["solar"]
    gap = float(solar["adhesive_gap"])
    border = float(solar["protective_border"])
    frame_h = float(solar.get("frame_height", 0.8))
    inner_l = panel.length + 2 * gap
    inner_w = panel.width + 2 * gap
    outer_l = inner_l + 2 * border
    outer_w = inner_w + 2 * border
    frame = rounded_box(outer_l, outer_w, frame_h, 0)
    void = rounded_box(inner_l, inner_w, frame_h + 0.2, 0)
    frame = frame.cut(void)
    frame.translate(v(0, 0, lid_h - frame_h))
    return frame


def _oring_channel(length: float, width: float, lid_h: float, seal: dict[str, Any], wall: float):
    channel_w = float(seal["channel_width"])
    depth = float(seal["channel_depth"])
    outer = rounded_box(length - 2 * wall, width - 2 * wall, depth + 0.1, 4)
    inner = rounded_box(length - 2 * wall - 2 * channel_w, width - 2 * wall - 2 * channel_w, depth + 0.2, 3)
    outer.translate(v(0, 0, -0.05))
    inner.translate(v(0, 0, -0.1))
    return outer.cut(inner)


def _centering_rib(length: float, width: float, seal: dict[str, Any], wall: float):
    rib_w = float(seal.get("centering_rib_width", 1.4))
    rib_h = float(seal.get("centering_rib_height", 1.0))
    outer = rounded_box(length - 2 * wall - 7, width - 2 * wall - 7, rib_h, 0)
    inner = rounded_box(length - 2 * wall - 7 - 2 * rib_w, width - 2 * wall - 7 - 2 * rib_w, rib_h + 0.2, 0)
    rib = outer.cut(inner)
    rib.translate(v(0, 0, -rib_h))
    return rib


def _compression_limiters(length: float, width: float, seal: dict[str, Any], fasteners: dict[str, Any]):
    limiter_h = float(seal.get("compression_limiter_height", 1.5))
    od = float(fasteners["insert_boss_diameter"]) + 1.0
    clearance = float(fasteners["screw_clearance_diameter"])
    margin = 12
    shape = None
    for x in (-length / 2 + margin, length / 2 - margin):
        for y in (-width / 2 + margin, width / 2 - margin):
            limiter = cylinder(od, limiter_h, x, y, -limiter_h)
            hole = cylinder(clearance, limiter_h + 0.4, x, y, -limiter_h - 0.2)
            limiter = limiter.cut(hole)
            shape = limiter if shape is None else shape.fuse(limiter)
    return shape


def _lid_screw_tubes(length: float, width: float, fasteners: dict[str, Any], lid_h: float):
    return _screw_bosses(length, width, fasteners, lid_h)


def _cable_chain_system(doc, config: BuildConfig):
    chain = config.data.get("cable_chain", {})
    if not chain.get("enabled", False):
        return [_flexible_link(doc, config)]

    radius = float(config.data.get("animal", {}).get("neck_radius_mm", config.data["neck"].get("neck_radius_mm", config.data["neck"]["radius"])))
    angle = min(float(chain["max_bend_angle_deg"]) * (int(chain["link_count"]) - 1), 58.0)
    points = make_arc_points(radius, -angle / 2, angle / 2, 42, int(chain["link_count"]))
    link_shapes = []
    pin_shapes = []
    cover_shapes = []
    stop_shapes = []
    for idx, point in enumerate(points):
        tangent_angle = _arc_tangent_angle(points, idx)
        link_shapes.append(_chain_link_shape(chain, point, tangent_angle))
        pin_shapes.append(_chain_pin_shape(chain, point, tangent_angle))
        cover_shapes.append(_chain_cover_shape(chain, point, tangent_angle))
        stop_shapes.append(_chain_bend_stop_shape(chain, point, tangent_angle, idx))

    link_group = _fuse_shapes([*link_shapes, *stop_shapes])
    pin_group = _fuse_shapes(pin_shapes)
    cover_group = _fuse_shapes(cover_shapes)
    end_mount_group = _fuse_shapes([
        _chain_end_mount_shape(chain, points[0], _arc_tangent_angle(points, 0), -1),
        _chain_end_mount_shape(chain, points[-1], _arc_tangent_angle(points, len(points) - 1), 1),
    ])
    grommet_group = _fuse_shapes([
        _chain_grommet_shape(chain, points[0], _arc_tangent_angle(points, 0), -1),
        _chain_grommet_shape(chain, points[-1], _arc_tangent_angle(points, len(points) - 1), 1),
    ])
    relief_group = _fuse_shapes([
        _chain_strain_relief_shape(chain, points[0], _arc_tangent_angle(points, 0), -1),
        _chain_strain_relief_shape(chain, points[-1], _arc_tangent_angle(points, len(points) - 1), 1),
    ])

    parts = [
        (add_shape(doc, "cable_chain_link", link_group), "Nylon, PETG, ASA or PA-CF", f"{chain['link_count']} reinforced cable-chain links with internal protected cable channel"),
        (add_shape(doc, "cable_chain_pin", pin_group), chain["metal_pin_option"], "Removable articulation pins; printed pin option is also configured"),
        (add_shape(doc, "cable_chain_cover", cover_group), "UV-stable ASA/PETG/PA cover", "Removable top closures for cable service access"),
        (add_shape(doc, "cable_chain_end_mount", end_mount_group), "Rigid printed or molded body mount", "Bolted structural entry mount with O-ring/labyrinth concept; attaches to module body, not lid"),
        (add_shape(doc, "cable_chain_grommet", grommet_group), "Commercial rubber grommet or molded elastomer", "Sealed cable entry interface into each module body"),
        (add_shape(doc, "cable_chain_strain_relief", relief_group), "Flexible TPU or rubber-lined clamp", "Cable clamp and smooth bend relief before entering sealed module"),
    ]
    return [
        (
            obj,
            {
                "part": obj.Name,
                "qty": 1,
                "material": material,
                "notes": notes,
            },
        )
        for obj, material, notes in parts
    ]


def _chain_link_shape(chain: dict[str, Any], point, angle: float):
    length = float(chain["link_length_mm"])
    width = float(chain["link_width_mm"])
    height = float(chain["link_height_mm"])
    channel_w = float(chain["internal_channel_width_mm"])
    channel_h = float(chain["internal_channel_height_mm"])
    body = rounded_box(length, width, height, 0)
    body.translate(v(0, 0, -height / 2))
    channel = rounded_box(length + 1.0, channel_w, channel_h, 0)
    channel.translate(v(0, 0, -channel_h / 2))
    body = body.cut(channel)

    for y in (-width / 2 + 2.2, width / 2 - 2.2):
        rib = rounded_box(length * 0.78, float(chain["rib_thickness_mm"]), height * 0.46, 0)
        rib.translate(v(0, y, -height * 0.48))
        body = body.fuse(rib)

    hinge_d = float(chain["pin_diameter_mm"]) + 3.0
    for x in (-length / 2 + 2.8, length / 2 - 2.8):
        barrel = cylinder(hinge_d, width + 2.0, x, -width / 2 - 1.0, 0)
        barrel.rotate(v(x, 0, 0), v(1, 0, 0), 90)
        hole = cylinder(float(chain["pin_diameter_mm"]) + 0.4, width + 4.0, x, -width / 2 - 2.0, 0)
        hole.rotate(v(x, 0, 0), v(1, 0, 0), 90)
        body = body.fuse(barrel.cut(hole))

    return _orient_chain_shape(body, point, angle)


def _chain_pin_shape(chain: dict[str, Any], point, angle: float):
    width = float(chain["link_width_mm"])
    pin = cylinder(float(chain["pin_diameter_mm"]), width + 6.0, 0, -width / 2 - 3.0, 0)
    pin.rotate(v(0, 0, 0), v(1, 0, 0), 90)
    return _orient_chain_shape(pin, point, angle)


def _chain_cover_shape(chain: dict[str, Any], point, angle: float):
    length = float(chain["link_length_mm"]) - 3.0
    width = float(chain["internal_channel_width_mm"]) + 4.0
    thickness = float(chain["cover_thickness_mm"])
    height = float(chain["link_height_mm"])
    cover = rounded_box(length, width, thickness, 0)
    cover.translate(v(0, 0, height / 2))
    for x in (-length / 2 + 3.0, length / 2 - 3.0):
        cover = cover.cut(cylinder(float(chain["top_cover_screw_diameter_mm"]), thickness + 1.0, x, 0, height / 2 - 0.5))
    return _orient_chain_shape(cover, point, angle)


def _chain_bend_stop_shape(chain: dict[str, Any], point, angle: float, idx: int):
    length = float(chain["bend_stop_thickness_mm"])
    width = float(chain["link_width_mm"])
    height = float(chain["link_height_mm"]) * 0.5
    x = float(chain["link_length_mm"]) / 2 - 1.0
    stop = rounded_box(length, width * 0.35, height, 0)
    stop.translate(v(x if idx % 2 == 0 else -x, 0, -height / 2))
    return _orient_chain_shape(stop, point, angle)


def _chain_end_mount_shape(chain: dict[str, Any], point, angle: float, side: int):
    length = float(chain["end_mount_length_mm"])
    width = float(chain["end_mount_flange_width_mm"])
    height = float(chain["end_mount_flange_height_mm"])
    mount = rounded_box(length, width, height, 0)
    mount.translate(v(side * (length / 2 + float(chain["link_length_mm"]) / 2), 0, -height / 2))

    tunnel = rounded_box(length + 2, float(chain["internal_channel_width_mm"]) + 2, float(chain["internal_channel_height_mm"]) + 2, 0)
    tunnel.translate(v(side * (length / 2 + float(chain["link_length_mm"]) / 2), 0, -float(chain["internal_channel_height_mm"]) / 2))
    mount = mount.cut(tunnel)

    for y in (-width / 2 + 7, width / 2 - 7):
        mount = mount.cut(cylinder(float(chain["end_mount_screw_diameter_mm"]), height + 2, side * (length / 2 + float(chain["link_length_mm"]) / 2), y, -height / 2 - 1))

    o_ring = cylinder(float(chain["grommet_outer_diameter_mm"]) + 2 * float(chain["end_mount_oring_section_mm"]), length + 1, side * (length + float(chain["link_length_mm"]) / 2), 0, 0)
    o_ring.rotate(v(side * (length + float(chain["link_length_mm"]) / 2), 0, 0), v(0, 1, 0), 90)
    mount = mount.fuse(o_ring)
    return _orient_chain_shape(mount, point, angle)


def _chain_grommet_shape(chain: dict[str, Any], point, angle: float, side: int):
    diameter = float(chain["grommet_outer_diameter_mm"])
    length = float(chain["end_mount_length_mm"]) * 0.55
    grommet = cylinder(diameter, length, side * (float(chain["link_length_mm"]) / 2 + length / 2), 0, 0)
    grommet.rotate(v(side * (float(chain["link_length_mm"]) / 2 + length / 2), 0, 0), v(0, 1, 0), 90)
    slot = rounded_box(length + 1, float(chain["grommet_inner_width_mm"]), float(chain["internal_channel_height_mm"]), 0)
    slot.translate(v(side * (float(chain["link_length_mm"]) / 2 + length / 2), 0, -float(chain["internal_channel_height_mm"]) / 2))
    return _orient_chain_shape(grommet.cut(slot), point, angle)


def _chain_strain_relief_shape(chain: dict[str, Any], point, angle: float, side: int):
    length = float(chain["strain_relief_length_mm"])
    width = float(chain["internal_channel_width_mm"]) + 8.0
    height = float(chain["internal_channel_height_mm"]) + 6.0
    relief = rounded_box(length, width, height, 0)
    relief.translate(v(side * (float(chain["link_length_mm"]) / 2 + length / 2), 0, -height / 2))
    channel = rounded_box(length + 1, float(chain["internal_channel_width_mm"]), float(chain["internal_channel_height_mm"]), 0)
    channel.translate(v(side * (float(chain["link_length_mm"]) / 2 + length / 2), 0, -float(chain["internal_channel_height_mm"]) / 2))
    relief = relief.cut(channel)
    for y in (-width / 2 + 4, width / 2 - 4):
        relief = relief.cut(cylinder(float(chain["strain_relief_clamp_screw_diameter_mm"]), height + 2, side * (float(chain["link_length_mm"]) / 2 + length / 2), y, -height / 2 - 1))
    return _orient_chain_shape(relief, point, angle)


def _orient_chain_shape(shape, point, angle: float):
    shape.rotate(v(0, 0, 0), v(0, 1, 0), -angle)
    shape.translate(point)
    return shape


def _fuse_shapes(shapes: list):
    shape = shapes[0]
    for item in shapes[1:]:
        shape = shape.fuse(item)
    return shape


def _flexible_link(doc, config: BuildConfig):
    data = config.data
    neck = data["neck"]
    link = data.get("flexible_link", data.get("bridge"))
    radius = float(neck["radius"])
    angle = float(neck.get("flexible_link_angle_deg", neck.get("bridge_angle_deg", 46)))
    width = float(link["width"])
    height = float(link.get("thickness", link.get("height", 12)))
    variant = str(link.get("selected_variant", link.get("version", "watch_link_reinforced")))
    count = int(link.get("link_count", 7))
    pitch = float(link.get("pitch", 15))
    cable_w = float(link.get("cable_channel_width", link.get("cable_channel_diameter", 8)))
    cable_h = float(link.get("cable_channel_height", cable_w * 0.6))

    points = make_arc_points(radius, -angle / 2, angle / 2, 40, count)
    blocks = []
    voids = []
    for idx, point in enumerate(points):
        local_width = width
        local_pitch = pitch
        if variant == "reinforced_tpu_band":
            local_pitch = pitch * 1.1
            local_width = width * 0.92
        elif variant == "multi_hinge":
            local_pitch = pitch * 0.85
        elif variant == "hybrid_tpu_rigid_inserts" and idx % 2:
            local_width = width * 0.72
        elif variant == "articulated_chain" and idx % 2:
            local_width = width * 0.82

        block = Part.makeBox(local_pitch, local_width, height, v(-local_pitch / 2, -local_width / 2, -height / 2))
        tangent_angle = _arc_tangent_angle(points, idx)
        block.rotate(v(0, 0, 0), v(0, 1, 0), -tangent_angle)
        block.translate(point)
        blocks.append(block)

        void = Part.makeBox(local_pitch + 2, cable_w, cable_h, v(-(local_pitch + 2) / 2, -cable_w / 2, -cable_h / 2))
        void.rotate(v(0, 0, 0), v(0, 1, 0), -tangent_angle)
        void.translate(point)
        voids.append(void)

        if variant in {"articulated_chain", "multi_hinge", "watch_link_reinforced"}:
            pin = cylinder(float(link["hinge_pin_diameter"]), local_width + 4, point.x, point.y - local_width / 2 - 2, point.z)
            pin.rotate(v(point.x, point.y, point.z), v(1, 0, 0), 90)
            blocks.append(pin)

    shape = blocks[0]
    for block in blocks[1:]:
        shape = shape.fuse(block)
    for void in voids:
        shape = shape.cut(void)
    shape = shape.fuse(_strain_relief_guide(points[0], -1, link)).fuse(_strain_relief_guide(points[-1], 1, link))
    obj = add_shape(doc, "flexible_link_with_protected_cable_channel", shape)
    meta = {
        "part": obj.Name,
        "qty": 1,
        "material": _link_material(variant),
        "notes": f"Variant {variant}, radius {radius} mm, internal cable channel {cable_w} x {cable_h} mm, controlled fuse neck {link.get('mechanical_fuse_neck_width', 'configured')} mm",
    }
    return obj, meta


def _arc_tangent_angle(points, idx: int) -> float:
    if idx == 0:
        prev_point, next_point = points[idx], points[idx + 1]
    elif idx == len(points) - 1:
        prev_point, next_point = points[idx - 1], points[idx]
    else:
        prev_point, next_point = points[idx - 1], points[idx + 1]
    return math.degrees(math.atan2(next_point.z - prev_point.z, next_point.x - prev_point.x))


def _strain_relief_guide(point, side: int, link: dict[str, Any]):
    length = float(link.get("strain_relief_length", 16))
    width = float(link["width"]) * 0.76
    height = float(link.get("thickness", link.get("height", 12))) * 0.55
    guide = rounded_box(length, width, height, 0)
    guide.translate(v(point.x + side * length / 2, point.y, point.z - height / 2))
    channel = rounded_box(length + 2, float(link.get("cable_channel_width", 9)), float(link.get("cable_channel_height", 5)), 0)
    channel.translate(v(point.x + side * length / 2, point.y, point.z - height / 2))
    return guide.cut(channel)


def _link_material(variant: str) -> str:
    materials = {
        "articulated_chain": "PA-CF or acetal rigid links with A4 stainless pins",
        "reinforced_tpu_band": "TPU 95A with embedded aramid/stainless reinforcement concept",
        "multi_hinge": "PA-CF segmented hinges with replaceable pins",
        "watch_link_reinforced": "PA-CF or TPU/PA co-design, watch-link inspired reinforced geometry",
        "hybrid_tpu_rigid_inserts": "TPU body with rigid PA-CF inserts and internal cable guide",
    }
    return materials.get(variant, "Configured flexible-link material")


def _counterweight(doc, config: BuildConfig):
    cw = config.data["counterweight"]
    profile = _counterweight_profile(cw)
    length = float(profile["carrier_length"])
    width = float(profile["carrier_width"])
    height = float(profile["carrier_height"])
    shape = rounded_box(length, width, height, 5)
    pocket = rounded_box(length - 12, width - 8, height - 5, 3)
    pocket.translate(v(0, 0, 4))
    shape = shape.cut(pocket)
    for x in (-length / 2 + 10, length / 2 - 10):
        shape = shape.cut(cylinder(float(cw["screw_clearance_diameter"]), height + 2, x, 0, -1))
    shape.translate(v(0, -95, -12))
    obj = add_shape(doc, "removable_counterweight_carrier", shape)
    meta = {
        "part": obj.Name,
        "qty": 1,
        "material": f"Printed carrier with removable {profile['material']} mass",
        "notes": f"Selected counterweight profile {cw.get('selected_profile', 'configured')}, target mass {profile['mass_g']} g",
    }
    return obj, meta


def _counterweight_profile(cw: dict[str, Any]) -> dict[str, Any]:
    if "profiles" not in cw:
        return {
            "mass_g": cw.get("mass_target_g", 0),
            "material": "configured_mass",
            "carrier_length": cw["carrier_length"],
            "carrier_width": cw["carrier_width"],
            "carrier_height": cw["carrier_height"],
        }
    return cw["profiles"][cw["selected_profile"]]


def _export_assembly_step(doc, out_dir: Path, design_id: str) -> None:
    objs = [obj for obj in doc.Objects if hasattr(obj, "Shape")]
    Part.export(objs, str(out_dir / f"{design_id}_assembly.step"))


def _export_dxf_templates(config: BuildConfig, out_dir: Path) -> None:
    panel = config.panel
    path = out_dir / "solar_panel_adhesive_template.dxf"
    path.write_text(
        "\n".join(
            [
                "0",
                "SECTION",
                "2",
                "ENTITIES",
                *_dxf_rect(-panel.length / 2, -panel.width / 2, panel.length, panel.width),
                "0",
                "ENDSEC",
                "0",
                "EOF",
                "",
            ]
        ),
        encoding="utf-8",
    )


def _dxf_rect(x: float, y: float, length: float, width: float) -> list[str]:
    points = [(x, y), (x + length, y), (x + length, y + width), (x, y + width), (x, y)]
    lines: list[str] = []
    for start, end in zip(points, points[1:]):
        lines.extend(["0", "LINE", "8", "SOLAR_PANEL", "10", str(start[0]), "20", str(start[1]), "11", str(end[0]), "21", str(end[1])])
    return lines


def _export_pdf_summary(doc, out_dir: Path, config: BuildConfig, design_id: str) -> None:
    text = f"{config.name} {config.revision} - mechanical summary"
    _write_minimal_pdf(out_dir / f"{design_id}_summary.pdf", text)


def _write_minimal_pdf(path: Path, text: str) -> None:
    stream = f"BT /F1 14 Tf 72 760 Td ({text}) Tj ET"
    objects = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        f"<< /Length {len(stream)} >>\nstream\n{stream}\nendstream",
    ]
    body = "%PDF-1.4\n"
    offsets = [0]
    for idx, obj in enumerate(objects, start=1):
        offsets.append(len(body.encode("latin-1")))
        body += f"{idx} 0 obj\n{obj}\nendobj\n"
    xref = len(body.encode("latin-1"))
    body += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n"
    for offset in offsets[1:]:
        body += f"{offset:010d} 00000 n \n"
    body += f"trailer << /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n"
    path.write_bytes(body.encode("latin-1"))
