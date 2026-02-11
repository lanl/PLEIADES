PLEIADES YAML config + workflow (draft)
======================================

Purpose
-------
This note defines the draft YAML structure that instructs PLEIADES how to process data,
configure SAMMY, and execute fitting routines. It reflects the desired directory layout
for multi-fit workflows and serves as a working specification for end-to-end operation.

Backbone + reproducibility intent
---------------------------------
The YAML file is intended to be the backbone structure for running PLEIADES. It should:
- Define the complete workspace layout for consistent file placement.
- Declare datasets and fit routines in a single, structured source of truth.
- Record each run as an append-only entry for analysis provenance and reproducibility.
- Capture configuration inputs (fit options, nuclear parameters, data sources) alongside
  execution details (backend, paths, outputs) to enable re-running or auditing results.
This makes the config both an operational entry point and a durable record of analysis.

Directory layout
----------------
working_dir/
  endf_dir/
    isotope_dir_1/
      results_dir/
      dummy.inp
      dummy.par
    isotope_dir_2/
      ...
  fitting_dir/
    <routine_id>/
      results_dir/
      input.inp
      params.par
  results_dir/
    run_results_*.json
    results_map.json
  data_dir/
    <routine_id>.dat
  image_dir/
    ...
  config.yaml

Notes:
- The SAMMY fit directory is named after the routine_id.
- The data file for a run is keyed by routine_id: data_dir/<routine_id>.dat
- endf_dir should map to PleiadesConfig.nuclear_data_cache_dir so NuclearDataManager
  uses it for ENDF caching.

Draft YAML schema (example)
---------------------------
pleiades_version: 2

workspace:
  root: /path/to/working_dir
  endf_dir: ${workspace.root}/endf_dir
  fitting_dir: ${workspace.root}/fitting_dir
  results_dir: ${workspace.root}/results_dir
  data_dir: ${workspace.root}/data_dir
  image_dir: ${workspace.root}/image_dir

nuclear:
  sources:
    DIRECT: https://www-nds.iaea.org/public/download-endf
    API: https://www-nds.iaea.org/exfor/servlet
  default_library: ENDF-B-VIII.0
  isotopes:
    - isotope: "U-235"
      abundance: 0.0072
      vary_abundance: 0
      endf_library: ENDF-B-VIII.0
    - isotope: "U-238"
      abundance: 0.9928
      vary_abundance: 0

sammy:
  backend: local  # local | docker | nova
  local:
    sammy_executable: /path/to/sammy
    shell_path: /bin/bash
    env_vars: {}
  docker:
    image_name: kedokudo/sammy-docker
    container_working_dir: /sammy/work
    container_data_dir: /sammy/data
  nova:
    url: ${NOVA_URL}
    api_key: ${NOVA_API_KEY}
    tool_id: neutrons_imaging_sammy
    timeout: 3600

datasets:
  example_dataset:
    description: "Natural Si transmission"
    data_kind: raw_imaging  # raw_imaging | sammy_dat | sammy_twenty
    raw:
      facility: ornl
      sample_folders:
        - /path/to/sample/run_1
      ob_folders:
        - /path/to/ob/run_1
      nexus_dir: /path/to/nexus
      roi:
        x1: 0
        y1: 0
        width: 512
        height: 512
      image_dir: ${workspace.image_dir}
    processed:
      transmission_files: []
      energy_units: eV
      cross_section_units: barn
    path_to_data_files: ${workspace.data_dir}/example_fit.dat
    metadata: {}

fit_routines:
  example_fit:
    dataset_id: example_dataset
    mode: fitting  # fitting | endf_extraction | multi_isotope
    update_from_results: false
    fit_config:
      fit_title: "SAMMY Fit"
      tolerance: null
      max_iterations: 1
      i_correlation: 50
      max_cpu_time: null
      max_wall_time: null
      max_memory: null
      max_disk: null
      nuclear_params: {}         # pleiades.nuclear.models.nuclearParameters
      physics_params: {}         # pleiades.experimental.models.PhysicsParameters
      data_params: {}            # pleiades.sammy.data.options.SammyData
      options_and_routines: {}   # pleiades.sammy.fitting.options.FitOptions
runs:
  - run_id: run_001
    routine_id: example_fit
    dataset_id: example_dataset
    created_at: "2026-01-14T12:00:00Z"
    fit_dir: ${workspace.fitting_dir}/example_fit
    results_dir: ${workspace.fitting_dir}/example_fit/results_dir
    input_files:
      inp: ${workspace.fitting_dir}/example_fit/input.inp
      par: ${workspace.fitting_dir}/example_fit/params.par
      data: ${workspace.data_dir}/example_fit.dat
    output_files:
      lpt: ${workspace.fitting_dir}/example_fit/results_dir/SAMMY.LPT
      lst: ${workspace.fitting_dir}/example_fit/results_dir/SAMMY.LST
      sammy_par: ${workspace.fitting_dir}/example_fit/results_dir/SAMMY.PAR
    sammy_execution:
      backend: local
      success: false
      console_output: ${workspace.fitting_dir}/example_fit/results_dir/sammy_console.txt
    results:
      run_results_path: ${workspace.results_dir}/run_results_001.json
      summary:
        chi_squared: null
        dof: null
        reduced_chi_squared: null

results_index:
  per_fit: []
  aggregate: ${workspace.results_dir}/results_map.json

How this config is used
-----------------------
1) Load config.yaml into PleiadesConfig (workspace + nuclear + sammy + datasets + routines).
2) Resolve dataset inputs:
   - raw_imaging: run normalization to produce transmission data, then export
     to data_dir/<routine_id>.dat (or .twenty).
   - sammy_dat/sammy_twenty: use path_to_data_files or input_files.data directly.
3) Cache isotope data with NuclearDataManager:
   - Use nuclear.isotopes for FitConfig population.
   - If isotopic data is not already cached, download using nuclear.data_cache_dir
     (default: ~/.pleiades/nuclear_data) and default_library.
4) Create a run record:
   - Append a new entry to runs with run_id, routine_id, dataset_id, and paths.
   - Capture runtime metadata (timestamps, user, host, software versions).
5) Build SAMMY inputs:
   - Construct FitConfig from fit_routines.<routine_id>.fit_config.
   - Write input.inp and params.par via InpManager and ParManager into the fit_dir.
6) Execute SAMMY:
   - Instantiate SammyRunner via SammyFactory using sammy.backend.
   - Run SAMMY with SammyFiles; collect output files in results_dir.
7) Parse outputs:
   - LptManager and LstManager create RunResults.
   - Serialize RunResults to JSON and store the path in runs[].results.
8) Record provenance and reproducibility:
   - Persist config snapshot, SAMMY outputs, and run metadata together.
   - Store git commit, environment, and dependency versions for re-running.
9) Optional iteration:
   - If update_from_results is true, update FitConfig for the next run.

ENDF integration
----------------
- NuclearDataManager uses PleiadesConfig.nuclear_data_cache_dir as its cache root.
- If nuclear.data_cache_dir is omitted, it defaults to ~/.pleiades/nuclear_data.
- When provided, nuclear.data_cache_dir overrides the default and can be placed
  under workspace.endf_dir or any other location.
