# Mesh convergence and domain checks (baseline, mesh family B)

Levels refine every spacing by r = 1.5 (docs/mesh.md). GCI after Celik et al. (2008): Fs = 1.25 with the observed order when the triplet converges monotonically with shrinking differences; otherwise (oscillatory, or differences that grow with refinement, i.e. a negative observed order) the triplet is outside the asymptotic range and the conservative p = 1, Fs = 3 is used. GCI_fine is the uncertainty of the fine-level value, GCI_medium that of the medium-level (sweep) value.

| Quantity | coarse | medium | fine | observed order p | extrapolated | GCI fine | GCI medium |
|---|---:|---:|---:|---:|---:|---:|---:|
| C_D | 1.4612 | 1.4627 | 1.4605 | n/a (oscillatory) | n/a | 0.89 % | 0.60 % |
| q''_max shield (objective) [W/m^2] | 1.1284e+05 | 1.1056e+05 | 1.0931e+05 | 1.49 | 1.0781e+05 | 1.71 % | 3.10 % |
| q'' plateau median 0.1-0.5 [W/m^2] | 93816 | 91950 | 91234 | 2.36 | 90789 | 0.61 % | 1.58 % |
| q'' shoulder peak [W/m^2] | 1.1284e+05 | 1.1056e+05 | 1.0931e+05 | 1.49 | 1.0781e+05 | 1.71 % | 3.10 % |
| shock stand-off / D | 0.15399 | 0.15244 | 0.15138 | 0.94 | 0.1491 | 1.88 % | 2.73 % |

## Domain check (medium level, the sweep level)

| Check | C_D | Δ C_D | q''_max shield | Δ q''_max |
|---|---:|---:|---:|---:|
| far boundary 3.0 D / 7.0 D | 1.4625 | 0.01 % | 110495 | 0.05 % |

Absolute numerical uncertainty of a medium-level value: u_CD = 0.60 %, u_q = 3.10 % (largest of the medium-level GCI, the far-boundary sensitivity and the largest residual non-stationarity among converged sweep cases: drag 0.06 %, peak heating 0.46 % between the last two snapshots).

Family-C supplement: K05, S03, S03_fine enter the trade space from family C; its baseline differs from the family-B baseline by 0.00 % in C_D and 0.41 % in peak heating, which is added to the ranking margins.

## Ranking check (finalists at the fine level)

| Case | C_D / C_D,B00 medium | C_D / C_D,B00 fine | q''_max / q''_max,B00 medium | q''_max / q''_max,B00 fine |
|---|---:|---:|---:|---:|
| C41 | 1.0012 | 1.0014 | 0.9965 | 1.0004 |
| K03 | 0.9067 | 0.9088 | 0.9307 | 0.9341 |
| N10 | 0.9822 | 0.9846 | 0.9471 | 0.9471 |
| S03 (family C, ratios to its own baseline) | 1.0282 | 1.0301 | 1.0293 | 1.0149 |

Uncertainty of a design *difference* at the medium level (largest change of a ratio to the baseline between the medium and the fine level, the far-boundary sensitivity and the residual non-stationarity): u_CD = 0.24 %, u_q = 1.44 %. These are the margins used for the robust nondominated set; the absolute uncertainties above apply to any single value quoted against experiment.

## Cylinder benchmark levels

| Level | cells | C_D (1st order) | q''_stag (1st) [W/m^2] | C_D (2nd) | q''_stag (2nd) | q''_stag / Q_0 (2nd) |
|---|---:|---:|---:|---:|---:|---:|
| coarse | 23380 | 0.6300 | 498811 | 0.6275 | 504186 | 0.699 |
| medium | 52290 | 0.6293 | 516103 | 0.6273 | 519872 | 0.721 |
| fine | 117180 | 0.6294 | 554655 | 0.6278 | 547675 | 0.760 |
