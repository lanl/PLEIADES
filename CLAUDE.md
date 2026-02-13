# PLEIADES Claude Code Guidelines

## MCP Integration Development Workflow

**IMPORTANT**: This workflow MUST be followed for all MCP-related development (Issue #163 epic and sub-issues). Do not skip stages or take shortcuts.

### Workflow Overview

```
┌─────────────────────────────────────────────────────────────────┐
│  Stage 1: Research                                              │
│  (Launch research agents for codebase + web)                    │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│  Stage 2: TDD                                                   │
│  (Test-writing agent → Implement to pass tests)                 │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│  Stage 3: Review                                                │
│  (Brutal review agent - must approve to proceed)                │
└─────────────────────┬───────────────────────────────────────────┘
                      │
            ┌─────────┴─────────┐
            │                   │
            ▼                   ▼
     ┌──────────┐        ┌──────────┐
     │ APPROVED │        │ REJECTED │
     └────┬─────┘        └────┬─────┘
          │                   │
          │                   │ ◄── ITERATE: Go back to Stage 2
          │                   │     Fix issues, re-run review
          │                   │     Repeat until APPROVED
          ▼                   │
┌─────────────────────────────┴───────────────────────────────────┐
│  Stage 4: Ready                                                 │
│  (Ruff, pre-commit - only after review approval)                │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│  Stage 5: Notify User                                           │
│  (PR decision - do NOT claim victory prematurely)               │
└─────────────────────────────────────────────────────────────────┘
```

### Branch Strategy

**CRITICAL: Read this before creating any PR.**

```
Repository Default Branch: next (NOT main)

Epic Development Flow:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
next (default branch)
  │
  └── feature/163-mcp-integration (epic base branch)
        │
        ├── feature/165-mcp-tool-decorator (sub-issue) ──► PR to base
        ├── feature/166-mcp-server-module (sub-issue)  ──► PR to base
        └── feature/167-xxx (sub-issue)                ──► PR to base
                                                              │
                                    Once ALL sub-issues done ─┘
                                              │
                                              ▼
                            Formal PR: base branch ──► next
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Rules:**
1. Epic base branch: `feature/163-mcp-integration`
2. Feature branches for sub-issues branch OFF the epic base branch
3. PRs for sub-issues target the epic base branch: `--base feature/163-mcp-integration`
4. **NEVER** use `--base main` or `--base next` for sub-issue PRs
5. Only when ALL MCP sub-issues are closed (epic complete), create formal PR from base → `next`
6. The epic issue (#163) stays open until the formal PR to `next` is merged

**Common Mistake:** Using `--base main` when creating PR. Always verify the base branch before `gh pr create`.

### Stage 1: Research (MANDATORY)
Before writing ANY code:
1. Launch an **independent research agent** to explore:
   - Existing PLEIADES codebase patterns (how similar features are implemented)
   - Current library APIs via web search (FastMCP, mcp, pydantic, etc.)
2. **Why**: Claude's knowledge cutoff is early 2024. We are in late 2025. APIs change. Do NOT rely on internal knowledge for library usage - verify everything.
3. Research agent should return:
   - Relevant existing code patterns to follow
   - Current API signatures with examples
   - Potential pitfalls or breaking changes

### Stage 2: TDD Development Cycle (MANDATORY)
1. **Hand off to TEST-WRITING AGENT** (separate from implementation):
   - Provide research results and requirements
   - Agent writes comprehensive unit tests FIRST
   - Tests should cover: happy path, edge cases, error conditions
   - Claude (implementer) has NO influence on test design

2. **Implement to pass tests**:
   - Write minimal code to pass each test
   - Do not modify tests to pass implementation
   - If tests seem wrong, discuss with user - don't change them unilaterally

3. **Iterate** until all tests pass

**Why separation matters**: Prevents "cheating" where tests are designed to pass existing buggy code. Independent test agent enforces real TDD.

### Stage 3: Review (MANDATORY)
1. Launch **brutal review agent** (honest, to-your-face style)
2. Review agent checks:
   - Logic errors and bugs
   - API misuse
   - Missing error handling
   - Type safety issues
   - Code quality
   - Unused variables, misleading comments, dead code
   - Linter issues the agent should have caught
3. **Review outcomes**:
   - **APPROVED**: Proceed to Stage 4
   - **REJECTED**: Go back to Stage 2, fix ALL issues, re-run review

### ⚠️ CRITICAL: Stage 2 ↔ Stage 3 Iteration Loop

**You MUST iterate between Stage 2 and Stage 3 until the review agent gives APPROVED.**

- Do NOT proceed to Stage 4 until review passes
- Do NOT skip re-running review after fixes
- Each iteration requires a FULL review, not partial
- Track iteration count (e.g., "Iteration 3: Review gave B+, fixing 5 issues")
- Provide summary to user after each iteration

Example iteration history:
```
Iteration 1: D- grade (21 issues) → Fix all
Iteration 2: C+ grade (8 issues) → Fix all
Iteration 3: B+ grade (3 issues) → Fix all
Iteration 4: A grade → APPROVED ✓
```

### Stage 4: Ready (MANDATORY)
**Only enter this stage after Stage 3 review is APPROVED.**

1. Run `pixi run ruff check` on changed files
2. Run `pixi run ruff format` on changed files
3. Run pre-commit hooks: `git add . && git commit` (let hooks run)
4. Verify all checks pass

### Stage 5: Notify User
Only after ALL stages pass:
- Inform user that code is ready for review
- User decides whether to create PR
- Do NOT claim victory prematurely

### Anti-Patterns to Avoid
- Writing implementation before tests (violates TDD)
- Writing tests after implementation (fake TDD)
- Skipping research and hallucinating APIs
- Superficial fixes that don't address root cause
- Claiming "done" when review agent finds issues
- Modifying tests to make buggy code pass
- **Skipping review re-run after fixes** (critical!)
- **Proceeding to Stage 4 without review approval** (critical!)

## Build & Test Commands
- Run all tests: `pixi run test`
- Run single test: `pixi run pytest tests/unit/path/to/test_file.py::test_function_name -v`
- Run linter: `pixi run ruff check .`
- Format code: `pixi run ruff format .`

## Code Style Guidelines
- Line length: 140 characters max
- Use type hints and validate with pydantic
- Classes use CamelCase; functions/variables use snake_case
- Use docstrings for modules, classes, functions
- Error handling: Prefer explicit exception handling with specific exception types
- Python 3.10+ required
