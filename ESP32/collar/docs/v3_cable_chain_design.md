# EXA Collar V3 Cable Carrier Chain

The V3 module union is a reinforced articulated cable carrier chain. It is not a
simple strap and it is not a rigid bridge.

## Functions

- Mechanically join the electronics and battery modules.
- Allow controlled flexion over the animal neck.
- Protect the internal cable bundle between sealed modules.

## Generated Pieces

- `cable_chain_link`: repeated reinforced links with internal cable tunnel,
  hinge barrels, bend stops and side ribs.
- `cable_chain_pin`: removable articulation pins, intended for A4 stainless or
  printed PA-CF prototypes.
- `cable_chain_cover`: removable upper covers for cable replacement.
- `cable_chain_end_mount`: bolted structural body mount with labyrinth/O-ring
  concept. It attaches to the module body, never to the lid.
- `cable_chain_grommet`: elastomer sealing interface at each module entry.
- `cable_chain_strain_relief`: clamp and bend-relief guide before the cable
  enters the sealed module.

## Cable Bundle

The protected tunnel is sized for:

- Battery positive
- Battery negative
- Battery measurement signal
- Optional I2C
- Optional UART
- Optional GPIO
- Future sensor conductors

## Design Intent

The chain is serviceable. A technician should be able to remove covers, replace
pins, replace a link, reroute conductors, or replace the full chain without
destroying the collar.

The end mounts are the sealing-critical region. Individual links are not IP67,
but the module body entries must be sealed with grommets, O-rings or equivalent
commercial elastomer hardware.
