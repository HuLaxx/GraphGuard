/**
 * GraphGuard - Load Testing Script (k6)
 * ======================================
 * File: tests/load/k6_load_test.js
 * 
 * Production load testing for GraphGuard API.
 * Tests: /health, /score endpoints with realistic load patterns.
 * 
 * Usage:
 *   # Install k6: https://k6.io/docs/getting-started/installation/
 *   
 *   # Run smoke test (10 users, 1 minute)
 *   k6 run --env SCENARIO=smoke tests/load/k6_load_test.js
 *   
 *   # Run load test (100 users, 5 minutes)
 *   k6 run --env SCENARIO=load tests/load/k6_load_test.js
 *   
 *   # Run stress test (500 users, 10 minutes)
 *   k6 run --env SCENARIO=stress tests/load/k6_load_test.js
 *   
 *   # Run spike test (sudden burst)
 *   k6 run --env SCENARIO=spike tests/load/k6_load_test.js
 */

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Counter, Rate, Trend } from 'k6/metrics';

// ============================================
// Configuration
// ============================================

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const API_KEY = __ENV.API_KEY || 'gguard_dev_key_9x7k2p4m1n8q6r5t3w0z';

// Custom metrics
const fraudScoreLatency = new Trend('fraud_score_latency', true);
const healthCheckLatency = new Trend('health_check_latency', true);
const errorRate = new Rate('error_rate');
const rateLimitHits = new Counter('rate_limit_hits');

// ============================================
// Test Scenarios
// ============================================

const scenarios = {
    smoke: {
        executor: 'constant-vus',
        vus: 10,
        duration: '1m',
    },
    load: {
        executor: 'ramping-vus',
        startVUs: 0,
        stages: [
            { duration: '1m', target: 50 },   // Ramp up
            { duration: '3m', target: 100 },  // Stay at 100
            { duration: '1m', target: 0 },    // Ramp down
        ],
    },
    stress: {
        executor: 'ramping-vus',
        startVUs: 0,
        stages: [
            { duration: '2m', target: 100 },
            { duration: '3m', target: 300 },
            { duration: '3m', target: 500 },
            { duration: '2m', target: 0 },
        ],
    },
    spike: {
        executor: 'ramping-vus',
        startVUs: 0,
        stages: [
            { duration: '10s', target: 10 },
            { duration: '10s', target: 500 },  // Sudden spike
            { duration: '30s', target: 500 },
            { duration: '10s', target: 10 },
        ],
    },
};

const selectedScenario = __ENV.SCENARIO || 'smoke';

export const options = {
    scenarios: {
        default: scenarios[selectedScenario],
    },
    thresholds: {
        // SLA thresholds
        'fraud_score_latency': ['p95<100', 'p99<200'],  // 95th < 100ms, 99th < 200ms
        'health_check_latency': ['p95<50'],             // Health checks < 50ms
        'error_rate': ['rate<0.01'],                    // <1% errors
        'http_req_duration': ['p95<150'],               // Overall p95 < 150ms
    },
};

// ============================================
// Test Data Generators
// ============================================

function generateTransactionId() {
    return `txn_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

function generateUserId() {
    return `user_${Math.floor(Math.random() * 10000)}`;
}

function generateDeviceId() {
    return `device_${Math.random().toString(36).substr(2, 16)}`;
}

function generateTransaction() {
    const amounts = [25, 50, 100, 250, 500, 1000, 2500, 5000];
    const merchants = ['merchant_001', 'merchant_002', 'merchant_003', 'merchant_004'];

    return {
        transaction_id: generateTransactionId(),
        user_id: generateUserId(),
        merchant_id: merchants[Math.floor(Math.random() * merchants.length)],
        amount: amounts[Math.floor(Math.random() * amounts.length)],
        currency: 'USD',
        device_id: generateDeviceId(),
        ip_address: `192.168.${Math.floor(Math.random() * 255)}.${Math.floor(Math.random() * 255)}`,
    };
}

// ============================================
// HTTP Headers
// ============================================

const headers = {
    'Content-Type': 'application/json',
    'X-API-Key': API_KEY,
};

// ============================================
// Test Functions
// ============================================

function testHealthEndpoint() {
    const start = Date.now();
    const res = http.get(`${BASE_URL}/health`, { headers });
    const duration = Date.now() - start;

    healthCheckLatency.add(duration);

    const passed = check(res, {
        'health status 200': (r) => r.status === 200,
        'health has status field': (r) => JSON.parse(r.body).status !== undefined,
    });

    errorRate.add(!passed);

    return passed;
}

function testScoreEndpoint() {
    const transaction = generateTransaction();
    const payload = JSON.stringify(transaction);

    const start = Date.now();
    const res = http.post(`${BASE_URL}/score`, payload, { headers });
    const duration = Date.now() - start;

    fraudScoreLatency.add(duration);

    // Handle rate limiting
    if (res.status === 429) {
        rateLimitHits.add(1);
        return true; // Rate limiting is expected, not an error
    }

    const passed = check(res, {
        'score status 200': (r) => r.status === 200,
        'score has fraud_score': (r) => {
            try {
                const body = JSON.parse(r.body);
                return body.fraud_score !== undefined &&
                    body.fraud_score >= 0 &&
                    body.fraud_score <= 1;
            } catch (e) {
                return false;
            }
        },
        'score has decision': (r) => {
            try {
                const body = JSON.parse(r.body);
                return ['AUTO_APPROVE', 'REVIEW', 'AUTO_DECLINE'].includes(body.decision);
            } catch (e) {
                return false;
            }
        },
        'score latency < 100ms': (r) => duration < 100,
    });

    errorRate.add(!passed);

    return passed;
}

// ============================================
// Main Test Flow
// ============================================

export default function () {
    // 10% health checks, 90% score requests (realistic production mix)
    if (Math.random() < 0.1) {
        testHealthEndpoint();
    } else {
        testScoreEndpoint();
    }

    // Random think time (simulate real user behavior)
    sleep(Math.random() * 0.5 + 0.1); // 100-600ms
}

// ============================================
// Setup and Teardown
// ============================================

export function setup() {
    console.log(`Starting ${selectedScenario} test against ${BASE_URL}`);

    // Verify API is reachable
    const healthRes = http.get(`${BASE_URL}/health`);
    if (healthRes.status !== 200) {
        throw new Error(`API not reachable: ${healthRes.status}`);
    }

    return {
        startTime: Date.now(),
        scenario: selectedScenario,
    };
}

export function teardown(data) {
    const duration = (Date.now() - data.startTime) / 1000;
    console.log(`Test completed in ${duration.toFixed(2)} seconds`);
}

// ============================================
// Summary Report Handler
// ============================================

export function handleSummary(data) {
    // Generate summary JSON
    const summary = {
        timestamp: new Date().toISOString(),
        scenario: selectedScenario,
        metrics: {
            fraud_score_p95: data.metrics.fraud_score_latency.values.p95,
            fraud_score_p99: data.metrics.fraud_score_latency.values.p99,
            error_rate: data.metrics.error_rate.values.rate,
            total_requests: data.metrics.http_reqs.values.count,
            rate_limit_hits: data.metrics.rate_limit_hits?.values.count || 0,
        },
        passed: Object.values(data.thresholds).every(t => t.ok),
    };

    return {
        'tests/load/results/summary.json': JSON.stringify(summary, null, 2),
        stdout: textSummary(data, { indent: ' ', enableColors: true }),
    };
}

function textSummary(data) {
    return `
================================================================================
                        GraphGuard Load Test Summary
================================================================================

Scenario: ${selectedScenario}
Base URL: ${BASE_URL}

📊 Performance Metrics:
   • Fraud Score Latency (p95): ${data.metrics.fraud_score_latency?.values.p95?.toFixed(2) || 'N/A'} ms
   • Fraud Score Latency (p99): ${data.metrics.fraud_score_latency?.values.p99?.toFixed(2) || 'N/A'} ms
   • Health Check Latency (p95): ${data.metrics.health_check_latency?.values.p95?.toFixed(2) || 'N/A'} ms
   • Total Requests: ${data.metrics.http_reqs?.values.count || 0}
   • Request Rate: ${data.metrics.http_reqs?.values.rate?.toFixed(2) || 0} req/s

❌ Error Metrics:
   • Error Rate: ${(data.metrics.error_rate?.values.rate * 100)?.toFixed(2) || 0}%
   • Rate Limit Hits: ${data.metrics.rate_limit_hits?.values.count || 0}

✅ Threshold Results:
${Object.entries(data.thresholds || {}).map(([name, result]) =>
        `   • ${name}: ${result.ok ? '✓ PASS' : '✗ FAIL'}`
    ).join('\n')}

================================================================================
`;
}
