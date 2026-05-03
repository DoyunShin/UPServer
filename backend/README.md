# ory-upserver

Simple upload server with a FastAPI backend and a bundled SvelteKit frontend.
The wheel ships the prebuilt SPA, so a single `pip install` is enough to run a
working share-link service usable from curl, browsers, or scripts.

Source, design notes, Docker setup, and the full repository live at
<https://github.com/DoyunShin/UPServer>.

## Install

```bash
pip install ory-upserver
```

## Configure

A starter config is bundled at `<site-packages>/oryups/config.example.json`.
Copy it somewhere writable, edit `host.domain`, `local.root`, and (optionally)
`general.*` for branding, then launch:

```bash
ups --config /path/to/config.json
```

`--host` and `--port` override the values from the config.

## HTTP cheat sheet

| Method | Path                              | Purpose                                                |
| ------ | --------------------------------- | ------------------------------------------------------ |
| GET    | `/`                               | SPA upload page                                        |
| GET    | `/api/info`                       | Branding / footer info consumed by the SPA             |
| PUT    | `/{filename}`                     | Upload — response: share URL, `X-Owner-Key` header     |
| GET    | `/{fileid}/{filename}`            | Browser → SPA detail page; curl → direct download      |
| GET    | `/get/{fileid}/{filename}`        | Forced direct download                                 |
| GET    | `/api/v1/{fileid}/{filename}`     | Public metadata (owner key never included)             |
| PATCH  | `/api/v1/{fileid}/{filename}`     | Update `delete_after` (admin only). `-1` = never; `>= 0` = retention seconds |
| DELETE | `/api/v1/{fileid}/{filename}`     | Permanent removal — accepts `X-Owner-Key` (owner) or `Authorization: Bearer <admin-token>` (admin) |

## License

Apache-2.0. See `LICENSE` (bundled with the wheel) for the full text.
