# Architecture & Design

This document explains the architectural design of the Locust Performance Testing Framework, including component responsibilities, data flow, and design patterns used.

## Table of Contents

- [System Overview](#system-overview)
- [Component Architecture](#component-architecture)
- [Design Patterns](#design-patterns)
- [Module Responsibilities](#module-responsibilities)
- [Extension Points](#extension-points)

## System Overview

The framework follows a **layered architecture** with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────┐
│                   Test Execution Layer                   │
│              (run_performance.py, locustfile.py)         │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│              Task & Scenario Layer                       │
│          (tasks/user_behavior.py)                        │
│    - Defines user journeys                              │
│    - Task weights and order                             │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│              API Abstraction Layer                       │
│          (api/auth_api.py, api/user_api.py)            │
│    - Encapsulates HTTP interactions                     │
│    - Payload construction                               │
│    - Error handling                                     │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│         Configuration & Utilities Layer                  │
│    - config/: Environment configuration                 │
│    - utils/: Data loading & reporting                   │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│           Locust HTTP Client (External)                  │
│    - HTTP communication with target API                 │
└─────────────────────────────────────────────────────────┘
```

## Component Architecture

### 1. **Entry Point Layer** (`run_performance.py`, `locustfile.py`)

**Responsibility:** Orchestrate test execution and SLA validation

| Component | Purpose |
|-----------|---------|
| `run_performance.py` | Orchestrates test execution, collects metrics, validates SLAs |
| `locustfile.py` | Defines Locust HttpUser class and links to task definitions |

**Key Characteristics:**
- Reads environment variables for thresholds
- Invokes Locust via subprocess with configured parameters
- Parses CSV reports and validates performance metrics
- Returns appropriate exit codes for CI/CD integration

### 2. **Task & Scenario Layer** (`tasks/`)

**Responsibility:** Define user behavior and test scenarios

| Component | Purpose |
|-----------|---------|
| `user_behavior.py` | TaskSet defining simulated user actions |

**Key Characteristics:**
- `on_start()`: Initialization per user (login, setup)
- `@task` decorated methods: Actions performed during test
- Task weights: Control frequency of task execution
- Tags: Mark tasks for selective execution

### 3. **API Abstraction Layer** (`api/`)

**Responsibility:** Encapsulate all HTTP interactions with the target API

| Component | Purpose |
|-----------|---------|
| `auth_api.py` | Authentication endpoint wrapper |
| `user_api.py` | User operations endpoint wrapper |

**Key Characteristics:**
- Class-based wrappers around HTTP methods
- Payload construction and validation
- Consistent error handling with `catch_response=True`
- Authorization header management

**Why This Layer Exists:**
- Decouples test logic from HTTP details
- Enables easy endpoint refactoring
- Centralizes authentication/authorization handling
- Improves test readability

### 4. **Configuration Layer** (`config/`)

**Responsibility:** Manage environment-specific settings

| Component | Purpose |
|-----------|---------|
| `config.py` | Base URLs and configuration constants |

**Key Characteristics:**
- Single source of truth for target API URL
- Environment-specific overrides via environment variables
- Extensible for additional settings (timeouts, retries, etc.)

### 5. **Utilities Layer** (`utils/`)

**Responsibility:** Provide reusable helper functions

| Component | Purpose |
|-----------|---------|
| `data_loader.py` | Load test data from CSV files |
| `report_manager.py` | Manage report directories and file paths |

**Key Characteristics:**
- Stateless utility functions
- Single responsibility per module
- Extensible for future utilities

## Design Patterns

### 1. **API Wrapper Pattern**

Each API endpoint or logical grouping is wrapped in a class:

```python
class AuthAPI:
    def __init__(self, client):
        self.client = client
    
    def login(self, username, password):
        # Encapsulates HTTP details, payload construction
        return self.client.post(...)
```

**Benefits:**
- ✅ Decouples test logic from HTTP implementation
- ✅ Centralizes endpoint versioning
- ✅ Enables easy mocking for unit tests
- ✅ Improves code reusability

### 2. **Task Set Pattern**

TaskSet classes define user behavior with decorated task methods:

```python
class UserBehavior(TaskSet):
    def on_start(self):
        # Per-user initialization
        pass
    
    @task(weight)
    def action_name(self):
        # Task executed repeatedly
        pass
```

**Benefits:**
- ✅ Clean syntax for behavior definition
- ✅ Task weights control execution frequency
- ✅ Tags enable selective execution
- ✅ Lifecycle hooks (on_start, on_stop)

### 3. **Configuration Management Pattern**

Centralized config with environment variable overrides:

```python
BASE_URL = os.getenv("BASE_URL", "https://default.com")
```

**Benefits:**
- ✅ Environment-agnostic code
- ✅ Easy multi-environment support
- ✅ Secrets can be injected at runtime
- ✅ Single source of truth

### 4. **Utility Module Pattern**

Pure functions for data loading and path management:

```python
def load_users(file_path):
    # Stateless function
    return data

def create_report_directory():
    # Returns Path object for flexibility
    return report_path
```

**Benefits:**
- ✅ Highly reusable across projects
- ✅ Easy to unit test
- ✅ No side effects or hidden state
- ✅ Simple to extend

## Module Responsibilities

| Module | Responsibility | Concern Level |
|--------|---------------|----|
| `run_performance.py` | Test orchestration, SLA validation | High-level |
| `locustfile.py` | HttpUser configuration, task binding | High-level |
| `tasks/user_behavior.py` | User behavior definition | Medium |
| `api/*.py` | HTTP interaction encapsulation | Medium |
| `config/config.py` | Environment configuration | Low |
| `utils/data_loader.py` | Test data loading | Low |
| `utils/report_manager.py` | Report path management | Low |

**Dependency Direction (top = depends on bottom):**
```
run_performance.py
    ↓
locustfile.py
    ↓
tasks/user_behavior.py
    ↓
api/ + config/ + utils/
```

For more details on specific components, see:
- [API_TESTING.md](API_TESTING.md) — API layer deep dive

