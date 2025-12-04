-- Create database for local development (using default engine instead of Replicated)
CREATE DATABASE IF NOT EXISTS paste;

-- Create main data table
CREATE TABLE IF NOT EXISTS paste.data
(
    fingerprint UInt32 DEFAULT reinterpretAsUInt32(unhex(fingerprint_hex)),
    hash UInt128 DEFAULT reinterpretAsUInt128(unhex(hash_hex)),
    prev_fingerprint UInt32 DEFAULT reinterpretAsUInt32(unhex(prev_fingerprint_hex)),
    prev_hash UInt128 DEFAULT reinterpretAsUInt128(unhex(prev_hash_hex)),
    content String,

    size UInt32 MATERIALIZED length(content),
    time DateTime64 MATERIALIZED now64(),
    query_id String MATERIALIZED queryID(),

    fingerprint_hex String EPHEMERAL '',
    hash_hex String EPHEMERAL '',
    prev_fingerprint_hex String EPHEMERAL '',
    prev_hash_hex String EPHEMERAL '',
    is_encrypted UInt8,
    burn_after_reading UInt8 DEFAULT 0,

    CONSTRAINT length CHECK length(content) < 10 * 1024 * 1024,
    CONSTRAINT hash_is_correct CHECK sipHash128(content) = reinterpretAsFixedString(hash),
    CONSTRAINT not_uniform_random CHECK length(content) < 10000 OR arrayReduce('entropy', extractAll(content, '.')) < 7,
    CONSTRAINT not_constant CHECK length(content) < 10000 OR arrayReduce('uniqUpTo(1)', extractAll(content, '.')) > 1,

    PRIMARY KEY (fingerprint, hash)
)
ENGINE = MergeTree;

-- Create paste user with CORS and async insert settings
CREATE USER IF NOT EXISTS paste IDENTIFIED WITH no_password
DEFAULT DATABASE paste
SETTINGS
    add_http_cors_header = 1 READONLY,
    async_insert = 1 READONLY,
    wait_for_async_insert = 0 READONLY,
    limit = 1 READONLY,
    offset = 0 READONLY,
    max_result_rows = 1 READONLY,
    force_primary_key = 1 READONLY,
    max_query_size = '10M' READONLY;

-- Create internal paste_sys user for the view
CREATE USER IF NOT EXISTS paste_sys HOST LOCAL IDENTIFIED WITH no_password
DEFAULT DATABASE paste
SETTINGS
    add_http_cors_header = 1 READONLY,
    async_insert = 1 READONLY,
    wait_for_async_insert = 0 READONLY,
    limit = 1 READONLY,
    offset = 0 READONLY,
    max_result_rows = 1 READONLY,
    force_primary_key = 1 READONLY,
    max_query_size = '10M' READONLY;

-- Create quota for rate limiting
CREATE QUOTA IF NOT EXISTS paste
KEYED BY ip_address
FOR RANDOMIZED INTERVAL 1 MINUTE MAX query_selects = 100, query_inserts = 1000,
FOR RANDOMIZED INTERVAL 1 HOUR MAX query_selects = 1000, query_inserts = 10000,
FOR RANDOMIZED INTERVAL 1 DAY MAX query_selects = 5000, query_inserts = 50000, written_bytes = '500M'
TO paste;

-- Create view with definer for access control
CREATE VIEW IF NOT EXISTS paste.data_view DEFINER = 'paste_sys' AS
SELECT * FROM paste.data
WHERE fingerprint = reinterpretAsUInt32(unhex({fingerprint:String}))
  AND hash = reinterpretAsUInt128(unhex({hash:String}))
ORDER BY time LIMIT 1;

-- Grant permissions
GRANT INSERT ON paste.data TO paste;
GRANT SELECT ON paste.data_view TO paste;
GRANT ALTER UPDATE ON paste.data TO paste;  -- Required for DELETE in ClickHouse
GRANT SELECT ON paste.data TO paste_sys;
