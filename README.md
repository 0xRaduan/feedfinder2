# Feedfinder2

This package helps locate RSS/Atom feeds for a given website.

Requires Python 3.10 or later.

## Building with uv

This project uses [uv](https://github.com/astral-sh/uv) for dependency
management and building distributions.

Install dependencies with:

```
uv sync
```

Build wheels and source archives with:

```
uv build --sdist --wheel -o dist/
```

Earlier revisions relied on `setup.py` and a `backend-path` entry in
`pyproject.toml`, which caused build errors with Poetry.  Those files
have been removed in favour of the standard `pyproject.toml` approach.
