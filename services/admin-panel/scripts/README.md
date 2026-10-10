# Generated API contracts

Run `pnpm --dir services/admin-panel generate:api` from the repository root after
changing HTTP routes or request/response models. This imports the actual FastAPI
app using an in-memory store and local settings, without starting services,
writing runtime data, or requiring cloud credentials. Run `uv sync` first.

`pnpm --dir services/admin-panel generate:api --check` verifies generated files
match the current backend. Generated interfaces are split into cohesive modules
to remain within the 1,000-line file limit.

The typed `apiClient` exported from `lib/api.ts` uses the authenticated same-origin
proxy. Supply `/v1` paths exactly as generated:

```ts
const result = await apiClient.PATCH("/v1/entities/{entity_id}", {
  params: { path: { entity_id: "ticket:123" } },
  body: { version: 2, reason: "Resolved by administrator", fields: { status: "done" } },
});
```

Inspect `result.error` and `result.response.status` for failures. The existing
dynamic `api` helper throws `ApiError` and supports flexible admin views.
Response bodies without FastAPI response models remain `unknown` in the generated
contract; adding models to the backend improves inference on regeneration.

Contracts cover every `/v1/` gateway route, including routes added by later
services. MCP transport and internal worker endpoints are outside the browser API.
