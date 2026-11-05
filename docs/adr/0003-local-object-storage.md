# ADR-0003: Local S3-Compatible Object Storage

Status: Accepted
Date: 2026-11-04

## Context

The MVP needs local S3-compatible storage for datasets, adapters, artifacts, and logs. The original
stack proposed MinIO. In 2026 the MinIO open-source repository was archived, and the
`minio/minio` and `minio/mc` Docker Hub images were removed. A fresh clone can no longer pull the
images named in the original plan. MinIO is therefore not a viable default for a new contributor.

## Decision

Use **RustFS 1.0.4** for local development.

- Apache-2.0, actively maintained, S3-compatible.
- Single-node, single-disk mode is sufficient for local development.
- The S3 API stays on port 9000; the console is on 9001.
- Buckets are created by `rustfs/rc` in an init service.
- Production remains Cloudflare R2, which is S3-compatible.

## Consequences

- Local and production use the same S3 API, so application code does not branch on the provider.
- The local compose stack includes a one-shot bucket initializer.
- RustFS is newer than MinIO and has a smaller operational track record. It is used only for local
  development, not as the production system of record.
- MinIO-specific `mc` commands and documentation must not be added.
- If RustFS becomes unsuitable, the replacement must remain S3-compatible and be recorded in a new
  ADR.

## Rejected alternatives

### Keep MinIO

- The community images are no longer available from Docker Hub.
- The upstream open-source project is archived and no longer receives security patches.
- Keeping it would break fresh-clone onboarding and create an unsupported dependency.

### LocalStack S3

- Heavy for a small local dependency.
- The free tier is not a production substitute.
- More moving parts than a single S3 server.

### Garage / SeaweedFS

- Both are viable S3-compatible options.
- RustFS has a simpler single-container local setup and a recent 1.0 release.
- Revisit if RustFS operational issues appear.

### Filesystem-only storage

- Would require a second storage abstraction in application code.
- Does not exercise presigned URLs or S3 semantics used in production.
