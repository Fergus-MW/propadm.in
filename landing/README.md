# Landing page

The public Properly landing page plus a small signup endpoint. It has no
dependencies and needs only Node 20.9+.

```sh
node landing/server.mjs        # http://127.0.0.1:3001
node --test landing/test/server.test.mjs
```

`make dev` also starts it on port 3001 (`LANDING_PORT` overrides).

## Signups

The form posts to `POST /api/signup`. Valid emails are lower-cased, de-duplicated
and appended to `landing/.data/signups.csv` (`created_at,email`), which is
gitignored. Open it in any spreadsheet app.

| Variable | Default | Purpose |
| --- | --- | --- |
| `PORT` | `3001` | Port to listen on |
| `HOST` | `127.0.0.1` | Use `0.0.0.0` inside a container |
| `SIGNUPS_PATH` | `landing/.data/signups.csv` | Where signups are saved |

When hosting, put `SIGNUPS_PATH` on a persistent disk. Serverless and static
hosts (Vercel, Cloud Run without a mounted volume) discard local files.

## Layout

- `public/` holds the page (`index.html`, `styles.css`, `main.js`), logo and team photos.
- `server.mjs` serves `public/`, `GET /healthz` and `POST /api/signup`.
- The page is a marketing surface with its own look, so it does not use the
  admin design system described in `design.md`.
