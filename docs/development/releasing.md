# Releasing

A release is a tag. Pushing `vX.Y.Z` runs [`.github/workflows/release.yml`](../../.github/workflows/release.yml):

1. the full test suite against Inkscape on Linux, Windows and macOS (the CI workflow);
2. a check that the tag, `src/inksmcp/__init__.py`, `server.json` and `CHANGELOG.md` agree;
3. `uv build`, then **PyPI** through trusted publishing (no tokens stored in the repo);
4. a **GitHub release** with the built files and that version's changelog section as notes;
5. **MCP Registry**: `server.json` published as `io.github.bhanutpt/inksmcp` (GitHub OIDC login; the
   registry checks the `mcp-name:` comment in the README on PyPI).

## One-time setup (maintainer)

1. **GitHub**: create `bhanutpt/inksmcp` (public) and push `main`. In *Settings → Code security*, turn
   on private vulnerability reporting (SECURITY.md points to it).
2. **PyPI**: on pypi.org, *Your account → Publishing → Add a pending publisher*: project `inksmcp`,
   owner `bhanutpt`, repository `inksmcp`, workflow `release.yml`, environment `pypi`.
3. **GitHub environment**: *Settings → Environments → New environment* `pypi`. Optionally add yourself
   as a required reviewer, so every PyPI upload waits for your click.
4. **MCP Registry**: nothing to register ahead. The `io.github.bhanutpt/` namespace is proven by the
   workflow's GitHub OIDC token.

## Each release

1. **Field test** the release candidate in a fresh agent session: at least one task drawn from scratch
   and one edit of a file made elsewhere (lessons learned, 2026-09-28). File the reports and fix what
   blocks.
2. **Benchmark** (`experiments/e20_benchmark.py`) and add a dated table to `benchmarks.md`, including
   the tool-list size.
3. **Bump**: `uv run python scripts/bump_version.py X.Y.Z`. It sets the version in `__init__.py` and
   `server.json`, moves the *Unreleased* changelog entries into a `## X.Y.Z — date` section, and
   regenerates `docs/tools.md`. Edit the new section's first lines into a short summary.
4. **Check**: `uv run pytest`, and look through the diff.
5. **Commit and tag**:

   ```bash
   git commit -am "Release X.Y.Z"
   git tag vX.Y.Z
   git push origin main vX.Y.Z
   ```

6. **Watch** the Release workflow. Afterwards check that `uvx inksmcp@X.Y.Z` starts, that
   [PyPI](https://pypi.org/project/inksmcp/) shows the README, and that the registry lists the version:
   `curl "https://registry.modelcontextprotocol.io/v0/servers?search=io.github.bhanutpt/inksmcp"`.

## Versions

Semantic versioning, with the 0.x caveat: until 1.0, a minor version may change tool arguments. The
changelog says so under *Changed* whenever it does. Patch versions only fix bugs.

## If something fails

- **Tests fail on one platform**: fix on `main`, delete the tag (`git push --delete origin vX.Y.Z`,
  `git tag -d vX.Y.Z`), tag again.
- **PyPI rejects the upload** (the version exists): PyPI versions can't be reused. Bump the patch version.
- **Registry publish fails** after PyPI succeeded: fix `server.json` on `main`, then publish by hand
  with `mcp-publisher login github` and `mcp-publisher publish`. Or re-run the job if the cause was
  temporary.
