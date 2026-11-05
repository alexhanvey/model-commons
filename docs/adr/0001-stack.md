# ADR-0001: MVP Stack

Status: Proposed; local object storage superseded by ADR-0003
Date: 2026-11-03

## Context

We need a small, buildable MVP for a community-owned small-model lab and inference co-op. The stack must support:

- contributor workers
- job scheduling
- double-entry points
- training and evaluation jobs
- an OpenAI-compatible inference API
- a contributor/admin dashboard
- local development and low-cost production deployment

## Decision

Use:

- Python 3.12 + `uv`
- FastAPI + Pydantic v2
- SQLAlchemy 2 + Alembic
- Postgres 16
- Redis 7 + ARQ
- S3-compatible storage (RustFS locally, Cloudflare R2 in production; see ADR-0003)
- Next.js 15 + TypeScript + Tailwind + shadcn/ui
- vLLM for inference
- PyTorch + Transformers + PEFT + TRL + bitsandbytes for training
- `lm-evaluation-harness` plus custom tool-use evals
- Docker Compose locally
- Fly.io for API, Vercel for web, Neon for Postgres, Upstash for Redis, R2 for artifacts
- GitHub OAuth and hashed API keys
- OpenTelemetry, Prometheus/Grafana, Sentry

## Why

- Python is the shortest path for ML and GPU tooling.
- FastAPI gives typed schemas and OpenAPI.
- Postgres handles relational state and the ledger.
- Redis handles rate limits and queues.
- vLLM is the strongest open serving option for small models.
- Next.js gives a fast dashboard with server components.
- Managed services reduce MVP operations.

## Consequences

- Two languages to maintain.
- GPU host is separate from the control plane.
- No Kubernetes in the MVP.
- No custom inference engine.
- No blockchain.
- No payments in the MVP.

## Rejected alternatives

- Django: heavier for an API-first MVP.
- Go API: better performance, slower ML integration.
- Kubernetes: too much operational overhead.
- Custom inference server: unnecessary.
- Token/blockchain: regulatory and product complexity.
