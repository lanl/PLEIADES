---
title: 'PLEIADES: Python Library Extensions for Isotopic Analysis via Detailed Examination of SAMMY results'
tags:
  - Python
  - neutron imaging
  - material science
  - non-destructive testing and evaluation

authors:
  - name: Alexander M. Long
    orcid: 0000-0003-4300-9454
    affiliation: 1
  - name: Tsviki Y. Hirsh
    orcid: 0000-0001-5889-4500
    affiliation: 2
  - name: Jean Bilheux
    orcid: 0000-0003-2172-6487
    affiliation: 3
  - name: Chen Zhang
    orcid: 0000-0001-8374-4467
    affiliation: 3
affiliations:
 - name: Los Alamos National Laboratory, Los Alamos, NM 87545,  USA
   index: 1
 - name: Soreq Nuclear Research Center, Yavne, 81800, Israel
   index: 2
 - name: Oak Ridge National Laboratory, Oak Ridge, TN 37830, USA
   index: 3
date: 07 Jan 2026
bibliography: paper.bib

---

## Summary

Neutron resonance transmission analysis is a non-destructive technique used to determine material composition from the isotope-specific interactions between neutrons and atomic nuclei.
As neutrons pass through a sample, they are absorbed or scattered in energy-dependent patterns that reflect the isotopes present.
Measuring these transmission spectra allows scientists to identify isotopes and quantify their abundances without altering the material.

**[TODO: Add a figure showing the workflow and how PLEIADES automates it.]**
Extracting these properties requires detailed physics-based modeling with R-matrix codes such as SAMMY [@Larson2008; @Dorothea2022].
The fitting process is labor-intensive: users must prepare input files, run the fit, examine large output files, and iteratively adjust parameters.
This cycle may repeat many times, and the workload grows significantly when analyzing energy-resolved neutron imaging data, where millions of spectra demand scaling and automation.

`PLEIADES` (Python Library Extensions for Isotopic Analysis via Detailed Examination of SAMMY results) is a Python software package that automates the end-to-end workflow around SAMMY.
The software generates input files, manages batch execution, and extracts isotopic densities and material parameters from fitting results.
By consolidating repetitive steps into a single, scriptable interface, `PLEIADES` reduces manual effort and enables large-scale analysis of neutron transmission data.
The package supports both expert users and researchers who are not specialists in nuclear reaction theory.

`PLEIADES` has been used in recent neutron imaging publications [@Hirsh2025a; @Hirsh2025b] and is the primary resonance analysis tool for the VENUS beamline at the Spallation Neutron Source [@Bilheux2023] and the ENRI/FP5 instrument at the Los Alamos Neutron Science Center [@Nelson2018].
The source code is archived on Zenodo [@pleiades_zenodo].

## Statement of Need

R-matrix fitting with SAMMY remains the standard approach for extracting resonance parameters and isotopic densities from neutron transmission data, but the workflow is highly manual and requires deep understanding of the domain specific software.
Users must craft structured input files, manage repeated fit iterations, and parse lengthy SAMMY outputs.
These requirements limit throughput and create an entry barrier for researchers who need neutron resonance analysis but are not experts in nuclear reaction modeling.

`PLEIADES` addresses this gap by automating input generation, execution control, and output extraction in a domain-specific manner.
Existing workflow tools do not integrate with SAMMY or handle the conventions of resonance analysis.
`PLEIADES` provides SAMMY-aware automation, scaling, and data handling designed specifically for transmission analysis and energy-resolved neutron imaging.
This allows faster, reproducible, and more accessible workflows across a wide range of applications.

## State of the Field

Neutron resonance imaging produces large collections of energy-resolved transmission spectra, but imaging-specific analysis software remains relatively limited.
To our knowledge, TRINIDI is currently the only dedicated open-source code that enables fast isotopic reconstructions from time-of-flight neutron resonance imaging data [@Trinidi2024].
TRINIDI’s approach leverages tabulated neutron total cross sections, which is efficient for high-throughput inference but does not allow direct adjustment of the underlying cross section model through resonance-parameter variation.

In contrast, SAMMY is widely used for neutron resonance transmission analysis and provides a comprehensive suite of R-matrix fitting capabilities [@Larson2008; @Dorothea2022].
SAMMY constructs cross sections from user-specified resonance parameters and updates those parameters through Bayesian fitting [@Larson2008], enabling physics-informed refinement when resonance parameters, sample conditions, or model assumptions must be varied and validated against measured transmission data.
Although SAMMY is widely adopted, its primary user interface is a command-line workflow based on fixed-width input files and text-based outputs.
The software exposes a large number of modeling options and control parameters that must be specified explicitly, and its outputs can be difficult to interpret without substantial domain expertise.
This complexity presents a barrier for new users and can inhibit adoption beyond the specialist nuclear data and resonance analysis community.
As a result, many groups build local scripts to generate inputs, manage repeated fit cycles, and parse outputs for downstream analysis, often resulting in workflows that are difficult to reuse, audit, and scale to large imaging datasets.

`PLEIADES` enables SAMMY to be used in the larger-scale and more complex workflows encountered in neutron resonance imaging.
Rather than re-implementing R-matrix physics, `PLEIADES` streamlines SAMMY usage by providing a SAMMY-aware workflow layer that standardizes common modes of analysis (e.g., single-spectrum studies, iterative refinement, and high-throughput per-region or per-pixel fitting).
It reduces user burden by handling many routine decisions and bookkeeping steps “behind the scenes,” including format-validated input templating, consistent file and run management, and structured extraction of fit outputs into analysis-ready data products.
This approach preserves SAMMY’s trusted modeling capabilities while improving usability, reproducibility, and scalability for imaging datasets where manual trial-and-error workflows and ad hoc parsing scripts do not translate to millions of spectra.


## Software Design

`PLEIADES` is designed as a *workflow and data-management layer* around SAMMY rather than a re-implementation of R-matrix physics.
The primary design goal is to make SAMMY-based resonance analysis reproducible and scalable (from a single spectrum to large imaging datasets) while keeping expert-level control available when needed.

### Design principles and trade-offs

- **Preserve SAMMY as the fitting engine.**
  `PLEIADES` delegates cross section construction and Bayesian parameter estimation to SAMMY. The trade-off is that analysis remains constrained by SAMMY’s file-based interfaces and run-time characteristics, which `PLEIADES` mitigates through automation and structured inputs and outputs.

- **Standardize common analysis modes with override points.**
  The library provides high-level, SAMMY-aware workflows (e.g., single-spectrum fits, iterative refinement loops, and high-throughput region/pixel processing) that encode routine choices such as input structure, run directory layout, and output harvesting.
  Advanced users can still customize templates, fitting controls, and run options when deviating from defaults is scientifically necessary.

- **Emphasize validation and provenance to prevent runtime errors**
  SAMMY inputs are generated from pydantic models with format and option checks to reduce any SAMMY run-time failures and to make analysis reproducible and auditable if needed.


## TODO sections

```bash
Your paper must include the following required sections:

✅ Summary: A description of the high-level functionality and purpose of the software for a diverse, non-specialist audience.
✅ Statement of need: A section that clearly illustrates the research purpose of the software and places it in the context of related work. This should clearly state what problems the software is designed to solve, who the target audience is, and its relation to other work.
✅ State of the field: A description of how this software compares to other commonly-used packages in the research area. If related tools exist, provide a clear “build vs. contribute” justification explaining your unique scholarly contribution and why existing alternatives are insufficient.
✅ Software Design: An explanation of the trade-offs you weighed, the design/architecture you chose, and why it matters for your research application. This should demonstrate meaningful design thinking beyond a superficial code structure description.
⁉️ Research Impact Statement: Evidence of realized impact (publications, external use, integrations) or credible near-term significance (benchmarks, reproducible materials, community-readiness signals). The evidence should be compelling and specific, not aspirational.
⁉️ AI usage disclosure: Transparent disclosure of any use of generative AI in the software creation, documentation, or paper authoring. If no AI tools were used, state this explicitly. If AI tools were used, describe how they were used and how the quality and correctness of AI-generated content was verified.
```

## Key Features

- Automated creation of SAMMY input files for neutron transmission fitting
- Batch execution management for large datasets
- Extraction of isotopic densities and material parameters from SAMMY outputs
- Support for energy-resolved neutron imaging workflows with millions of spectra
- Interfaces for managing ENDF-formatted nuclear data
- Configurable templates for reproducible and scalable analysis
- Python API suitable for scripting, interactive analysis, and integration with other tools

## Author Contributions [TODO]

## AI usage disclosure [TODO]

## Acknowledgements

Work was supported in part through the Nuclear Science User Facilities (NSUF), under DOE Idaho Operations Office Contract DE-AC07-05ID14517.
This research used resources at the Spallation Neutron Source, a U.S. Department of Energy Office of Science User Facility operated by Oak Ridge National Laboratory under Contract No. DE‑AC05‑00OR22725.
Resonance imaging measurements were carried out on the VENUS instrument at the SNS.
