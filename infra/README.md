# Infrastructure

Phase 1 provides local dependencies in `compose/`. Later phases add:

- `grafana/` — dashboards.
- `prometheus/` — scrape and alert rules.
- `fly/` — API deployment.
- `terraform/` or provider configs — managed Postgres, Redis, and object storage.
- `gpu/` — trusted vLLM host and inference proxy.

Do not commit secrets or provider credentials. Local object storage is RustFS; see
[`docs/adr/0003-local-object-storage.md`](../docs/adr/0003-local-object-storage.md).
