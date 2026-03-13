# Reporting & Metrics Guide

This document explains how to interpret test reports, understand performance metrics, and analyze test results.

## Table of Contents

- [Overview](#overview)
- [Report Files & Formats](#report-files--formats)
- [HTML Report Guide](#html-report-guide)
- [CSV Reports Explained](#csv-reports-explained)
- [Understanding Metrics](#understanding-metrics)
- [Performance Metrics Deep Dive](#performance-metrics-deep-dive)
- [SLA Validation](#sla-validation)

## Overview

After each test run, Locust generates multiple report files in `reports/<timestamp>/`:

```
reports/2026-03-01_16-44-40/
├── report.html                    # Interactive web report
├── report_stats.csv               # Summary statistics
├── report_stats_history.csv       # Per-request timing history
├── report_failures.csv            # Failed requests
└── report_exceptions.csv          # Exceptions encountered
```

## Report Files & Formats

### File Locations

All reports are timestamped and organized in `reports/` directory:

### Report Generation

Reports are created by Locust automatically during test execution:

### Report Sections

The HTML report contains multiple sections:

#### 1. **Summary Section**

Shows overall test results:

```
Test Started: 2026-03-01 16:44:40
Test Duration: 30 seconds
Number of Requests: 150
Number of Failures: 3
Failure Rate: 2%
Min Response Time: 45 ms
Max Response Time: 1250 ms
Average Response Time: 245 ms
Median Response Time: 201 ms
```

#### 2. **Requests Summary Table**

Lists all endpoints tested:

| Type | Name | # Requests | # Failures | Median | Average | Min | Max | Content Size | req/s |
|------|------|-----------|-----------|--------|---------|-----|-----|--------------|-------|
| GET | /auth/me | 100 | 0 | 150ms | 165ms | 45ms | 350ms | 2.5KB | 3.3/s |
| POST | /auth/login | 30 | 3 | 200ms | 245ms | 100ms | 1250ms | 1.2KB | 1.0/s |
| GET | /users | 20 | 0 | 120ms | 130ms | 60ms | 200ms | 15KB | 0.7/s |

**Key Columns:**
- **# Requests**: Total requests to this endpoint
- **# Failures**: Failed requests (status code > 400, timeout, exception)
- **Median**: 50th percentile response time
- **Average**: Mean response time
- **Min/Max**: Fastest and slowest requests
- **req/s**: Requests per second throughput

#### 3. **Charts & Graphs**

Visual representation of metrics:

- **Response Time Over Time**: Shows latency trends during test
- **Request/Failure Rate**: Shows request throughput and failures per second
- **Response Time Percentiles**: Shows p50, p95, p99 distribution
- **Requests Per Second**: Shows throughput trends

### Interpreting the HTML Report

**Good Performance Indicators:**
- ✅ Average response time < 500ms
- ✅ Failure rate < 1%
- ✅ P95 < 1000ms
- ✅ Consistent response times (low variance)
- ✅ Stable throughput

**Warning Signs:**
- ⚠️ Increasing response times over time (degradation)
- ⚠️ Increasing failure rate over time
- ⚠️ High variance in response times
- ⚠️ Throughput declining during test

**Poor Performance Indicators:**
- ❌ Average response time > 2000ms
- ❌ Failure rate > 5%
- ❌ P95 > 5000ms
- ❌ Frequent errors/exceptions
- ❌ Complete request failures

---

## CSV Reports Explained

### report_stats.csv - Summary Statistics

```
Name,# requests,# failures,Median response time,Average response time,Min response time,Max response time,Average Content-Length,Requests/s
GET /auth/me,100,0,150,165,45,350,2500,3.33
POST /auth/login,30,3,200,245,100,1250,1200,1.00
GET /users,20,0,120,130,60,200,15000,0.67
Aggregated,150,3,155,171,45,1250,5567,5.00
```

**Key Row: "Aggregated"**

The last row "Aggregated" combines all requests:

| Column | Meaning | Example |
|--------|---------|---------|
| # requests | Total requests | 150 |
| # failures | Total failures | 3 |
| Median response time | 50th percentile latency (ms) | 155 |
| Average response time | Mean latency (ms) | 171 |
| Min response time | Fastest request (ms) | 45 |
| Max response time | Slowest request (ms) | 1250 |
| Average Content-Length | Avg response body size (bytes) | 5567 |
| Requests/s | Throughput | 5.00 |

### report_stats_history.csv - Time-Series Data

```
Time,Type,Name,# requests,# failures,Median response time,Average response time,Min response time,Max response time,Average Content-Length,Requests/s
1234567890,GET,/auth/me,10,0,150,160,50,300,2500,3.33
1234567891,GET,/auth/me,10,1,160,170,45,350,2500,3.35
1234567892,GET,/auth/me,9,0,145,155,55,250,2500,3.00
...
```
### report_failures.csv - Failed Requests

```
Method,Name,# failures,Failure,Occurrences
POST,/auth/login,3,"HTTP 401: Unauthorized",3
```

**Columns:**
- **Method**: HTTP method (GET, POST, etc.)
- **Name**: Endpoint path
- **# failures**: Count of this failure type
- **Failure**: Error message
- **Occurrences**: How many times occurred

**Analysis:**
- Look for recurring failure patterns
- Check if failures are transient or consistent
- Identify which endpoints are failing

### report_exceptions.csv - Exceptions

```
Method,Name,# occurrences,Exception,Traceback
GET,/users,2,"ConnectionError: Connection refused",traceback...
POST,/auth/login,1,"Timeout: Request timed out",traceback...
```

**Common Exceptions:**
- `ConnectionError`: Cannot connect to server
- `TimeoutError`: Request took too long
- `JSONDecodeError`: Invalid JSON response
- `AssertionError`: Validation failed

---

## Understanding Metrics

### Response Time Metrics

**Median (50th Percentile)**
- 50% of requests faster, 50% slower
- Good for: Understanding typical request speed
- Less affected by outliers

**Average (Mean)**
- Sum of all latencies / number of requests
- Good for: Overall performance
- Affected by outliers

**95th Percentile (P95)**
- 95% of requests faster, 5% slower
- Good for: SLA boundaries, user experience
- Detects slow outliers

**99th Percentile (P99)**
- 99% of requests faster, 1% slower
- Good for: Worst-case scenarios
- Very sensitive to outliers

**Example Distribution:**
```
Request latencies: [50ms, 60ms, 100ms, 150ms, 200ms, 500ms, 1000ms, 2000ms]

Median (P50): 150ms - 50% of requests faster
Average: 381ms - mean of all
P95: 1900ms - 95% faster
P99: 2000ms - 99% faster
```

### Failure Rate

**Definition:**
```
Failure Rate = (# Failed Requests / Total Requests) × 100%
```

**Examples:**
- 3 failures out of 150 requests = 2% failure rate
- 1 failure out of 100 requests = 1% failure rate
- 10 failures out of 1000 requests = 1% failure rate

**Acceptable Thresholds:**
- Production: < 0.1% (99.9% success)
- Staging: < 1% (99% success)
- Development: < 5% (95% success)

### Throughput (Requests Per Second)

**Definition:**
```
Throughput = Total Requests / Test Duration (seconds)
```

**Example:**
```
150 total requests / 30 seconds = 5 requests/second
```

**Use Cases:**
- Estimate API capacity
- Compare performance across runs
- Identify bottlenecks

**Factors Affecting Throughput:**
- Number of concurrent users
- Response time (faster = more throughput)
- Task mix and wait times
- API processing speed

---

## Performance Metrics Deep Dive

### Key Performance Indicators (KPIs)

#### 1. **Response Time (Latency)**

**What it means:** How long requests take to complete

**Good targets:**
- API calls: 100-500ms
- Database queries: 10-100ms
- External calls: 500-2000ms

**Measurement:**
```
Request starts → Server processes → Response returns → Total Time
```

**Factors affecting:**
- Network latency
- Server processing time
- Database query time
- Authentication/authorization time
- Data serialization

#### 2. **Throughput**

**What it means:** How many requests per second the API can handle

**Example:**
```
10 concurrent users × 2 requests/user/minute = 20 requests/minute = 0.33 req/sec
```

**Good targets:**
- Low-traffic APIs: 1-10 req/sec
- Medium APIs: 10-100 req/sec
- High-traffic APIs: 100+ req/sec

#### 3. **Failure Rate**

**What it means:** Percentage of requests that fail

**Acceptable targets:**
```
Production:  < 0.1% (99.9% success - SLA)
Staging:     < 1%   (99% success)
Development: < 5%   (95% success)
```

**Types of failures:**
- HTTP errors (4xx, 5xx)
- Timeouts
- Connection refused
- Invalid responses

#### 4. **Concurrent Users**

**What it means:** Number of simultaneous users

**Examples:**
```
Users = 5    → Light load
Users = 100  → Moderate load
Users = 1000 → Heavy load
Users = 10000 → Extreme load
```

**Determines:**
- How realistic the test is
- How much load on the API
- Ability to find bottlenecks

---

## SLA Validation

### Understanding SLA Thresholds

SLAs (Service Level Agreements) define acceptable performance:

```python
# Environment variables
MAX_AVG_RESPONSE_TIME = 500      # Average must be < 500ms
MAX_P95_RESPONSE_TIME = 1000     # P95 must be < 1000ms
MAX_FAILURE_RATE = 5             # Failures must be < 5%
```

For more details, see:
- [ARCHITECTURE.md](ARCHITECTURE.md) — How metrics are collected

