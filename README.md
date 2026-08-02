# Locust Performance Testing Framework

A structured, baseline-driven performance testing framework built on [Locust](https://locust.io/). Simulates realistic multi-page user journeys, automatically captures and compares baselines, evaluates SLA compliance per API, and generates HTML reports per run.

---

## Table of Contents

- [Overview](#overview)
- [Project Structure](#project-structure)
- [How It Works](#how-it-works)
- [Setup](#setup)
- [Configuration](#configuration)
- [Running Tests](#running-tests)
- [Reports](#reports)
- [Logging](#logging)
- [Architecture Decisions](#architecture-decisions)
- [Pending Work](#pending-work)

---

## Overview

Most performance testing frameworks require manually maintained thresholds. This framework instead **auto-captures a baseline on first run** and compares every subsequent run against it — detecting regressions, new APIs, and removed APIs automatically.

It supports two test modes:

| Mode | Purpose |
|---|---|
| `journey` | Simulates a full user session across all 4 pages sequentially, with profile-driven file sizes |
| `stress` | _(Pending)_ Targets specific APIs at high concurrency with matrix reporting |

---

## Project Structure

```
run_performance.py              ← CLI entry point + Locust orchestrator
locustfile.py                   ← mode-switches between JourneyUser / StressUser

tasks/
    journey/
        __init__.py
        base_page.py            ← shared BasePage class (timing, event firing)
        data_prep_page.py       ← Page 1: upload + download + polling
        baseline_page.py        ← Page 2: upload + download + polling
        scoping_page.py         ← Page 3: download + polling only
        study_details_page.py   ← Page 4: API calls only
    stress/
        __init__.py
        file_upload.py          ← stress mode task (stub)
    journey_behavior.py         ← JourneyUser(HttpUser) — round-robin profiles
    stress_behavior.py          ← StressUser (stub)
    upload_behavior.py          ← legacy upload behavior (keep until journey verified)

api/
    upload_api.py
    data_prep_api.py
    baseline_api.py
    scoping_api.py
    study_details_api.py

config/
    profile_config/
        profile_50_rows.yml     ← profile: 50-row data files
        profile_100_rows.yml    ← profile: 100-row data files
    profile_test_data/
        data_prep/              ← data prep upload files
        baseline/               ← baseline upload files
    stress_config/
        stress_config.yml
    study_config.yml            ← study IDs for user assignment

utils/
    logger.py                   ← setup_logger() + get_logger()
    comparison_engine.py        ← baseline load/save/archive/diff
    sla_engine.py               ← SLA evaluation + breach detection
    stats_parser.py             ← Locust CSV parsing
    config_validator.py         ← pre-flight validation per mode
    profile_loader.py           ← YAML profile loading + sorting
    report_manager.py           ← HTML report generation
    polling_engine.py           ← async job polling
    get_api_complexity.py       ← API complexity tier lookup

reports/                        ← timestamped per-run output directories
    YYYY-MM-DD_HH-MM-SS/
        report.html             ← Locust default HTML report
        performance_report.html ← baseline comparison report
        page_report.html        ← page-level report with charts
        report_stats.csv        ← raw Locust stats
        run.log                 ← structured log for this run

baselineResults.json            ← current baseline (auto-captured)
baseline_history/               ← archived results from every past run
```

---

## How It Works

### First Run — Baseline Capture

When no `baselineResults.json` exists, the framework runs Locust and saves the results as a baseline. All subsequent runs compare against this baseline.

```
No baselineResults.json found
        ↓
Run Locust
        ↓
Parse report_stats.csv
        ↓
Save baselineResults.json
        ↓
Exit
```

### Subsequent Runs — Comparison Mode

```
baselineResults.json exists
        ↓
Run Locust
        ↓
Parse report_stats.csv
        ↓
Compare current vs baseline per API
        ↓
Classify each API: PASS / BREACH / NEW_API / REMOVED_API
        ↓
Generate performance_report.html + page_report.html
        ↓
Archive run to baseline_history/
        ↓
Warn if baseline > 30 days old
```

### Journey Mode — User Flow

Each virtual user is assigned one profile and one study ID at spawn time. All 4 pages execute sequentially in that order, every time:

```
User spawns
    ↓
on_start() — assign profile (round-robin) + study ID
    ↓
Page 1: Data Prep     — POST upload → poll → GET download → poll
    ↓
Page 2: Baseline      — POST upload → poll → GET download → poll
    ↓
Page 3: Scoping       — GET download → poll
    ↓
Page 4: Study Details — GET details + GET summary
    ↓
_mark_complete() — when all users done, quit Locust cleanly
```

### Profile Assignment

Users are distributed across profiles in round-robin order, sorted by `row_count` ascending:

```
2 profiles, 4 users:
  User 1 → profile_50_rows
  User 2 → profile_100_rows
  User 3 → profile_50_rows
  User 4 → profile_100_rows
```

If `--users` is not evenly divisible by profile count, earlier profiles get one extra user and a warning is logged.

---

## Setup

### Requirements

- Python 3.10+
- [Poetry](https://python-poetry.org/)

### Install

```bash
poetry install
```

### Environment Variables

| Variable | Default | Description |
|---|---|---|
| `TARGET_HOST` | `https://postman-echo.com` | Base URL for the application under test |
| `LOCUST_MODE` | `journey` | Set automatically by `run_performance.py` — do not set manually |

---

## Configuration

### Profile YAML (`config/profile_config/`)

Each profile describes the data files and SLA expectations for one user persona:

```yaml
profile_name: "profile_50_rows"
row_count: 50

page_data:

  data_prep_page:
    data_file: "data_prep/data_upload_1.xlsx"
    polling:
      interval_seconds: 10
      expected_ms: 120000
      max_wait_ms: 300000
    expected_sla:
      upload_max_ms: 30000
      download_max_ms: 15000

  baseline_page:
    data_file: "baseline/baseline_data_1.xlsx"
    polling:
      interval_seconds: 10
      expected_ms: 60000
      max_wait_ms: 180000
    expected_sla:
      upload_max_ms: 20000
      download_max_ms: 10000

  scoping_page:
    polling:
      interval_seconds: 5
      expected_ms: 30000
      max_wait_ms: 90000
    expected_sla:
      download_max_ms: 10000

  study_details_page:
    expected_sla:
      page_load_max_ms: 5000
```

Pages without a `data_file` (e.g. `scoping_page`) are download-only or API-only — the validator skips file existence checks for those pages automatically.

### Study Config (`config/study_config.yml`)

Maps users to study IDs. User 1 gets the first entry, User 2 gets the second, and so on:

```yaml
- study_id: 1001
- study_id: 1002
- study_id: 1003
```

If fewer study IDs are available than users requested, excess users skip their journeys and a warning is logged. This is never a hard stop.

### SLA Override (`config/profile_config/`)

Per-page SLA values in each profile YAML (under `expected_sla`) override the baseline comparison for that metric. When an SLA override is present, the metric is evaluated against the configured threshold rather than the captured baseline value.

---

## Running Tests

### Journey Mode (default)

```bash
poetry run python run_performance.py \
  --mode journey \
  --users 4 \
  --spawn-rate 2 \
  --run-time 30s
```

### Stress Mode (stub — not yet implemented)

```bash
poetry run python run_performance.py \
  --mode stress \
  --users 20 \
  --spawn-rate 5 \
  --run-time 300s
```

### CLI Arguments

| Argument | Default | Description |
|---|---|---|
| `--mode` | `journey` | `journey` or `stress` |
| `--users` | `3` | Number of concurrent virtual users |
| `--spawn-rate` | `2` | Users spawned per second |
| `--run-time` | `20s` | Duration to run (e.g. `30s`, `5m`, `1h`) |
| `--reset-baseline` | — | Delete `baselineResults.json` and re-capture on next run |
| `--clean-baseline` | — | Prune APIs from baseline that were not present in the last run |

### Recommended User Counts

Use a multiple of the number of profiles for even distribution:

```bash
# 2 profiles → use 2, 4, 6, 8 ...
poetry run python run_performance.py --users 4

# 3 profiles → use 3, 6, 9, 12 ...
poetry run python run_performance.py --users 6
```

---

## Reports

Three reports are generated per run inside a timestamped directory under `reports/`:

### `report.html` — Locust Default

The standard Locust HTML report. Contains request counts, response time percentiles, failure rates, and charts over time.

### `performance_report.html` — Baseline Comparison

Per-API comparison against the captured baseline. Each metric (avg, p95, p99, failure rate, etc.) is evaluated and classified:

| Status | Meaning |
|---|---|
| `PASS` | Within acceptable deviation from baseline |
| `BREACH` | Exceeded baseline threshold or SLA override |
| `NEW_API` | API present in current run but not in baseline |
| `REMOVED_API` | API in baseline but absent from current run |

A summary section shows total counts per status and lists all breached APIs with the metrics that triggered the breach.

### `page_report.html` — Page-Level Analysis

Visualises performance grouped by page and profile. Includes:

- **Grouped bar chart** — compare avg response time across profiles per page (filterable by profile via checkboxes)
- **Doughnut chart** — operation breakdown for a selected profile (upload vs download vs API calls)
- **Page cards** — per-page summary showing avg, p95, and request count for each profile

PAGE-type events (fired at the end of each page's `execute()`) are excluded from `performance_report.html` to avoid polluting the baseline comparison with composite timings.

---

## Logging

Every run writes a `run.log` file inside its report directory, alongside the HTML reports.

### Log Levels

| Destination | Level | Contains |
|---|---|---|
| Console | `INFO` and above | Run summary, warnings, errors, SLA breaches |
| `run.log` | `DEBUG` and above | Everything — every poll tick, page start/end, user assignments |

### Log Format

```
2026-03-13 10:45:23,411 | INFO     | __main__                                 | Performance run starting — mode: journey | users: 4 | spawn-rate: 2 | run-time: 30s
2026-03-13 10:45:23,412 | INFO     | __main__                                 | Loaded 2 profile(s): profile_50_rows, profile_100_rows
2026-03-13 10:45:23,413 | WARNING  | __main__                                 | Users (3) not evenly divisible by profiles (2)
2026-03-13 10:45:45,201 | WARNING  | __main__                                 | SLA breach — [data_prep_page][profile_100_rows] POST /api/data-prep/upload
```

### Module-Level Logger Usage

Each module calls `get_logger(__name__)` at module level:

```python
from utils.logger import get_logger

logger = get_logger(__name__)
logger.info("Starting upload")
logger.debug(f"Polling job {job_id} — attempt {attempt}")
logger.warning("Expected duration exceeded")
logger.error(f"Upload failed: {e}")
```

Locust's own log output is unified into the same `run.log` via a shared file handler.
