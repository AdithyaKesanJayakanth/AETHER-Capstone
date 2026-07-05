# AI Usage and Research Ownership — Project AETHER

*Author: Adithya Kesan Jayakanth. Statement of policy, June 2026.*

My goal in AETHER is to develop my understanding of aerodynamics, computational methods and research judgment. I will use AI as a tutor, programming assistant and critical reviewer, while retaining responsibility for the research decisions and conclusions.

Before asking AI to implement a task, I will write down the physical purpose, relevant assumptions, intended algorithm and expected behavior. I will first attempt the parts central to my learning, including defining the capsule geometry, understanding drag and heat-flux calculations, choosing boundary conditions and interpreting convergence.

I may use AI to explain unfamiliar concepts, suggest debugging approaches, draft routine scripts, improve code organization and review my writing. When learning a new concept, I will ask for explanations and hints, then work through the reasoning independently.

I will review and test AI-assisted code before accepting it. For code that affects geometry, simulation configuration, force normalization, heat-flux extraction or design ranking, I will be able to explain its logic, modify it and identify how an error could affect the conclusions.

I will verify technical claims against official documentation and primary research sources. Numerical results will be checked through reference comparisons, mesh refinement and physical consistency checks. AI-generated explanations or tests alone will not establish that a model is correct.

I will make and document the final choices about the design space, CFD assumptions, comparison criteria and interpretation of results. AI may suggest possibilities or challenge an explanation; I will decide what the evidence supports. I will preserve failed cases and findings that contradict my expectations.

My AI-use log will record the tool, task, significant assistance, changes I made and how I checked the output. I will also distinguish my own code from external libraries and identify the CFD solver's role.

The measure of successful AI use will be whether I can explain, reproduce and defend the work independently. My final disclosure will describe the assistance actually used and follow the requirements of each submission venue.

---

## AI-use log

Maintained by the author in `docs/ai_use_log.md` with one row per task, as the policy above requires (tool, task, significant assistance, changes made by the author, how the output was checked).

## Code provenance

| Component | Origin |
|---|---|
| `aether/` package (geometry, meshing, configuration, run control, post-processing, analysis, plots) | Project code, in this repository |
| SU2 v8.5.0 | External open-source CFD solver (compressible laminar Navier–Stokes, axisymmetric formulation, isothermal wall, force and heat-flux integration). Built from the tagged release; no modifications. |
| Gmsh 4.15.2 | External mesh generator, evaluated for the unstructured alternative described in `docs/mesh.md` |
| ParaView 6.2.0 | External visualisation software (field plots and line probes via `pvpython`) |
| NumPy, SciPy, pandas, matplotlib, PyYAML, meshio | External Python libraries |
| Reference data in `data/reference/` | NASA technical reports (cited there), digitised or transcribed by the author |
