# Mesh convergence and domain checks (baseline)

Levels refine every spacing by r = 1.5 (docs/mesh.md). GCI after Celik et al. (2008), Fs = 1.25 for a monotone triplet, else p = 1 and Fs = 3.

| Quantity | coarse | medium | fine | observed order p | extrapolated | GCI medium | GCI coarse |
|---|---:|---:|---:|---:|---:|---:|---:|
| C_D | 1.462 | 1.4628 | 1.4615 | n/a (non-monotone) | 1.4589 | 0.31 % | 0.47 % |
| q''_max shield (objective) [W/m^2] | 1.1339e+05 | 1.1074e+05 | 1.0583e+05 | 1.53 | 1.0011e+05 | 3.47 % | 6.45 % |
| q'' plateau median 0.1-0.5 [W/m^2] | 90529 | 91867 | 90596 | n/a (non-monotone) | 88054 | 8.73 % | 13.10 % |
| q'' shoulder peak [W/m^2] | 1.1339e+05 | 1.1074e+05 | 1.0583e+05 | 1.53 | 1.0011e+05 | 3.47 % | 6.45 % |
| shock stand-off / D | 0.15386 | 0.15239 | 0.15065 | 0.41 | 0.14109 | 6.64 % | 7.85 % |

## Domain check (medium level, the sweep level)

| Check | C_D | Δ C_D | q''_max shield | Δ q''_max |
|---|---:|---:|---:|---:|
| far boundary 3.0 D / 7.0 D | 1.4626 | 0.01 % | 110688 | 0.05 % |

Uncertainty used in the trade-space analysis (medium level): u_CD = 0.31 %, u_q = 3.47 % (largest of the medium-level GCI, the far-boundary sensitivity and the largest residual non-stationarity among converged sweep cases: drag 0.11 %, peak heating 1.21 % between the last two snapshots).

## Cylinder benchmark levels

| Level | cells | C_D (1st order) | q''_stag (1st) [W/m^2] | C_D (2nd) | q''_stag (2nd) | q''_stag / Q_0 (2nd) |
|---|---:|---:|---:|---:|---:|---:|
| coarse | 23380 | 0.6300 | 498811 | 0.6275 | 504186 | 0.699 |
| medium | 52290 | 0.6293 | 516103 | 0.6273 | 519872 | 0.721 |
| fine | 117180 | 0.6294 | 554655 | 0.6278 | 547675 | 0.760 |
