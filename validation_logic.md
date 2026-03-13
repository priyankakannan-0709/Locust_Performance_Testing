# Performance Framework — Implementation Spec

## Baseline File Management

On every run, `run_performance.py` checks for `baselineResults.json` in the framework root.

---

### If File Does NOT Exist (First Run)

- Set `comparison_flag = False`
- Run the test **3 times** (configurable via `baseline_runs` in config), average all captured metrics across runs
- Write averaged results to `baselineResults.json` with metadata:
  - `baseline_created_at` — ISO timestamp of capture
  - `baseline_runs_averaged` — number of runs averaged
- Skip comparison and reporting entirely — just store the baseline

---

### If File EXISTS

- Set `comparison_flag = True`
- Run Locust as a single run
- Compare current results against `baselineResults.json`
- Archive current results to `/baseline_history/` as `baseline_YYYY-MM-DDTHH-MM-SS.json`
- Proceed to deviation reporting

---

### Additional Behaviors

- Support a `--reset-baseline` CLI flag that deletes `baselineResults.json` and triggers a fresh first-run cycle
- Support a `--clean-baseline` CLI flag that prunes APIs from `baselineResults.json` not present in the last run (for deliberate removal of stale APIs)
- Log a warning if `baseline_created_at` is older than **30 days** (threshold configurable)

---

## SLA Tier System

Define a `complexity` field at the **API definition level** — not in any external config file. This keeps the SLA contract co-located with the API itself.

| Tier | Buffer Applied |
|------|---------------|
| `small` | 5% |
| `medium` | 10% |
| `complex` | 12% |

The buffer applies to **every metric returned by Locust** — `avg`, `p50`, `p75`, `p90`, `p95`, `p99`, `min`, `max`, `RPS`, `failure_rate`, and any others.

> Do not hardcode which metrics to compare. Iterate over all keys present in the results dict so any new metrics Locust returns in future are automatically included.

---

## Comparison Logic

When `comparison_flag = True`, for each API and for each metric:

1. Calculate the allowed threshold:
   ```
   threshold = baseline_value × (1 + complexity_buffer)
   ```

2. Calculate deviation %:
   ```
   deviation_pct = ((current_value - baseline_value) / baseline_value) × 100
   ```

3. Evaluate:
   - If `current_value > threshold` → mark as **BREACH** — highlight in report
   - If `current_value ≤ threshold` → mark as **PASS**

> A single breach in **any one metric** for any one API flags that API in the report.  
> The pipeline does **not** hard stop on breach — execution completes fully and the report surfaces all deviations for visibility.

---

## Edge Case Handling

### NEW_API — Present in current run, missing from baseline

- Do **not** overwrite `baselineResults.json` entirely
- Run the new API **3 times** (same `baseline_runs` config), average its metrics
- Surgically **append** only the new API's averaged result into the existing `baselineResults.json`
- Log as: `NEW_API — baseline captured and merged into baselineResults.json`
- In the report, mark this API as `NEW_BASELINE_CAPTURED` — no comparison done for this run

### REMOVED_API — Present in baseline, missing from current run

- Leave it **untouched** inside `baselineResults.json` — do not purge it automatically
- Log as: `REMOVED_API — retained in baseline for historical reference`
- Surface it as a **warning** in the report so the team can consciously decide to remove it
- Only remove it from baseline via the deliberate `--clean-baseline` CLI flag

### `comparison_flag = False` — No baseline exists

- Skip comparison entirely
- After baseline is written, any APIs discovered in future runs follow the **NEW_API merge logic** above
- The full re-capture only ever happens **once** — on the very first run or after `--reset-baseline`

---

## Reporting

The final report must clearly distinguish the run type and surface results accordingly.

### For Baseline Capture Runs
- State that this was a **baseline capture run**
- Show the number of runs averaged and the timestamp written to `baselineResults.json`
- No comparison table shown

### For Comparison Runs

**Per-API, Per-Metric Table:**

| API Name | Metric | Baseline Value | Current Value | Deviation % | Threshold | Status |
|----------|--------|---------------|---------------|-------------|-----------|--------|
| GetUserAPI | avg | 120ms | 128ms | +6.7% | 126ms (5%) | ✅ PASS |
| GenerateReportAPI | p95 | 800ms | 950ms | +18.75% | 896ms (12%) | 🔴 BREACH |

### Sample SLA result

{
  "post /auth/login": {
    "Average Response Time": { "status": "PASS", ... },
    "95%":                   { "status": "BREACH", ... },
    "_api_status":           "BREACH"
  },
  "post /users/export": {
    "_api_status": "NEW_BASELINE_CAPTURED"
  },
  "delete /users/:id": {
    "_api_status":  "REMOVED_API",
    "_reason":      "Present in baseline, not found in current run"
  }
}

**Summary Section:**

A consolidated list of all APIs with at least one BREACH, grouped for quick visibility:

```
⚠️  BREACH SUMMARY
──────────────────────────────────
GenerateReportAPI   →  p95 exceeded threshold by +6.75%
SearchProductsAPI   →  avg, p99 exceeded threshold
──────────────────────────────────
Total APIs breached: 2 / 8
```

**Special Status Markers:**

| Marker | Meaning |
|--------|---------|
| ✅ PASS | Within SLA threshold |
| 🔴 BREACH | Exceeded SLA threshold |
| 🆕 NEW_BASELINE_CAPTURED | New API — baseline merged, no comparison this run |
| ⚠️ REMOVED_API | In baseline but absent from current run |
