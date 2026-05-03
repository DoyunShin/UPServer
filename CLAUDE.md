# UPServer Project Notes

## Release Checklist

Backend and frontend versions are kept in lockstep. When bumping (e.g. `1.1.1` → `1.1.2`):

1. **Edit `backend/pyproject.toml`** — set `version = "X.Y.Z"`.
2. **Edit `frontend/package.json`** — set `"version": "X.Y.Z"` to match the backend exactly.
3. **Sync `backend/uv.lock`** — run `uv lock` inside `backend/`. Rewrites the `ory-upserver` entry. Do not hand-edit `uv.lock`.
4. **Sync `frontend/package-lock.json`** — run `npm install --package-lock-only` inside `frontend/`. Rewrites the root `version` fields without touching `node_modules`.
5. **Sanity test** — `cd backend && uv run pytest -q`. Must be green before tagging.
6. **Commit** — one commit, subject only, Conventional Commits style:
   - `chore(release): X.Y.Z`
   - Stage: `backend/pyproject.toml`, `backend/uv.lock`, `frontend/package.json`, `frontend/package-lock.json`.
7. **Tag** — `git tag vX.Y.Z` (note the `v` prefix; CI matches `v*.*.*`). Do not sign or annotate unless asked.
8. **Push (requires explicit user approval)** — push the commit and the tag together:
   - `git push origin master --follow-tags`

CI side effects (no manual action needed once the tag is pushed):

- `.github/workflows/cd.yaml` — verifies the tag matches `backend/pyproject.toml`, builds the wheel, publishes to PyPI.
- `.github/workflows/ghcr.yaml` — waits for the PyPI release to propagate, then builds and publishes the Docker image to GHCR. Stable tags also receive `latest`.

Constraints:

- **Tag, `backend/pyproject.toml`, and `frontend/package.json` must all carry the same `X.Y.Z`** — `cd.yaml` fails the release if backend pyproject diverges from the tag, and the lockstep rule above keeps the frontend in sync.
- **Never push tags or commits without explicit user confirmation** — the release pipeline publishes to PyPI and GHCR, which is irreversible.
