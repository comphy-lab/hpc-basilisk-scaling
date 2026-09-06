# Simulation sequences

These compact inputs reproduce the image panels accompanying the benchmark
curves. They come from separately completed simulations and are not snapshots
of the ten-step timing runs. Each directory records its source and checksums
in `provenance.json` and its attribution/reuse terms in `LICENSE.md`.

| Panel | Source and content | Rendered field |
|---|---|---|
| Bursting bubble | SingularJets2026 case 5003, $Oh=0.03$, $Bo=0$, near jet inception | Speed divided by the capillary velocity, instantaneous streamlines, VOF interface |
| Elastic Taylor–Culick | Completed axisymmetric case 3040, $Ec=0.1$, $Oh=0.05$ | Speed divided by the Taylor–Culick velocity and azimuthal log-conformation |
| Newtonian drop impact | Case 1082, diameter-based $We_D=200$, $Oh_D=0.01$ | Speed divided by impact velocity, instantaneous streamlines, VOF interface |
| 3D coalescence | *When do coalescing drops jump?*, $Oh=0.05$, $Bo=0$ | Orange free surface and adaptive mesh |

Each sequence reads left to right, then top to bottom:

| Sequence | Dimensionless times |
|---|---|
| Bursting, $t^*=tV_c/R$ | 0.492500, 0.494219, 0.496719, 0.499844 |
| Taylor–Culick, $t/t_\gamma$ | 17.30, 53.30, 74.90, 119.30 |
| Impact, $tU_0/R$ | 0.05, 0.22, 0.44, 4.19 |
| Coalescence, $t/\tau_\gamma$ | 0.24, 1.00, 1.75, 3.00 |

The bursting and impact inputs are extracted fields and geometric interface
segments. The Taylor–Culick and coalescence inputs retain the existing render
pixels; their compositors crop and arrange them without changing the field
colours or stretching the geometry. The coalescence example is labelled as a
separate 3D illustration below the VE3D impact timing curve.

Reproduction commands are in the repository README. Raw simulation snapshots
are not required for the normal plotting path and are not stored here. The
optional drop-impact re-extraction uses the checksum-identified snapshot and
the project-local Basilisk `v2026-07-20` pin recorded in its provenance.
