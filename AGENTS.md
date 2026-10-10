# Agent instructions

## Product and architecture

Read [PRD.md](PRD.md) for the product requirements. Agents access the graph
through exactly one MCP server: the API's `/mcp` endpoint. All graph read and
write tools belong to this server; do not introduce per-service MCP servers or
give agents direct database credentials.

## Local development

`make dev` is the required local development entry point. It must start **all
implemented services** together, initialise local dependencies and synthetic
seed data, and print their URLs and local login instructions. Local startup
must work without cloud credentials. Stop every child process cleanly on
Ctrl-C and report startup failures clearly.

Whenever a service is implemented later, add it to `make dev` in the same
change. Do not require developers to start any implemented service separately.

## Design

Read [design.md](design.md) before creating or changing any user interface.
Follow its design rules and use the extracted components, tokens, and reference
materials in `propadmin-design-system/`.

## Tests and pull requests

- Keep the test suite minimal while providing good coverage of meaningful
  behaviour, critical paths, edge cases, and regressions. Prefer focused tests
  over redundant tests or tests that mirror implementation details.
- Run the relevant tests locally and ensure they pass before pushing changes
  for a pull request, including updates to an existing PR.
- Include the local test commands and results in the PR description. If tests
  fail or cannot run, resolve the issue before pushing.

## File size

Files must not exceed 1,000 lines. Split larger files into cohesive modules
before they reach this limit; apply the same limit to test files.

## Current documentation

Use Context7 MCP to fetch current documentation whenever working on a library,
framework, SDK, API, CLI tool, or cloud service. This includes API syntax,
configuration, version migration, library-specific debugging, setup instructions,
and CLI usage. Prefer Context7 over web search for library documentation.

Do not use it for refactoring, writing scripts from scratch, debugging business
logic, code review, or general programming concepts unless library-specific
documentation is needed.

1. Start with `resolve-library-id` using the library name and the full question,
   unless an exact `/org/project` library ID has already been provided.
2. Select the best match by exact name, relevance, snippet count, source
   reputation, and benchmark score. Try alternate names or queries if needed;
   use version-specific IDs when a version is specified.
3. Call `query-docs` with the selected ID and the full question, scoped to one
   concept. Query separate concepts separately unless their interaction is the
   subject of the question.
4. Base the implementation or answer on the fetched documentation.
