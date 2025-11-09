---
title: "PostHog Docker Deployment"
description: "Docker Compose setup for running PostHog locally with environment variable configuration"
permalink: /posthog/devcontainer/readme/
lastmod: 2025-11-02T00:00:00.000Z
author: "PostHog Development Team"
tags: [docker, posthog, analytics, deployment]
categories: [Development, Infrastructure]
version: "1.0.0"
---

# PostHog Docker Deployment

This is a Docker Compose setup for running PostHog locally with environment variable configuration.

## Overview

PostHog is an open-source product analytics platform. This setup includes:

{: .table .table-bordered .table-striped .table-hover}
| Component | Purpose | Port |
|-----------|---------|------|
| PostgreSQL | Metadata database | 5432 |
| Redis | Caching layer | 6379 |
| ClickHouse | Analytics database | 8123 |
| Kafka | Event streaming | 9092 |
| Zookeeper | Kafka coordination | 2181 |
| PostHog Web | Web interface | 8080 |
| PostHog Worker | Background jobs | - |
| Plugins Server | Plugin execution | - |

## 📋 Environment Configuration

All configuration has been abstracted into environment variables for easier management and deployment across different environments.

### Files

{: .table .table-bordered .table-striped .table-hover}
| File | Purpose | Version Control |
|------|---------|-----------------|
| `.env` | Active environment variables | ❌ DO NOT commit |
| `.env.example` | Template with defaults | ✅ Safe to commit |
| `docker-compose.yml` | Service configuration | ✅ Safe to commit |
| `.gitignore` | Ignore patterns | ✅ Safe to commit |

### Environment Variables

The following categories of variables are configured (32 total):

#### 1. Database (4 variables)
- `POSTGRES_USER` - PostgreSQL username
- `POSTGRES_DB` - PostgreSQL database name
- `POSTGRES_PASSWORD` - PostgreSQL password
- `DATABASE_URL` - Full PostgreSQL connection string

#### 2. ClickHouse (6 variables)
- `CLICKHOUSE_HOST` - ClickHouse server hostname
- `CLICKHOUSE_DATABASE` - ClickHouse database name
- `CLICKHOUSE_USER` - ClickHouse username
- `CLICKHOUSE_PASSWORD` - ClickHouse password
- `CLICKHOUSE_SECURE` - Use TLS connection (true/false)
- `CLICKHOUSE_VERIFY` - Verify TLS certificates (true/false)

#### 3. Redis (2 variables)
- `REDIS_URL` - Redis connection URL
- `REDIS_MAX_MEMORY` - Maximum memory allocation for Redis

#### 4. Kafka & Zookeeper (9 variables)
- `KAFKA_BROKER_ID` - Kafka broker ID
- `KAFKA_ZOOKEEPER_CONNECT` - Zookeeper connection string
- `KAFKA_ADVERTISED_LISTENERS` - Kafka advertised listeners
- `KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR` - Replication factor
- `KAFKA_TRANSACTION_STATE_LOG_MIN_ISR` - Min in-sync replicas
- `KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR` - Replication factor
- `KAFKA_HOSTS` - Kafka hosts for PostHog
- `ZOOKEEPER_CLIENT_PORT` - Zookeeper client port
- `ZOOKEEPER_TICK_TIME` - Zookeeper tick time

#### 5. PostHog Application (7 variables)
- `SECRET_KEY` - Django secret key
- `SITE_URL` - Public URL for PostHog
- `WEB_PORT` - Port to expose web interface (default: 8080)
- `IS_BEHIND_PROXY` - Whether behind a proxy
- `DISABLE_SECURE_SSL_REDIRECT` - Disable SSL redirect
- `TRUST_ALL_PROXIES` - Trust all proxy headers

#### 6. Plugin Server (2 variables)
- `ENCRYPTION_KEYS` - Encryption keys for plugins (⚠️ must be base64url-encoded)
- `ENCRYPTION_SALT_KEYS` - Salt keys for encryption (⚠️ must be base64url-encoded)

> **⚠️ Important:** Encryption keys must use base64url format (uses `-_` instead of `+/` and no padding). See [Key Generation](#key-generation) section below.

## 🚀 Getting Started

### Prerequisites

- Docker and Docker Compose installed
- At least 4GB of available RAM

### Setup

1. **Copy the example environment file:**
   ```bash
   cp .env.example .env
   ```

2. **Customize the `.env` file:**
   Edit `.env` and update values as needed:
   - Change passwords for production use
   - Update `SECRET_KEY` (generate a new one)
   - Update `SITE_URL` if not using localhost
   - Update `WEB_PORT` if port 8080 is in use

3. **Generate secure keys:**
   
   <a name="key-generation"></a>
   ```bash
   # Generate SECRET_KEY (standard base64)
   openssl rand -hex 32
   
   # Generate ENCRYPTION_KEYS (base64url format - CRITICAL!)
   # Standard base64 uses +/= but PostHog plugin server requires base64url with -_ and no padding
   openssl rand -base64 32 | tr '+/' '-_' | tr -d '='
   
   # Generate ENCRYPTION_SALT_KEYS (base64url format)
   openssl rand -base64 32 | tr '+/' '-_' | tr -d '='
   ```
   
   > **Why base64url?** PostHog's plugin server expects base64url encoding which uses `-` and `_` instead of `+` and `/`, with no `=` padding. Using standard base64 will cause plugin server startup failures.

### Running PostHog

1. **Start all services:**
   ```bash
   docker-compose up -d
   ```

2. **Check status:**
   ```bash
   docker-compose ps
   ```

3. **View logs:**
   ```bash
   # All services
   docker-compose logs -f
   
   # Specific service
   docker-compose logs -f web
   ```

4. **Access PostHog:**
   Open your browser to: `http://localhost:8080` (or your configured `SITE_URL`)

### Stopping PostHog

```bash
# Stop services but keep data
docker-compose stop

# Stop and remove containers (keeps data volumes)
docker-compose down

# Stop, remove containers AND delete all data
docker-compose down -v
```

## ✅ Validation

After starting the services, you can verify the deployment:

```bash
# Check HTTP response
curl -I http://localhost:8080

# Expected: HTTP 302 redirect to /preflight
```

### Expected Warnings (Safe to Ignore)

The following warnings are normal in development mode:
- ⚠️ "Skipping async migrations setup. This is unsafe in production!" - Expected in dev
- ⚠️ "pkg_resources is deprecated" - Python library warning
- ⚠️ "GeoLite2 MMDB file not found" - Optional geolocation feature

## 🔍 Configuration Validation

Before deploying, validate your configuration:

```bash
docker-compose config
```

This will show the resolved configuration with all environment variables substituted.

## 🔧 Troubleshooting

### Services not starting

Check logs for specific service:
```bash
docker-compose logs [service-name]
```

Service names: `db`, `redis`, `clickhouse`, `kafka`, `zookeeper`, `worker`, `web`, `plugins`

### Connection issues

1. Ensure all services are running:
   ```bash
   docker-compose ps
   ```

2. Check network connectivity:
   ```bash
   docker network ls
   docker network inspect posthog_default
   ```

### Database migration issues

View web service logs to see migration progress:
```bash
docker-compose logs -f web | grep -i migrate
```

### Port conflicts

If port 8080 is in use, update `WEB_PORT` in `.env`:
```bash
WEB_PORT=8081
```

Then restart:
```bash
docker-compose up -d
```

### Plugin Server Errors

If you see encryption key errors like:
```
Error: Invalid encryption key format
```

**Cause:** Encryption keys are using standard base64 instead of base64url format.

**Solution:** Regenerate keys using the correct format:
```bash
# Generate new base64url keys (no + / = characters)
openssl rand -base64 32 | tr '+/' '-_' | tr -d '='
```

Update `.env` with the new keys and restart:
```bash
docker-compose restart plugins
```

## 💾 Data Persistence

Data is persisted in Docker volumes:
- `posthog_postgres-data` - PostgreSQL data
- `posthog_clickhouse-data` - ClickHouse data
- `posthog_zookeeper-data` - Zookeeper data
- `posthog_zookeeper-logs` - Zookeeper logs

To backup data:
```bash
docker run --rm -v posthog_postgres-data:/data -v $(pwd):/backup alpine tar czf /backup/postgres-backup.tar.gz -C /data .
```

## 🔒 Security Notes

⚠️ **Important for Production:**

1. Change all default passwords in `.env`
2. Generate new `SECRET_KEY` and `ENCRYPTION_KEYS`
3. Never commit `.env` file to version control
4. Use proper SSL/TLS certificates
5. Set `CLICKHOUSE_SECURE=true` and `CLICKHOUSE_VERIFY=true` for production
6. Review and harden ClickHouse configuration
7. Use a proper reverse proxy (nginx, Caddy, Traefik)
8. Ensure encryption keys use base64url format (critical for plugin server)

## 🏭 Development vs Production

This setup is optimized for development. For production:

1. Use managed databases (RDS, Cloud SQL, etc.)
2. Use managed Kafka (MSK, Confluent Cloud, etc.)
3. Enable SSL/TLS for all connections
4. Use proper secret management (AWS Secrets Manager, HashiCorp Vault, etc.)
5. Set up monitoring and alerting
6. Configure proper backups
7. Review PostHog's official production deployment guides

## 📚 Resources

- [PostHog Documentation](https://posthog.com/docs)
- [PostHog GitHub](https://github.com/PostHog/posthog)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Base64url Encoding Standard](https://datatracker.ietf.org/doc/html/rfc4648#section-5)

## 📊 Quick Reference

### Common Commands

{: .table .table-bordered .table-striped .table-hover}
| Action | Command |
|--------|---------|
| Start services | `docker-compose up -d` |
| Stop services | `docker-compose stop` |
| View logs | `docker-compose logs -f` |
| Check status | `docker-compose ps` |
| Validate config | `docker-compose config` |
| Remove all data | `docker-compose down -v` |

### Service URLs

{: .table .table-bordered .table-striped .table-hover}
| Service | URL | Default Port |
|---------|-----|--------------|
| PostHog Web | http://localhost:8080 | 8080 |
| PostgreSQL | localhost | 5432 |
| Redis | localhost | 6379 |
| ClickHouse | localhost | 8123 |
| Kafka | localhost | 9092 |

## 🤝 Contributing

Found an issue or have an improvement? 
- [Open an issue](https://github.com/PostHog/posthog/issues)
- [Submit a pull request](https://github.com/PostHog/posthog/pulls)
- [Join the community](https://posthog.com/slack)

## License

This configuration follows PostHog's MIT license.

---

**Last Updated:** 2025-11-02  
**Maintained by:** PostHog Development Team  
**Repository:** [PostHog GitHub](https://github.com/PostHog/posthog)
