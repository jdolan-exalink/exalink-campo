# EXA Collar V3 Flexible Link Variants

The flexible link is treated as a replaceable, configurable mechanical fuse. It
must absorb impacts and torsion before high loads reach the sealed module walls
or lid screws.

## Variant A: `articulated_chain`

Discrete rigid links with pin-like hinge features. Best for high serviceability
and predictable articulation. The main risk is dirt accumulation in hinge gaps,
so this variant should be tested with mud and manure exposure before field use.

## Variant B: `reinforced_tpu_band`

Continuous flexible band with a protected internal cable tunnel. Best for
sealing and impact absorption. A future production version should consider
overmolded fiber or stainless reinforcement.

## Variant C: `multi_hinge`

Short repeated hinge segments. Best when bending radius must be controlled more
strictly than a plain TPU strap. It needs fatigue testing around hinge roots.

## Variant D: `watch_link_reinforced`

Default V3 profile. It uses short repeated link masses inspired by watch straps
without copying any commercial geometry. It balances articulation, protection
and manufacturability for the first EXA Collar industrial prototype.

## Variant E: `hybrid_tpu_rigid_inserts`

TPU main body with periodic rigid insert zones. Best long-term candidate for
comfort plus durability, especially if production moves toward overmolding.

## Cable Protection Requirements

- Internal cable tunnel is always generated.
- Strain-relief guides are generated at both module interfaces.
- Cable bend radius is controlled by `flexible_link.bend_relief_radius`.
- Module entry uses a gland feature defined by `seal_gland_diameter`.
- Cables should be routed as a service loop inside each module, not tensioned
  across the flexible link.

