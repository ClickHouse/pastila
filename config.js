// ClickHouse Configuration
// This file is loaded before the main script and configures the ClickHouse URL

// Auto-detect environment based on hostname
const isLocalDevelopment = window.location.hostname === 'localhost' ||
                          window.location.hostname === '127.0.0.1' ||
                          window.location.hostname === '';

// Configure ClickHouse URL based on environment
// For local development, this points to local Docker instance
// For production, this points to ClickHouse Cloud
const detectedUrl = isLocalDevelopment
    ? "http://localhost:18123/?user=paste"
    : "https://uzg8q0g12h.eu-central-1.aws.clickhouse.cloud/?user=paste";

// You can also manually override by setting localStorage:
// localStorage.setItem('clickhouse_url', 'http://your-custom-url:8123/?user=paste');
const manual_override = localStorage.getItem('clickhouse_url');
if (manual_override) {
    console.log('Using manual ClickHouse URL override:', manual_override);
}

// Export the configured URL
window.CLICKHOUSE_URL = manual_override || detectedUrl;

console.log('ClickHouse URL configured:', window.CLICKHOUSE_URL);
