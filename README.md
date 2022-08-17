# Paste Service On Top Of ClickHouse

https://pastila.nl/

## About

[Read the blog post](https://clickhouse.com/blog/building-a-paste-service-with-clickhouse/).

This service is developed to demonstrate some features of ClickHouse
like asynchronous INSERTs, direct querying from HTML page, MATERIALIZED and EPHEMERAL columns,
CONSTRAINTS, custom HTTP handlers, quotas and user access control, etc.
in a toy service similar to "pastebin" or "gist".

Features:
- data is instantly saved in ClickHouse after pasting or editing - single page with no "save" button;
- after data is saved or loaded, you see the check mark in the bottom right corner;
- just copy the link from the address bar - it is a permanent link to the data;
- you can edit already saved data but the new link will be created and the old links remain permanent;
- you can host Markdown pages - just add .md to the URL and share it;
- you can host HTML pages - just add .html to the URL and share it
  this is very insecure, see "open redirect";
- browser history is used while editing for easy undo;
- edit history is also saved in the database: after you load the data,
  previous version of the data is available by clicking the "back" button in bottom right corner;
- Added Encryption option to encrypt data in browser before inserting into ClickHouse database,
  encryption key is kept in anchor tag which never leaves the user's browser.

## Motivation

ClickHouse is analytical database, and the usage scenario of this service
is definitely not the most natural for ClickHouse.
Nevertheless, it is always important to test the system in corner cases
and unusual scenarios to find potential flaws and to explore new possibilities.

## Contributing

Please send a pull request to
https://github.com/ClickHouse/pastila

## Terms Of Use

This service can be used for helping ClickHouse development.
No other usages permitted.

## Warranty

No warranties or conditions of any kind, either express or implied.
The data can be removed or lost at any moment of time.

## Security And Privacy

This service may not provide any security or privacy.

## Cookie Policy

This service does not use cookies.

## Report Abuse

To report abuse, write to feedback@clickhouse.com. DMCA violations should be reported as well.

## Installation

```
CREATE DATABASE paste ENGINE = Replicated('/clickhouse/databases/paste/', '{shard}', '{replica}');

CREATE TABLE paste.data
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

    CONSTRAINT length CHECK length(content) < 10 * 1024 * 1024,
    CONSTRAINT hash_is_correct CHECK sipHash128(content) = reinterpretAsFixedString(hash),
    CONSTRAINT not_uniform_random CHECK length(content) < 10000 OR arrayReduce('entropy', extractAll(content, '.')) < 7,
    CONSTRAINT not_constant CHECK length(content) < 10000 OR arrayReduce('uniqUpTo(1)', extractAll(content, '.')) > 1,

    PRIMARY KEY (fingerprint, hash)
)
ENGINE = ReplicatedMergeTree;

CREATE USER paste IDENTIFIED WITH no_password
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

CREATE QUOTA paste
KEYED BY ip_address
FOR RANDOMIZED INTERVAL 1 MINUTE MAX query_selects = 100, query_inserts = 1000, written_bytes = '10M',
FOR RANDOMIZED INTERVAL 1 HOUR MAX query_selects = 1000, query_inserts = 10000, written_bytes = '50M',
FOR RANDOMIZED INTERVAL 1 DAY MAX query_selects = 5000, query_inserts = 50000, written_bytes = '200M'
TO paste;

GRANT SELECT, INSERT ON paste.data TO paste;
```
