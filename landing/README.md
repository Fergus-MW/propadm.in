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
| `SIGNUPS_BUCKET` | unset | Private GCS bucket for durable hosted signups; takes precedence over CSV |

Cloud Run uses `SIGNUPS_BUCKET` and its service identity to save one JSON object
per email. SHA-256 object names keep emails out of URLs; a create-only generation
precondition deduplicates across concurrent instances and restarts. Local startup
continues to use CSV without cloud credentials. No credentials are embedded in
the page or container.

## Host on Cloud Run

Build the landing image from the repository root:

```sh
gcloud builds submit --project=PROJECT --config=cloudbuild/landing.yaml --substitutions=_TAG=COMMIT .
```

Set `landing_image` in the ignored `infra/main/terraform.tfvars` to
`europe-west1-docker.pkg.dev/PROJECT/propadmin/landing:COMMIT`, then run a
Terraform plan and apply. `infra/main/landing.tf` provisions the landing service,
its dedicated service account and private signup bucket. Only the page is public;
signup records are private. The `landing_url` output gives the hosted address.

The header and footer link to the deployed admin panel. The footer also provides
the link on mobile, where the existing design hides secondary header actions.

## Layout

- `public/` holds the page (`index.html`, `styles.css`, `main.js`), logo and team photos.
- `server.mjs` serves `public/`, `GET /healthz` and `POST /api/signup`.
- The page is a marketing surface with its own look, so it does not use the
  admin design system described in `design.md`.
