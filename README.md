# Locust Performance Testing Framework

A modular, scalable performance testing framework built with [Locust](https://locust.io/) for load testing APIs and web applications. This framework provides a structured approach to performance testing with built-in reporting, configurable test scenarios, and performance threshold validation.

## Table of Contents

- [Quick Start](#quick-start)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Project Structure](#project-structure)
- [Documentation](#documentation)
- [Features](#features)
- [Running Your First Test](#running-your-first-test)
- [Next Steps](#next-steps)
- [Troubleshooting](#troubleshooting)

## Quick Start

```bash
# Install dependencies
poetry install

# Run performance tests
poetry run python run_performance.py

# Reports will be generated in ./reports/<timestamp>/
```

## Prerequisites

- **Python**: 3.14+ (as specified in `pyproject.toml`)
- **Poetry**: For dependency management (install from https://python-poetry.org/)
- **Locust**: 2.43.3+ (automatically installed via Poetry)

## Installation

### Step 1: Clone or navigate to the project

```bash
cd /path/to/locust-performance-poc
```

### Step 2: Install dependencies using Poetry

```bash
poetry install
```

This will install Locust and create a virtual environment specific to this project.

### Step 3: Verify installation

```bash
poetry run locust --version
```

You should see something like: `locust 2.43.3 from ...`

## Project Structure

```
locust-performance-poc/
├── README.md                          # This file
├── ARCHITECTURE.md                    # System design and component overview
├── API_TESTING.md                     # API layer documentation
│
├── pyproject.toml                     # Poetry project configuration
├── poetry.lock                        # Locked dependency versions
│
├── locustfile.py                      # Locust entry point (user class)
├── run_performance.py                 # Test runner with SLA validation
│
├── api/                               # API abstraction layer
│   ├── __init__.py
│   ├── auth_api.py                    # Authentication API wrapper
│   └── user_api.py                    # User operations API wrapper
│
├── config/                            # Configuration management
│   ├── __init__.py
│   └── config.py                      # Base URLs and settings
│
├── tasks/                             # Test tasks and scenarios
│   ├── __init__.py
│   └── user_behavior.py               # User behavior definition
│
├── utils/                             # Utility functions
│   ├── __init__.py
│   ├── data_loader.py                 # Load test data from CSV
│   └── report_manager.py              # Report directory and file management
│
├── test_data/                         # Test data files
│   └── users.csv                      # Sample user credentials
│
└── reports/                           # Generated test reports (created at runtime)
    └── <timestamp>/
        ├── report.html                # Interactive HTML report
        ├── report_stats.csv           # Aggregated statistics
        ├── report_stats_history.csv   # Per-request history
        ├── report_failures.csv        # Failed requests
        └── report_exceptions.csv      # Exceptions encountered
```

For detailed information about each component, see the **Documentation** section below.

## Documentation

This framework includes comprehensive documentation split into focused modules:

| Document | Purpose |
|----------|---------|
| **[ARCHITECTURE.md](ARCHITECTURE.md)** | Understand the overall design, data flow, and architectural patterns |
| **[API_TESTING.md](API_TESTING.md)** | Learn how to use the API abstraction layer and add new endpoints |
| **[REPORTING.md](REPORTING.md)** | Interpret test reports and understand performance metrics |

## Features

✅ **Modular Architecture** — Separated concerns with API layer, tasks, config, and utilities  
✅ **API Abstraction** — Clean wrapper classes for API endpoints with error handling  
✅ **Configurable Test Data** — CSV-based user data loading for parameterized tests  
✅ **Flexible Task System** — Task weights and tags for complex test scenarios  
✅ **Performance Metrics** — Track p95, p99, average response time, and failure rates  
✅ **SLA Validation** — Automatic threshold checking and test failure on SLA breach  
✅ **Comprehensive Reporting** — HTML reports, CSV exports, and exception tracking  
✅ **Timestamped Reports** — Organized test results with automatic directory creation  
✅ **Environment-Driven** — Support for multiple environments via configuration  

## Running Your First Test

### 1. Update Test Credentials (Optional)

Edit `test_data/users.csv` to add your test user credentials:

```csv
username,password
testuser1,password123
testuser2,password456
```

### 2. Configure Base URL

Edit `config/config.py`:

```python
BASE_URL = "https://your-api-server.com"
```

### 3. Set Performance Thresholds (Optional)

Before running, you can set environment variables for SLA thresholds:

```bash
export MAX_AVG_RESPONSE_TIME=500    # milliseconds
export MAX_P95_RESPONSE_TIME=1000   # milliseconds
export MAX_FAILURE_RATE=5           # percentage
```

### 4. Run the Test

```bash
poetry run python run_performance.py
```

The test will:
1. Load test data from `test_data/users.csv`
2. Spawn 5 virtual users (default configuration)
3. Run for 30 seconds
4. Generate reports in `reports/<timestamp>/`
5. Validate against performance thresholds
6. Exit with code 0 (success) or 1 (failure)

### 5. View Results

Open the generated HTML report:

```bash
open reports/<latest-timestamp>/report.html
```

## Example Output

```
Running Locust with reports in: reports/2026-03-01_16-44-40
...
Avg: 245.5 ms
P95: 892.3 ms
Failure rate: 2.1 %

Performance thresholds satisfied ✅
```

If thresholds are exceeded:

```
Average response time too high: 245.5 > 100
P95 response time too high: 892.3 > 500
Failure rate too high: 2.1% > 1%

Performance thresholds violated
```

## Next Steps

1. **Understand the Architecture** → Read [ARCHITECTURE.md](ARCHITECTURE.md)
2. **Explore API Testing** → Read [API_TESTING.md](API_TESTING.md) and modify `api/` directory
3. **Create Test Scenarios** → Read [TASKS_AND_SCENARIOS.md](TASKS_AND_SCENARIOS.md)
4. **Configure Environments** → Read [CONFIG_AND_ENVIRONMENTS.md](CONFIG_AND_ENVIRONMENTS.md)
5. **Run Advanced Tests** → Read [RUNNING_TESTS.md](RUNNING_TESTS.md)
6. **Analyze Results** → Read [REPORTING.md](REPORTING.md)

## Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'locust'"

**Solution:** Ensure you're running commands with `poetry run`:
```bash
poetry run python run_performance.py
```

Or activate the poetry environment:
```bash
poetry shell
python run_performance.py
```

### Issue: "Connection refused" or "Unable to connect to host"

**Solution:** Verify your target API is running and the BASE_URL in `config/config.py` is correct.

### Issue: "Login failed" errors

**Solution:** Check that test credentials in `test_data/users.csv` are valid for your target environment.

### Issue: "Performance thresholds violated"

**Solution:** This is expected for the first baseline run. Either:
- Adjust thresholds in environment variables to match actual performance
- Optimize the target application
- Increase test duration to see if performance stabilizes

### Issue: Reports not generating

**Solution:** Ensure the `reports/` directory exists (it should be auto-created). Check file permissions.

## Support & Contributions

For questions or improvements to this framework:
1. Review the documentation in this folder
2. Check code comments in each module
3. Refer to [Locust Official Documentation](https://docs.locust.io/)

## License

This framework is provided as-is for performance testing purposes.

---

**Ready to dive in?** Start with [ARCHITECTURE.md](ARCHITECTURE.md) to understand how everything fits together.

