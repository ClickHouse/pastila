# Local Development Setup

This guide explains how to run Pastila locally with a Docker-based ClickHouse instance.

## Prerequisites

- Docker and Docker Compose
- Python 3 (for the HTTP server)

## Quick Start

1. **Start ClickHouse in Docker:**
   ```bash
   docker-compose up -d
   ```

   This will:
   - Start a local ClickHouse server on ports 18123 (HTTP) and 19000 (native)
   - Automatically run the initialization script (`init-db.sql`)
   - Create the database schema, users, quotas, and views

2. **Wait for ClickHouse to be ready:**
   ```bash
   # Check if ClickHouse is healthy
   docker-compose ps

   # Or watch the logs
   docker-compose logs -f clickhouse
   ```

3. **Start the local web server:**
   ```bash
   python3 -m http.server 8080
   ```

4. **Open in browser:**
   ```
   http://localhost:8080
   ```

   The application will automatically detect it's running locally and connect to `http://localhost:18123`.

## Configuration

### Automatic Environment Detection

The `config.js` file automatically detects if you're running locally:
- **Local development** (localhost/127.0.0.1): Uses `http://localhost:18123/?user=paste`
- **Production** (pastila.nl): Uses the ClickHouse Cloud URL

### Manual Override

You can manually override the ClickHouse URL in the browser console:

```javascript
localStorage.setItem('clickhouse_url', 'http://your-custom-url:18123/?user=paste');
// Then reload the page
```

To clear the override:
```javascript
localStorage.removeItem('clickhouse_url');
```

## Useful Commands

### Check ClickHouse is running
```bash
curl http://localhost:18123/
# Should return "Ok."
```

### Query the database directly
```bash
docker-compose exec clickhouse clickhouse-client
```

```sql
-- Show databases
SHOW DATABASES;

-- Show tables in paste database
SHOW TABLES FROM paste;

-- View recent pastes
SELECT fingerprint, hash, length(content) as size, time
FROM paste.data
ORDER BY time DESC
LIMIT 10;
```

### View logs
```bash
docker-compose logs -f clickhouse
```

### Stop services
```bash
docker-compose down
```

### Clean up (removes all data)
```bash
docker-compose down -v
rm -rf clickhouse-data/
```

## Database Schema

The database schema is defined in `init-db.sql` and includes:
- **paste.data** table with constraints for hash validation, size limits, and spam prevention
- **paste.data_view** for access control
- **paste** and **paste_sys** users with specific permissions
- **Quotas** for rate limiting

## Differences from Production

The local setup uses:
- **MergeTree** engine instead of **ReplicatedMergeTree** (single node)
- **No SSL** (http:// instead of https://)
- **Docker-based** ClickHouse instead of ClickHouse Cloud

## Troubleshooting

### Port 18123 or 19000 already in use
The default setup uses ports 18123 (HTTP) and 19000 (native) to avoid conflicts with other services.

If you need to use different ports, modify `docker-compose.yml`:
```yaml
ports:
  - "28123:8123"  # Use port 28123 instead
  - "29000:9000"  # Use port 29000 instead
```

Then update your manual override:
```javascript
localStorage.setItem('clickhouse_url', 'http://localhost:28123/?user=paste');
```

### Database initialization fails
Check the logs:
```bash
docker-compose logs clickhouse
```

You can manually re-run the initialization:
```bash
docker-compose exec clickhouse clickhouse-client < init-db.sql
```

### CORS errors
Make sure you're accessing via `http://localhost:8080` (or similar) and not `file://`.
The ClickHouse user has `add_http_cors_header = 1` enabled.
