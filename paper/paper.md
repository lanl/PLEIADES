---
title: 'PLEIADES: Python Library Extensions for Isotopic Analysis via Detailed Examination of SAMMY results'
tags:
  - Python
  - neutron imaging
  - material science
  - non-descrutive testing and evaluation

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
date: 16 August 2024
bibliography: paper.bib

---

# Summary

Neutron resonance transmission analysis is a non-destructive technique used to determine material composition from the isotope-specific interactions between neutrons and atomic nuclei. As neutrons pass through a sample, they are absorbed or scattered in energy-dependent patterns that reflect the isotopes present. Measuring these transmission spectra allows scientists to identify isotopes and quantify their abundances without altering the material.

Extracting these properties requires detailed physics-based modeling with R-matrix codes such as SAMMY [@Larson2008; @Dorothea2022]. The fitting process is labor-intensive: users must prepare input files, run the fit, examine large output files, and iteratively adjust parameters. This cycle may repeat many times, and the workload grows significantly when analyzing energy-resolved neutron imaging data, where millions of spectra demand scaling and automation.

`PLEIADES` (Python Library Extensions for Isotopic Analysis via Detailed Examination of SAMMY results) is a Python software package that automates the end-to-end workflow around SAMMY. The software generates input files, manages batch execution, and extracts isotopic densities and material parameters from fitting results. By consolidating repetitive steps into a single, scriptable interface, `PLEIADES` reduces manual effort and enables large-scale analysis of neutron transmission data. The package supports both expert users and researchers who are not specialists in nuclear reaction theory.

`PLEIADES` has been used in recent neutron imaging publications [@Hirsh2025a; @Hirsh2025b] and is the primary resonance analysis tool for the VENUS beamline at the Spallation Neutron Source [@Bilheux2023] and the ENRI/FP5 instrument at the Los Alamos Neutron Science Center [@Nelson2018]. The source code is archived on Zenodo [@pleiades_zenodo].

# Statement of Need

R-matrix fitting with SAMMY remains the standard approach for extracting resonance parameters and isotopic densities from neutron transmission data, but the workflow is highly manual. Users must craft structured input files, manage repeated fit iterations, and parse lengthy SAMMY outputs. These requirements limit throughput and create an entry barrier for researchers who need neutron resonance analysis but are not experts in nuclear reaction modeling.

`PLEIADES` addresses this gap by automating input generation, execution control, and output extraction in a domain-specific manner. Existing workflow tools do not integrate with SAMMY or handle the conventions of resonance analysis. `PLEIADES` provides SAMMY-aware automation, scaling, and data handling designed specifically for transmission analysis and energy-resolved neutron imaging. This allows faster, reproducible, and more accessible workflows across a wide range of applications.

# Key Features

- Automated creation of SAMMY input files for neutron transmission fitting  
- Batch execution management for large datasets  
- Extraction of isotopic densities and material parameters from SAMMY outputs  
- Support for energy-resolved neutron imaging workflows with millions of spectra  
- Interfaces for managing ENDF-formatted nuclear data  
- Configurable templates for reproducible and scalable analysis  
- Python API suitable for scripting, interactive analysis, and integration with other tools  

# Acknowledgements