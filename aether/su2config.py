"""Render SU2 configuration files from configs/su2_template.cfg.

A case is run in two stages with the same mesh:

  stage 1  first-order upwind (MUSCL off), CFL controlled by SU2's adaptive
           controller between 1 and 50. Establishes the bow shock from a
           uniform free-stream initial field without the start-up
           oscillations that often diverge second-order hypersonic runs.

Convective scheme: SLAU2 (Kitamura & Shima 2013) with the exact flux
Jacobian for the implicit system. This choice follows a documented test on
the Wieting cylinder (docs/validation.md): AUSM+-up2, AUSM, HLLC-type and
Roe fluxes on this shock-aligned grid developed the carbuncle instability
(kinked bow shock, non-decreasing residual), Roe with a large entropy fix
converged but tripled the wall heat flux, SLAU2 converged with the heat
flux at the experimental level.
  stage 2  restart from stage 1, second-order MUSCL with the Venkatakrishnan
           limiter, larger CFL. This is the solution used for all results.

For the planar cylinder benchmark both stages are run and both reported.
For the axisymmetric capsule runs only stage 1 is run: with SU2 v8.5.0 the
axisymmetric formulation combined with MUSCL reconstruction does not reach a
stationary state on the flat capsule face (stagnation pressure pulsating
above the pitot value) whatever the flux function, limiter or CFL, while
the same configuration is stationary in planar mode and the first-order
axisymmetric solution converges; see docs/validation.md section A.4. The
first-order discretisation error is quantified by the three-level mesh
study (Richardson extrapolation) and by the first/second-order comparison
on the cylinder benchmark.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Dict

TEMPLATE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "configs", "su2_template.cfg")

BC_LINES = {
    "capsule": "MARKER_SYM= ( axis )\nMARKER_FAR= ( farfield )",
    "capsule_truncated": "MARKER_SYM= ( axis )\nMARKER_FAR= ( farfield )\nMARKER_SUPERSONIC_OUTLET= ( outflow )",
    "capsule_wedge": "MARKER_SYM= ( symmetry_left, symmetry_right )\nMARKER_FAR= ( farfield )\nMARKER_SUPERSONIC_OUTLET= ( outflow )",
    "cylinder": "MARKER_SYM= ( symmetry )\nMARKER_FAR= ( farfield )\nMARKER_SUPERSONIC_OUTLET= ( outflow )",
}


@dataclass
class CaseSettings:
    kind: str                     # "capsule" | "cylinder"
    mach: float
    p_inf: float
    T_inf: float
    T_wall: float
    ref_length: float
    ref_area: float
    mesh: str = "mesh.su2"
    conv_scheme: str = "SLAU2"
    venkat: float = 0.05
    # stage 1
    s1_cfl: float = 0.5
    s1_cfl_min: float = 0.5
    s1_cfl_max: float = 30.0
    s1_iter: int = 3000
    s1_conv_resid: float = -10.0
    s1_cauchy_eps: float = 2e-5
    # stage 2
    s2_cfl: float = 1.0
    s2_cfl_min: float = 1.0
    s2_cfl_max: float = 50.0
    s2_iter: int = 8000
    s2_conv_resid: float = -10.0
    s2_cauchy_eps: float = 1e-5
    wrt_freq: int = 500
    run_stage2: bool = True   # second-order stage; disabled for axisymmetric capsule runs (docs/validation.md A.4)
    extra: Dict[str, str] = field(default_factory=dict)

    @property
    def axisymmetric(self) -> str:
        return "YES" if self.kind in ("capsule", "capsule_truncated") else "NO"


def _render(settings: CaseSettings, stage: int) -> str:
    with open(TEMPLATE) as fh:
        tpl = fh.read()
    common = dict(
        axisymmetric=settings.axisymmetric,
        mach=f"{settings.mach:.4f}",
        p_inf=f"{settings.p_inf:.6g}",
        T_inf=f"{settings.T_inf:.6g}",
        T_wall=f"{settings.T_wall:.4f}",
        ref_length=f"{settings.ref_length:.8g}",
        ref_area=f"{settings.ref_area:.10g}",
        bc_lines=BC_LINES[settings.kind],
        conv_scheme=settings.conv_scheme,
        venkat=f"{settings.venkat:g}",
        mesh=settings.mesh,
        wrt_freq=str(settings.wrt_freq),
        cfl_adapt="YES",
    )
    if stage == 1:
        spec = dict(restart_sol="NO", muscl="NO", cfl=f"{settings.s1_cfl:g}",
                    cfl_min=f"{settings.s1_cfl_min:g}", cfl_max=f"{settings.s1_cfl_max:g}",
                    iter=str(settings.s1_iter), conv_resid=f"{settings.s1_conv_resid:g}", cauchy_eps=f"{settings.s1_cauchy_eps:g}",
                    solution_in="restart_stage1.dat", restart_out="restart_stage1.dat",
                    history="history_stage1", volume="flow_stage1", surface="surface_stage1",
                    breakdown="forces_stage1.dat")
    else:
        spec = dict(restart_sol="YES", muscl="YES", cfl=f"{settings.s2_cfl:g}",
                    cfl_min=f"{settings.s2_cfl_min:g}", cfl_max=f"{settings.s2_cfl_max:g}",
                    iter=str(settings.s2_iter), conv_resid=f"{settings.s2_conv_resid:g}", cauchy_eps=f"{settings.s2_cauchy_eps:g}",
                    solution_in="restart_stage1.dat", restart_out="restart_stage2.dat",
                    history="history_stage2", volume="flow_stage2", surface="surface_stage2",
                    breakdown="forces_stage2.dat")
    values = {**common, **spec}
    out = tpl
    for k, v in values.items():
        out = out.replace("{" + k + "}", v)
    for k, v in settings.extra.items():
        # append/override simple KEY= VALUE options
        lines = out.splitlines()
        lines = [ln for ln in lines if not ln.startswith(k + "=")]
        if v != "__DELETE__":
            lines.append(f"{k}= {v}")
        out = "\n".join(lines) + "\n"
    body = "\n".join(ln for ln in out.splitlines() if not ln.startswith("%"))
    leftover = re.findall(r"\{[a-z_0-9]+\}", body)
    if leftover:
        raise ValueError(f"unfilled placeholders: {sorted(set(leftover))}")
    return out


def write_stage_configs(settings: CaseSettings, case_dir: str) -> Dict[int, str]:
    os.makedirs(case_dir, exist_ok=True)
    paths = {}
    for stage in (1, 2):
        path = os.path.join(case_dir, f"stage{stage}.cfg")
        with open(path, "w") as fh:
            fh.write(_render(settings, stage))
        paths[stage] = path
    return paths
