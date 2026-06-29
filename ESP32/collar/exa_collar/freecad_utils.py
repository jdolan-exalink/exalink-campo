from __future__ import annotations

import math
from pathlib import Path
from typing import Iterable


try:
    import FreeCAD as App  # type: ignore
    import Part  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - exercised outside freecadcmd.
    App = None
    Part = None


def require_freecad() -> None:
    if App is None or Part is None:
        raise RuntimeError("FreeCAD Python modules are not available. Run with freecadcmd.")


def v(x: float, y: float, z: float):
    require_freecad()
    return App.Vector(float(x), float(y), float(z))


def rounded_box(length: float, width: float, height: float, radius: float):
    require_freecad()
    shape = Part.makeBox(length, width, height, v(-length / 2, -width / 2, 0))
    return shape


def cylinder(diameter: float, height: float, x: float, y: float, z: float = 0):
    require_freecad()
    return Part.makeCylinder(diameter / 2, height, v(x, y, z))


def cut_all(base, cutters: Iterable):
    shape = base
    for cutter in cutters:
        shape = shape.cut(cutter)
    return shape


def add_shape(doc, name: str, shape):
    obj = doc.addObject("Part::Feature", name)
    obj.Shape = shape
    return obj


def export_shape(obj, out_dir: Path, basename: str) -> None:
    require_freecad()
    out_dir.mkdir(parents=True, exist_ok=True)
    Part.export([obj], str(out_dir / f"{basename}.step"))
    obj.Shape.exportStl(str(out_dir / f"{basename}.stl"))


def make_arc_points(radius: float, start_deg: float, end_deg: float, z: float, count: int = 16):
    points = []
    for i in range(count):
        t = i / (count - 1)
        angle = math.radians(start_deg + (end_deg - start_deg) * t)
        points.append(v(radius * math.sin(angle), 0, z + radius * (1 - math.cos(angle))))
    return points
