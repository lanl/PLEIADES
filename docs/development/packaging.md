# Packaging Guide

## Distribution Channels

- **PyPI**: Built and published from this repository
- **conda-forge**: Managed via feedstock at https://github.com/conda-forge/pleiades-neutron-feedstock

## PyPI Publishing

### Automated (Production)

GitHub Actions automatically publishes to PyPI when tags are pushed to `main`:

```bash
git tag v2.1.3
git push origin v2.1.3
```

Workflow: `.github/workflows/package.yaml`

### Manual (Testing)

```bash
pixi run build-pypi          # Creates wheel and sdist in dist/
pixi run twine upload dist/* # Uploads to PyPI
```

For TestPyPI, add `--repository testpypi` flag.

## Version Numbering

Managed by `versioningit` from git tags:

- Clean version: Requires tagged commit (e.g., `v2.1.3` → `2.1.3`)
- Dev version: Commits after tag (e.g., `v2.1.3-1-gef2c755` → `2.2.0.dev1`)
- Dirty version: Modified tracked files (e.g., `2.1.3+d20251007`)

PyPI rejects dev and dirty versions.

## Conda-Forge Updates

Automated via `regro-cf-autotick-bot`:

1. Publish new version to PyPI
2. Bot detects release, creates PR on feedstock
3. Review and merge bot PR

Manual updates: See https://conda-forge.org/docs/maintainer/updating_pkgs/

## Dependencies

### Optional Dependencies

Defined in `[project.optional-dependencies]`:

```toml
[project.optional-dependencies]
nova = ["nova-galaxy>=0.7.4,<0.8"]
```

Install with: `pip install pleiades-neutron[nova]`

### PyPI/Conda-Forge Alignment

Keep dependencies synchronized. If unavailable on conda-forge, make optional in PyPI.

## Release Checklist

1. Run tests: `pixi run test`
2. Create tag: `git tag vX.Y.Z`
3. Push tag: `git push origin vX.Y.Z`
4. Verify PyPI publication
5. Monitor conda-forge bot PR
