# ADR-001: MCP Integration Pattern for PLEIADES

**Status**: Accepted (for PLEIADES v2.2.0)
**Date**: 2025-12-09
**Authors**: PLEIADES Development Team
**Related Issues**: #163 (Epic), #171 (Research)

## Context

### The Problem

Scientific software faces a persistent challenge: **code rots, but physics doesn't**. Dependencies decay, platforms change, and significant engineering effort goes into maintenance that doesn't advance science. Meanwhile, the underlying physics—the equations, the data reduction algorithms, the validation criteria—remains constant.

PLEIADES needed to integrate AI capabilities (via MCP - Model Context Protocol) while:

1. Avoiding tight coupling that would create future maintenance burden
2. Keeping the core library functional without AI dependencies
3. Enabling future adaptation as MCP ecosystem evolves
4. Aligning with a longer-term vision where physics descriptions, not code, become the primary artifact

### The Broader Vision

This integration is part of a larger initiative (Scientific Model Context Protocol - sMCP) that treats physics knowledge as "source code" that AI can "compile" into executable implementations:

```
Assembly era:  Hardware-specific code → New hardware = rewrite everything
Compiler era:  High-level source → Compiler → Machine code (source unchanged)
sMCP era:      Physics description → AI → Generated code (physics unchanged)
```

Just as we don't version control `.o` files or compiler assembly output, the vision is that we shouldn't need to version control Python scripts generated from physics descriptions.

## Decisions

### Decision 1: Optional Package (not Separate Package)

**Choice**: MCP is an optional dependency within PLEIADES (`pip install pleiades-neutron[mcp]`), not a separate package.

**Alternatives Considered**:
- Separate package (`pleiades-mcp`) that depends on PLEIADES core
- MCP as a required dependency

**Rationale**:
- **Prevents drift**: Changes to core PLEIADES APIs are immediately reflected in MCP tools. A separate package would gradually diverge as the two evolve independently.
- **Single source of truth**: One repository, one test suite, one release cycle.
- **Simpler dependency graph**: Users install one package with optional extras, not multiple packages with version compatibility concerns.

**Implementation**:
```toml
# pyproject.toml
[project.optional-dependencies]
mcp = ["fastmcp>=2.12.0,<3"]
```

### Decision 2: FastMCP 2.x (not MCP 1.0)

**Choice**: Use FastMCP 2.x as the MCP server implementation.

**Alternatives Considered**:
- Official `mcp` package (1.0)
- Building directly on MCP protocol primitives

**Rationale**:
- **Future direction**: FastMCP represents where the MCP ecosystem is heading. The official MCP package adopted FastMCP v1.0 patterns, validating this direction.
- **No catch-up game**: Using state-of-the-art now avoids migration costs later.
- **Pydantic 2.x compatibility**: FastMCP 2.12+ resolved compatibility issues with modern Pydantic.
- **Developer experience**: Cleaner API, better error messages, less boilerplate.

**Implementation**:
```toml
# Pin to 2.x series - version 3.x may have breaking API changes
mcp = ["fastmcp>=2.12.0,<3"]
```

### Decision 3: Thin Wrapper (not Direct FastMCP Usage)

**Choice**: Create a custom `@mcp_tool` decorator that wraps FastMCP, rather than using FastMCP's built-in `@server.tool()` directly.

**Alternatives Considered**:
- Direct use of `@server.tool()` decorator
- Code generation approach

**Rationale**:
- **Decoupling**: PLEIADES is fundamentally a library for SAMMY-based resonance analysis. MCP is a nice-to-have feature, not core functionality. A thin wrapper allows switching frameworks if needed—for example, when the official `mcp` package adopted FastMCP patterns, we avoided migration pain by already abstracting the dependency.
- **Testability**: Tools can be tested without running an MCP server by calling the decorated functions directly.
- **Registry pattern**: Enables auto-discovery and runtime introspection of available tools without importing FastMCP.
- **Future flexibility**: If FastMCP 3.x introduces breaking changes or a better implementation emerges, only `server.py` (~50 lines) needs updating—all tool definitions remain unchanged.

**Implementation** (actual pattern from `decorators.py`):
```python
# pleiades/mcp/decorators.py - registry-based decorator
_mcp_registry: dict[str, dict[str, Any]] = {}

def mcp_tool(func=None, *, name=None, description=None, parameter_descriptions=None):
    """Decorator to register a function as an MCP tool."""
    def decorator(fn):
        tool_name = name or fn.__name__
        _mcp_registry[tool_name] = {"name": tool_name, "func": fn, ...}
        return fn  # Return unchanged - no wrapper overhead
    return decorator

# Usage in tools.py:
@mcp_tool(description="Analyze resonance data")
def analyze_resonance(dataset_path: str) -> dict:
    ...
```

### Decision 4: Physics-Centric Manifest Format

**Choice**: Design manifest format to capture physics knowledge and validation criteria, not just configuration parameters.

**Alternatives Considered**:
- Simple JSON configuration
- Tool-specific config formats
- Generic workflow description

**Rationale**:
- **Longevity**: Physics doesn't change; code does. A manifest that captures the physics (isotope properties, expected resonances, validation criteria) remains valid even as implementation code evolves.
- **AI-compilable**: With sufficient physics description, an AI agent can generate appropriate processing code for any target platform.
- **Self-documenting data**: Datasets carry their own processing instructions, enabling cross-facility portability.
- **Validation-first**: Embedded correctness criteria (expected peak positions, statistical quality metrics) enable automated verification.

**Implementation**:
```yaml
# Manifest captures physics, not just parameters
isotope: Hf-177
material_properties:
  density_g_cm3: 13.31
  atomic_mass_amu: 178.49
  temperature_k: 295.0

# Explicit isotope list for analysis
isotopes:
  - Hf-176
  - Hf-177
  - Hf-178
```

## Consequences

### Benefits

1. **Maintainability**: Core PLEIADES works without MCP; MCP integration is isolated.
2. **Evolvability**: Can upgrade or replace MCP implementation without touching workflows.
3. **Testability**: All components testable in isolation.
4. **Portability**: Manifest format enables cross-tool, cross-facility workflows.
5. **Future-proofing**: Architecture aligns with AI-first scientific computing vision.

### Trade-offs

1. **Additional abstraction**: Thin wrapper adds a layer of indirection (minimal overhead).
2. **Pattern duplication**: Other packages (iBeatles, etc.) must copy the pattern rather than import a shared library.
3. **Learning curve**: Developers must understand the registry pattern, not just FastMCP.

### Security Considerations

MCP tools accept file system paths from AI clients. The current implementation:
- Does **not** restrict path traversal (`../` is permitted)
- Relies on OS-level permissions for access control
- Should run with minimal necessary file system permissions

See `docs/mcp/README.md` for deployment security guidance.

### Why Not a Shared Package?

We considered extracting a `scientific-mcp` shared package (~100 lines) but decided against it:

- **Premature abstraction**: The pattern is still evolving; freezing it in a package would slow iteration.
- **Maintenance burden**: Another package to version, release, and keep compatible.
- **Low value**: The pattern is simple enough to copy; documentation provides sufficient guidance.
- **Dependency coupling**: A shared package locks projects into synchronized releases and version compatibility constraints, reducing each project's ability to evolve independently.

**Recommendation**: Document the pattern thoroughly (this ADR + `integration-pattern.md`) and let projects copy/adapt as needed. Revisit shared package decision when pattern stabilizes across 3+ implementations.

## Vision Alignment

This architecture supports the broader sMCP vision:

```
┌─────────────────────────────────────────────────────────────┐
│ Layer 1: Physics Compiler (Future)                          │
│   full_smcp_manifest (physics knowledge)                    │
│       ↓                                                     │
│   Generated Code                                            │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Layer 2: Pipeline Linker (Current: manifest_intermediate)   │
│   manifest_intermediate (tool usage instructions)           │
│       ↓                                                     │
│   Orchestrated Workflow                                     │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Layer 3: Execution Runtime (Current: PLEIADES MCP)          │
│   MCP Server executes tools                                 │
│       ↓                                                     │
│   Validated Results                                         │
└─────────────────────────────────────────────────────────────┘
```

PLEIADES MCP currently operates at **Layer 3** (execution runtime), with manifest format designed to support **Layer 2** (pipeline orchestration). The physics-centric manifest design anticipates **Layer 1** (AI-generated code from physics descriptions).

## References

- [MCP Protocol Specification](https://modelcontextprotocol.io/)
- [FastMCP Documentation](https://gofastmcp.com/)
- [PLEIADES MCP Integration Pattern](./integration-pattern.md)
- [PLEIADES Manifest Format](./manifest-format.md)
- sMCP Architecture Vision (internal documentation, not public)

## Revision History

| Date | Change |
|------|--------|
| 2025-12-09 | Initial version documenting decisions from MCP integration sprint |
