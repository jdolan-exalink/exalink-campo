# EXA Collar - Mechanical V3

Parametric mechanical design for the EXA Collar smart cattle collar.

The model is generated entirely from Python for FreeCAD. It creates two sealed
independent modules joined by a reinforced articulated cable carrier chain, with solar panel
recesses on top lids, strap ears, screw bosses, component posts, O-ring lid
channels, cable routing, strain relief and a removable lower counterweight
support.

## Quick Start

Run the complete export pipeline with FreeCAD:

```bash
freecadcmd scripts/build_freecad.py --pass --config configs/v3_default.yaml --out outputs/v3
```

The same command can be run with Python for non-CAD deliverables only:

```bash
python -m exa_collar.build --config configs/v3_default.yaml --out outputs/v3 --no-cad
```

## Outputs

The build command writes:

- `FCStd`
- `STEP`
- `STL`
- `DXF` panel adhesive templates
- `BOM` as CSV and JSON
- `PDF` build summary when FreeCAD is available
- `render_top_view.svg` technical top-view render

## Project Layout

- `configs/`: collar profiles and mechanical parameters
- `panels/`: commercial solar panel catalog entries in YAML
- `exa_collar/`: Python generator package
- `outputs/`: generated files

## Design Notes

This is an original EXA Collar platform. It intentionally avoids copying
commercial collar geometry and uses parametric primitives suitable for FDM first
and future plastic injection evolution:

- M3 stainless fasteners with heat-set inserts
- independent sealed volumes per module
- commercial O-rings with configurable compression
- top-only service lids with centering ribs and compression limiters
- replaceable adhesive solar panels with integrated protective frames
- large radii and reinforced strap ears
- removable lids and serviceable electronics/battery packs
- reinforced articulated cable carrier chain with protected internal cable channel
- removable lower counterweight carrier

## Cable Chain

The primary V3 union is configured under `cable_chain`. It generates:

- `cable_chain_link`
- `cable_chain_pin`
- `cable_chain_cover`
- `cable_chain_end_mount`
- `cable_chain_grommet`
- `cable_chain_strain_relief`

The chain is inspired by industrial cable carriers, but is adapted for a cattle collar: reinforced links, removable covers, internal cable channel, bend stops, body-mounted end mounts, grommets and strain relief.
