# TODO

## Publish to PyPI

**Target Package Name**: `feedfinder2-async`

### Context

The original `feedfinder2` hasn't been updated since 2022. We've created a modern fork with significant improvements and are waiting for response from the original author:
- Issue: https://github.com/dfm/feedfinder2/issues/14
- PR: https://github.com/dfm/feedfinder2/pull/15

### Tasks

- [ ] Update `pyproject.toml` with package name `feedfinder2-async`
- [ ] Add PyPI metadata (authors, keywords, classifiers, URLs)
- [ ] Build package: `uv build --sdist --wheel`
- [ ] Test installation in clean environment
- [ ] Publish to PyPI: `uv publish`
- [ ] Verify package on PyPI
- [ ] Update README.md installation instructions
- [ ] Update docs/installation.mdx
- [ ] Create GitHub release with changelog

### Timeline

Wait 3-6 months for original author response. If no response, consider:
- Publishing as `feedfinder2-async` (respectful fork), OR
- Taking over `feedfinder2` name (if truly abandoned)

### Current Installation (Git-based)

Users currently install via:

```bash
uv add "feedfinder2 @ git+https://github.com/0xRaduan/feedfinder2.git"
```

### Future Installation (After PyPI)

```bash
uv add feedfinder2-async
```
