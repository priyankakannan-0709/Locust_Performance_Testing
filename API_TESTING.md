# API Testing Guide

This document explains how the API abstraction layer works, how to use existing APIs, and how to add new endpoints.

## Overview

The API abstraction layer encapsulates all HTTP interactions with the target API. This design:
- ✅ Separates test logic from HTTP details
- ✅ Enables easy endpoint refactoring
- ✅ Centralizes authentication handling
- ✅ Improves test readability and maintainability

### Architecture

```
Task (tasks/user_behavior.py)
    ↓
API Class (api/auth_api.py, api/user_api.py)
    ↓
Locust HttpClient
    ↓
Target API
```

## Current API Endpoints



### Common HTTP Status Codes

| Code | Meaning | Handling |
|------|---------|----------|
| 200 | OK | Success - expected response |
| 201 | Created | Success - resource created |
| 204 | No Content | Success - no response body |
| 400 | Bad Request | Failure - check request payload |
| 401 | Unauthorized | Failure - check authentication token |
| 403 | Forbidden | Failure - insufficient permissions |
| 404 | Not Found | Failure - resource doesn't exist |
| 500 | Internal Error | Failure - server error (worth noting) |
| 503 | Unavailable | Failure - service down |

---


```python
BASE_URL = "https://your-api.com"
```

---

For more details, see:
- [ARCHITECTURE.md](ARCHITECTURE.md) — Overall design patterns

