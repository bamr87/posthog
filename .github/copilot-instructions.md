# PostHog AI Agent Development Guide

## Architecture Overview

PostHog is a full-stack product analytics platform with three main architectural layers:

1. **Django Backend** (`posthog/`) - REST APIs, models, business logic, Celery tasks
2. **Frontend** (`frontend/`) - React+TypeScript SPA using Vite, Kea for state management
3. **Plugin Server** (`plugin-server/`) - Node.js event ingestion, data pipeline, plugins (TypeScript)
4. **Data Layer** - ClickHouse (analytics database) + PostgreSQL (metadata) + Kafka (event streaming)

Key subsystems:
- **HogQL** (`posthog/hogql/`) - SQL-like query language that compiles to ClickHouse SQL
- **Query Runners** (`posthog/hogql_queries/`) - Execute queries, cache results, power insights
- **Temporal** (`posthog/temporal/`) - Workflow orchestration for data imports, batch jobs
- **CDP** (`posthog/cdp/`) - Customer data platform, event transformations, destinations

## Environment & Workflow

### Starting Development

```bash
# Auto-detect and use flox environment
./bin/start                    # Full stack with mprocs
./bin/start --minimal          # Minimal services (faster)
```

**Critical**: When flox is available, use `flox activate -- bash -c "<command>"` for terminal commands. Never use `flox activate` interactively (it hangs).

### Testing

```bash
# Python tests
pytest path/to/test.py::TestClass::test_method

# Frontend tests
pnpm --filter=@posthog/frontend test
pnpm --filter=@posthog/frontend jest <test_file>

# Single describe block per jest file
# Use parameterized tests in Python (with `parameterized` library)
```

### Linting & Formatting

```bash
# Python - NEVER run mypy (too slow)
ruff check . --fix && ruff format .

# Frontend
pnpm --filter=@posthog/frontend format
pnpm --filter=@posthog/frontend typescript:check
```

### Build Commands

```bash
pnpm --filter=@posthog/frontend build
./bin/start
```

## ClickHouse Migration Patterns

**Critical rules**:
- **NEVER** use `ON CLUSTER` clause in SQL
- **ALWAYS** use `IF EXISTS`/`IF NOT EXISTS`
- Use `DROP TABLE IF EXISTS ... SYNC` when recreating replicated tables in same migration

### Migration Structure

```python
operations = [
    run_sql_with_exceptions(
        SQL_FUNCTION(),
        node_roles=[NodeRole.DATA, NodeRole.COORDINATOR],  # Choose based on table type
        sharded=False,           # True for sharded tables
        is_alter_on_replicated_table=False  # True for ALTER on replicated tables
    ),
]
```

### Node Roles by Table Type

| Table Type | Node Roles | Notes |
|------------|------------|-------|
| Sharded data tables | `[NodeRole.DATA]` | Data nodes only |
| Non-sharded replicated tables | `[NodeRole.DATA, NodeRole.COORDINATOR]` | All nodes |
| Distributed (read) tables | `[NodeRole.DATA, NodeRole.COORDINATOR]` | Query from anywhere |
| Kafka tables (new) | `[NodeRole.INGESTION_SMALL]` | Ingestion layer |
| Materialized views (new) | `[NodeRole.INGESTION_SMALL]` | Ingestion layer |

### Table Engine Patterns

```python
# Sharded table
engine=AggregatingMergeTree("table_name", replication_scheme=ReplicationScheme.SHARDED)

# Non-sharded replicated
engine=ReplacingMergeTree("table_name", replication_scheme=ReplicationScheme.REPLICATED)

# Distributed - sharded
engine=Distributed(data_table="sharded_events", sharding_key="sipHash64(person_id)")

# Distributed - non-sharded (for ingestion)
engine=Distributed(data_table="my_table", cluster=settings.CLICKHOUSE_SINGLE_SHARD_CLUSTER)
```

### Ingestion Layer Pattern (Preferred)

For new Kafka ingestion:

1. Create data table on main cluster (`DATA` or `DATA+COORDINATOR`)
2. Create writable distributed table on `INGESTION_SMALL`
3. Create Kafka table on `INGESTION_SMALL`
4. Create materialized view on `INGESTION_SMALL`

See migration 0153 and `posthog/clickhouse/migrations/AGENTS.md` for complete examples.

## Code Style & Conventions

### Python
- Type hints required, follow mypy strict rules (but don't run mypy - too slow)
- snake_case naming
- Early returns over deep nesting
- No docstrings in tests
- Comments explain **why**, not **what**
- Use `parameterized` library for test parameters

### TypeScript/Frontend
- Explicit return types required
- camelCase naming
- Use Tailwind utilities over inline styles
- Avoid direct dayjs imports - use `lib/dayjs`
- Import sorting via prettier-plugin-sort-imports (auto on format)
- Prefer absolute imports: `lib/`, `scenes/`, `queries/`, etc.

### Testing Philosophy
- Parameterized tests over multiple assertions
- Think about inputs/outputs to explain code to future developers
- Balance simplicity (fewest parts) vs maintainability (understandability)

### General Rules
- American English spelling
- Product names use Sentence casing: "Product analytics" not "Product Analytics"
- UI text uses Sentence casing: "Save as view" not "Save As View"
- Separate concerns: data/logic/presentation, safety checks/policies
- Start simple, iterate - avoid over-engineering
- One top-level describe block per jest test file

## Monorepo Structure

```
posthog/                 # Python backend (Django)
  hogql/                 # SQL-like query language
  hogql_queries/         # Query runners for insights
  clickhouse/            # CH schema, migrations
  temporal/              # Workflow orchestration
  cdp/                   # Customer data platform

frontend/                # React+TypeScript SPA
  src/
    lib/                 # Shared utilities
    scenes/              # Page components
    queries/             # Query logic
    layout/              # Layout components
  @posthog/lemon-ui/     # UI component library

plugin-server/           # Node.js ingestion & plugins
  src/
    worker/              # Event processing workers
    utils/               # Shared utilities

common/                  # Shared between frontend/backend
  hogvm/typescript/      # HogVM TypeScript runtime
  plugin_transpiler/     # Plugin code transpilation
```

PNPM workspace with Turbo for builds. Use `pnpm --filter=@posthog/frontend <cmd>` to target specific packages.

## Key Integration Points

- **Django ↔ ClickHouse**: Query runners in `posthog/hogql_queries/` execute HogQL
- **Frontend ↔ Backend**: REST API via `frontend/src/lib/api.ts`
- **Kafka → ClickHouse**: Plugin-server consumes events, materializes to CH tables
- **Plugins**: Run in VM sandbox (`plugin-server/src/worker/vm/`), transform events
- **Temporal**: Data imports, batch exports via workflow orchestration

## Documentation References

For detailed ClickHouse migration patterns, see:
- `AGENTS.md` - This file (consolidated agent instructions)
- `posthog/clickhouse/migrations/AGENTS.md` - Comprehensive migration guide
- `posthog/clickhouse/migrations/README.md` - Migration basics
