# Manifest Format Specification

PLEIADES uses manifest files to describe neutron resonance datasets. Manifests contain metadata about the sample, experiment conditions, and analysis parameters.

## File Format

Manifests use YAML frontmatter followed by an optional Markdown body:

```markdown
---
name: sample-identifier
description: Human-readable description
version: "1.0.0"
# ... other fields
---

# Optional Markdown Content

Analysis notes, processing instructions, or other documentation.
```

## File Naming

PLEIADES searches for manifest files in this order:

1. `manifest_intermediate.md`
2. `smcp_manifest.md`
3. `manifest.md`

Place the manifest file in your dataset root directory.

## Field Reference

### Required Fields

These fields have defaults if not specified:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | string | `"unknown"` | Unique dataset identifier |
| `description` | string | `""` | Human-readable description |
| `version` | string | `"1.0.0"` | Manifest version (semver) |
| `created` | string | `""` | ISO-8601 timestamp (e.g., `2024-06-15T10:30:45Z`) |

### Experiment Metadata (Optional)

| Field | Type | Description |
|-------|------|-------------|
| `facility` | string | Facility name (e.g., `"SNS"`, `"LANSCE"`) |
| `beamline` | string | Beamline identifier (e.g., `"VENUS"`) |
| `detector` | string | Detector type (e.g., `"MCP"`) |
| `sample_id` | string | Sample reference number |

### Primary Isotope

| Field | Type | Description |
|-------|------|-------------|
| `isotope` | string | Primary isotope for analysis |

**Accepted formats:**
- Full specification: `"Au-197"`, `"Hf-177"`, `"U-235"`
- Element only: `"Hf"` (uses natural abundance)
- Natural indicator: `"Hf-nat"` (equivalent to element only)

### Material Properties (Optional)

Nested object describing physical properties:

```yaml
material_properties:
  density_g_cm3: 19.32      # Required if section present, must be > 0
  atomic_mass_amu: 196.97   # Required if section present, must be > 0
  temperature_k: 293.6      # Optional, must be > 0 if provided
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `density_g_cm3` | float | Yes* | Material density in g/cm³ |
| `atomic_mass_amu` | float | Yes* | Atomic mass in amu |
| `temperature_k` | float | No | Sample temperature in Kelvin |

*Required if `material_properties` section is present.

### Isotope Composition

PLEIADES supports three ways to specify which isotopes to analyze:

#### Option 1: Explicit Isotope List (Highest Priority)

```yaml
isotope: Hf-177
isotopes:
  - Hf-176
  - Hf-177
  - Hf-178
```

When `isotopes` is set, only these isotopes are included regardless of natural abundance. Each isotope receives equal weight in the analysis.

**Validation rules:**
- Each entry must match format: `Element-MassNumber` (e.g., `"Hf-177"`)
- Element symbol: 1-2 characters, first uppercase
- Mass number: numeric only (metastable states like `"U-235m"` are not supported)

> **Important**: Each isotope you specify must have ENDF parameter data available. If an isotope lacks ENDF data, the analysis will fail with "ENDF parameter file not found for isotope: X".

**Validation failure behavior**: If isotope format is invalid, a `ValueError` is raised during manifest parsing (e.g., "Invalid isotope format: '177Hf'. Expected format: 'Element-MassNumber' (e.g., 'Hf-177')").

#### Option 2: Custom Enrichment

```yaml
isotope: U-235
use_natural_abundance: false
enrichment:
  U-235: 0.90
  U-238: 0.10
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `use_natural_abundance` | boolean | `true` | Whether to use natural abundances |
| `enrichment` | dict | `null` | Custom isotope composition |

**Enrichment validation rules:**
- All values must be in range [0, 1]
- Values must sum to ~1.0 (within 1% tolerance)
- Keys must be explicit isotopes (e.g., `"U-235"`, not `"U"`)

**Validation failure behavior**: If enrichment validation fails, a `ValueError` is raised during manifest parsing with a descriptive message (e.g., "Enrichment values must sum to approximately 1.0").

#### Option 3: Natural Abundance (Default)

```yaml
isotope: Au-197
use_natural_abundance: true  # This is the default
```

Uses isotope data from PLEIADES internal database to determine natural abundances.

### Priority Order

When determining isotope composition, PLEIADES uses this priority:

1. **User-specified isotopes parameter** (in `analyze_resonance` call)
2. **Manifest `isotopes` field** (explicit list)
3. **Manifest `enrichment` field** (when `use_natural_abundance: false`)
4. **Natural abundance lookup** (default behavior)

## Complete Example

```yaml
---
name: Hf_foil_sample_001
description: >
  Natural hafnium foil resonance measurement from VENUS beamline.
  Sample thickness: 0.5mm, measured at room temperature.
version: "2.0.0"
created: "2024-11-15T14:30:00Z"

# Experiment metadata
facility: SNS
beamline: VENUS
detector: MCP
sample_id: IPTS-35945-HF001

# Analysis parameters
isotope: Hf-177

# Material properties
material_properties:
  density_g_cm3: 13.31
  atomic_mass_amu: 178.49
  temperature_k: 295.0

# Isotope composition - analyze specific isotopes only
isotopes:
  - Hf-176
  - Hf-177
  - Hf-178
  - Hf-179
  - Hf-180
---

# Analysis Notes

## Sample Preparation

Foil was cleaned with ethanol and mounted in standard sample holder.

## Expected Results

Primary resonances expected at:
- Hf-177: 1.1 eV, 2.4 eV, 5.9 eV
- Hf-178: 7.8 eV

## Post-Processing

Results will be compared with ENDF/B-VIII.0 library values.
```

## Minimal Example

For quick testing, a minimal manifest:

```yaml
---
name: quick-test
isotope: Au-197
---
```

## Synthetic Data Example

For documentation and testing without real experimental data:

```yaml
---
name: synthetic-gold-sample
description: Synthetic Au-197 data for testing and documentation
version: "1.0.0"
created: "2024-01-01T00:00:00Z"

facility: Simulated
beamline: Virtual
isotope: Au-197

material_properties:
  density_g_cm3: 19.32
  atomic_mass_amu: 196.97
  temperature_k: 300.0

use_natural_abundance: true
---

# Synthetic Dataset

This manifest describes synthetic/simulated data for testing purposes.
Not derived from actual experimental measurements.
```

## Parsing Notes

- YAML datetime values are automatically converted to ISO format strings
- Empty `material_properties` sections return `null`
- Invalid material properties are logged but don't fail parsing
- All raw YAML data is preserved in `raw_frontmatter` for extensibility
- Markdown horizontal rules (`---`) in the body are handled correctly
