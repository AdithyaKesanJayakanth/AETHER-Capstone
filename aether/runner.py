"""Launch SU2 for a case directory and record what happened.

Binary selection (environment variable AETHER_SU2 overrides):
  tools/su2-native/bin/SU2_CFD  (arm64, MPI)   -> run with mpirun -n NP
  tools/su2-rosetta/bin/SU2_CFD (x86_64 serial) -> run serially under Rosetta 2

Every run writes <stage>.log in the case directory and a run_<stage>.json
record with the binary, number of ranks, wall time, exit code, last
iteration and whether the run diverged (NaN in the residual history or a
non-zero exit). Nothing is deleted on failure: failed runs are evidence.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import time
from typing import Optional

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NATIVE = os.path.join(ROOT, "tools", "su2-native", "bin", "SU2_CFD")
ROSETTA = os.path.join(ROOT, "tools", "su2-rosetta", "bin", "SU2_CFD")


def pick_binary() -> tuple[str, str]:
    env = os.environ.get("AETHER_SU2")
    if env:
        return env, ("native-mpi" if "native" in env else "custom")
    if os.path.exists(NATIVE):
        return NATIVE, "native-mpi"
    if os.path.exists(ROSETTA):
        return ROSETTA, "rosetta-serial"
    raise FileNotFoundError("no SU2_CFD found; run scripts/install_su2.sh")


def su2_version(binary: str) -> str:
    out = subprocess.run([binary, "--help"], capture_output=True, text=True).stdout
    m = re.search(r"SU2 v[\d.]+ \"[^\"]+\"", out)
    ver = m.group(0) if m else "unknown"
    marker = os.path.join(os.path.dirname(os.path.dirname(binary)), "PATCHES.txt")
    if os.path.exists(marker):
        ver += " + PR2715 near-axis patch"
    return ver


def _last_history_row(path: str) -> Optional[dict]:
    if not os.path.exists(path):
        return None
    with open(path) as fh:
        header = fh.readline()
        last = None
        for line in fh:
            if line.strip():
                last = line
    if last is None:
        return None
    keys = [k.strip().strip('"') for k in header.split(",")]
    vals = [v.strip() for v in last.split(",")]
    return dict(zip(keys, vals))


def run_stage(case_dir: str, stage: int, nproc: int = 8, timeout_s: int = 6 * 3600,
              binary: Optional[str] = None) -> dict:
    cfg = f"stage{stage}.cfg"
    if binary is None:
        binary, flavour = pick_binary()
    else:
        flavour = "native-mpi" if "native" in binary else "rosetta-serial"
    if flavour == "native-mpi" and nproc > 1 and shutil.which("mpirun"):
        cmd = ["mpirun", "-n", str(nproc), binary, cfg]
    else:
        cmd = [binary, cfg]
        nproc = 1
    log = os.path.join(case_dir, f"stage{stage}.log")
    t0 = time.time()
    rec = {"stage": stage, "binary": binary, "flavour": flavour, "nproc": nproc,
           "cmd": " ".join(cmd), "su2_version": su2_version(binary), "started": time.strftime("%Y-%m-%dT%H:%M:%S")}
    with open(log, "w") as fh:
        try:
            proc = subprocess.run(cmd, cwd=case_dir, stdout=fh, stderr=subprocess.STDOUT, timeout=timeout_s)
            rec["exit_code"] = proc.returncode
            rec["timed_out"] = False
        except subprocess.TimeoutExpired:
            rec["exit_code"] = -1
            rec["timed_out"] = True
    rec["wall_time_s"] = round(time.time() - t0, 1)
    hist = _last_history_row(os.path.join(case_dir, f"history_stage{stage}.csv"))
    rec["last_history"] = hist
    diverged = rec["exit_code"] != 0
    if hist:
        for k, v in hist.items():
            # only physically meaningful monitors; SU2 reports NaN for the
            # (irrelevant) buffet sensor on axisymmetric cases
            if k.startswith(("rms[", "CD", "CL", "HF", "maxHF")) and v.lower() in ("nan", "-nan", "inf", "-inf"):
                diverged = True
    with open(log) as fh:
        tail = fh.read()[-4000:]
    if "SU2 has diverged" in tail or "Exit Success" not in tail:
        diverged = True
    rec["diverged"] = diverged
    with open(os.path.join(case_dir, f"run_stage{stage}.json"), "w") as fh:
        json.dump(rec, fh, indent=2)
    return rec


def run_case(case_dir: str, nproc: int = 8, timeout_s: int = 6 * 3600) -> dict:
    """Run stage 1 then (if enabled for the case) stage 2. Stage 2 is skipped
    if stage 1 diverged."""
    r1 = run_stage(case_dir, 1, nproc, timeout_s)
    if r1["diverged"]:
        return {"stage1": r1, "stage2": None}
    run2 = True
    cj = os.path.join(case_dir, "case.json")
    if os.path.exists(cj):
        with open(cj) as fh:
            run2 = json.load(fh).get("settings", {}).get("run_stage2", True)
    if not run2:
        return {"stage1": r1, "stage2": None}
    r2 = run_stage(case_dir, 2, nproc, timeout_s)
    return {"stage1": r1, "stage2": r2}
