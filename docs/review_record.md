# Technical review record

*Project AETHER — Adithya Kesan Jayakanth. Planned review period: August 2026.*

Reviewer names, affiliations and dates are entered only once a review has actually been received. Each comment is answered with what was changed (file, figure, number) or why no change was made.

## Review requests

| # | Scope requested | Material sent | Date sent | Status |
|---|---|---|---|---|
| R1 | Geometry definition and closure rule (docs/geometry.md) | docs/geometry.md, docs/figure_geometry_baseline.svg | | not yet sent |
| R2 | CFD assumptions, conditions and numerical settings (docs/conditions.md, configs/) | docs/conditions.md, configs/su2_template.cfg, docs/validation.md | | not yet sent |
| R3 | Mesh convergence and validation evidence (docs/mesh.md, docs/validation.md) | docs/mesh.md, docs/validation.md, results/figures | | not yet sent |
| R4 | Conclusions and limitations (docs/report/report.md) | docs/report/report.pdf | | not yet sent |

## Comments received and responses

| # | Reviewer | Date | Comment (paraphrased) | Response / change made | Commit |
|---|---|---|---|---|---|
| | | | | | |

## Open items carried from the technical work

Items the author flagged for reviewers before any external comment was received:

1. SU2 v8.5.0 axisymmetric near-axis behaviour and the patch applied (docs/validation.md A.3): is the treatment acceptable, and does the sphere check justify using the near-axis heat-flux values?
2. Residual plateau with limited second-order upwind schemes: the convergence criterion is stationarity of drag and peak heating (0.1 % over 500 iterations); is that sufficient?
3. Wake exclusion (outlet plane normal to the cone end) and the quantified base-drag bound.
4. Perfect-gas assumption at T0 = 1056 K and the Sutherland extrapolation to 49 K free-stream temperature.
5. Digitised reference data uncertainty and the choice of the q''_t normalisation station.
