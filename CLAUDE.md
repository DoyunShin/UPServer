# UPServer Project Notes

## Release Checklist

When bumping the backend version (e.g. `1.1.1` → `1.1.2`):

1. **Edit `backend/pyproject.toml`** — set `version = "X.Y.Z"`.
2. **Sync `backend/uv.lock`** — run `uv lock` inside `backend/`. This rewrites the `ory-upserver` entry to the new version. Do not hand-edit `uv.lock`.
3. **Sanity test** — `cd backend && uv run pytest -q`. Must be green before tagging.
4. **Commit** — one commit, subject only, Conventional Commits style:
   - `chore(release): X.Y.Z`
   - Stage: `backend/pyproject.toml` and `backend/uv.lock` only.
5. **Tag** — `git tag vX.Y.Z` (note the `v` prefix; CI matches `v*.*.*`). Do not sign or annotate unless asked.
6. **Push (requires explicit user approval)** — push the commit and the tag together:
   - `git push origin master --follow-tags`

CI side effects (no manual action needed once the tag is pushed):

- `.github/workflows/cd.yaml` — verifies the tag matches `backend/pyproject.toml`, builds the wheel, publishes to PyPI.
- `.github/workflows/ghcr.yaml` — waits for the PyPI release to propagate, then builds and publishes the Docker image to GHCR. Stable tags also receive `latest`.

Constraints:

- **Tag and pyproject version must match** — `cd.yaml` fails the release otherwise.
- **Frontend version (`frontend/package.json`) is not bumped** for backend releases. Leave it untouched.
- **Never push tags or commits without explicit user confirmation** — the release pipeline publishes to PyPI and GHCR, which is irreversible.
