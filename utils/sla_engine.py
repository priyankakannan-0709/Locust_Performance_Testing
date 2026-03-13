import json
from datetime import datetime, timezone
from utils.comparison_engine import get_baseline_path, load_baseline, identify_api_changes, get_normalised_keys, \
    merge_new_api_baseline, archive_run_to_history, check_baseline_staleness
from utils.get_api_complexity import get_api_complexity
from utils.profile_loader import load_all_profiles
from utils.logger import get_logger
logger = get_logger(__name__)

def build_sla_overrides() -> dict:
    """
    Build SLA override lookup from all profile configs.
    Each profile's expected_sla metrics are registered under
    its own profile_name based key — independent per profile.

    Returns:
        dict: {
            "POST /upload/{profile_name}": {
                "metric_name": threshold_value,
                ...
            }
        }
        sample output: {
    "post /upload/priyanka":  { "Max Response Time": 3000 },
    "post /upload/priyanshi": { "Max Response Time": 5000 }
}
    """
    profiles     = load_all_profiles()
    sla_overrides = {}

    for profile in profiles:
        profile_name = profile.get("profile_name")
        expected_sla = profile.get("expected_sla", {})

        if not profile_name:
            logger.warning(f"⚠️   Profile missing profile_name — skipping SLA override")
            continue

        if not expected_sla:
            logger.warning(f"⚠️   No expected_sla defined in profile: {profile_name}")
            continue

        # Register all metrics under this profile's CSV key
        api_key = f"post /upload/{profile_name.lower()}"
        sla_overrides[api_key] = {}

        for metric_name, threshold in expected_sla.items():
            sla_overrides[api_key][metric_name] = threshold
            logger.info(f"📋  SLA override registered — "
                  f"{api_key} | {metric_name}: {threshold}")


    return sla_overrides

def run_sla_evaluation(api_changes, current_results, baseline_data, sla_overrides):
    '''
    run_sla_evaluation()
        │
        ├── build_sla_overrides()
        │       reads all profile YAMLs
        │       builds { "post /upload/priyanka": { "Max Response Time": 3000 } }
        │
        └── for each API in common_apis:
                for each metric:
                        │
                  metric in sla_overrides?
                        │
               ┌────────┴────────┐
              YES                NO
               │                  │
        CONFIG_SLA path     BASELINE path
               │                  │
        threshold =         threshold =
        config value        baseline * (1 + buffer)
               │                  │
        deviation vs        deviation vs
        config threshold    baseline value
               │                  │
        source =            source =
        "CONFIG_SLA"        "BASELINE"
               │                  │
               └────────┬─────────┘
                        │
                  PASS or BREACH
                  written to sla_results
                  shown in report
    '''
    logger.info("\n📊 Evaluating SLA for all APIs...\n")

    # safe to compare — baseline entry guaranteed to exist
    sla_results = {}
    for api_name in api_changes["common_apis"]:
        '''
        Runs through each API,
        If the API present in both baseline and current :
        Check if the metric defined in sla_overrides, If yes,
                Make source = config_SLA
                Mark the baseline value to N/A , which means ignore this while comparing
            else
                Make source = baseline
        '''
        logger.debug(f"DEBUG sla_overrides keys : {list(sla_overrides.keys())}")
        logger.debug(f"DEBUG common_apis keys   : {list(api_changes['common_apis'])}")

        logger.info("\n📊 Evaluating SLA for all APIs...\n")
        logger.info(f"Processing API: {api_name}")

        complexity = get_api_complexity(api_name)
        sla_results[api_name] = {}

        current_metrics = get_normalised_keys(current_results).get(api_name, {})
        baseline_metrics = get_normalised_keys(baseline_data).get(api_name, {})

        for metric_name, current_value in current_metrics.items():

            # Skip non-metric fields
            if metric_name in ("Type", "Name"):
                continue

            # Skip non-numeric values
            if not isinstance(current_value, (int, float)):
                continue

            # ── Config SLA override path ───────────────────────────────────
            if api_name in sla_overrides and \
                    metric_name in sla_overrides[api_name]:

                config_threshold = sla_overrides[api_name][metric_name]
                deviation_pct = (
                    ((current_value - config_threshold) / config_threshold) * 100
                    if config_threshold != 0 else 0
                )
                status = "BREACH" if current_value > config_threshold else "PASS"

                sla_results[api_name][metric_name] = {
                    "baseline_value": "N/A",  # not used in config SLA path
                    "current_value": current_value,
                    "deviation_pct": round(deviation_pct, 2),
                    "threshold": config_threshold,
                    "status": status,
                    "comparison_source": "CONFIG_SLA"
                }

                status_symbol = "✅" if status == "PASS" else "🔴"
                logger.info(f"  [{metric_name}] {status_symbol} {status} "
                      f"| config_threshold={config_threshold} "
                      f"| current={current_value} "
                      f"| deviation={round(deviation_pct, 2)}% "
                      f"| source=CONFIG_SLA")

            # ── Baseline comparison path ───────────────────────────────────
            else:
                baseline_value = baseline_metrics.get(metric_name, 0)
                evaluation = evaluate_sla(
                    metric_name, baseline_value, current_value, complexity
                )
                evaluation["comparison_source"] = "BASELINE"
                sla_results[api_name][metric_name] = evaluation

                status_symbol = "✅" if evaluation["status"] == "PASS" else "🔴"
                logger.info(f"  [{metric_name}] {status_symbol} {evaluation['status']} "
                      f"| baseline={baseline_value} "
                      f"| current={current_value} "
                      f"| deviation={evaluation['deviation_pct']}% "
                      f"| source=BASELINE")

        # Flag API-level status
        api_status = "BREACH" if any(
            m["status"] == "BREACH"
            for k, m in sla_results[api_name].items()
            if not k.startswith("_")
        ) else "PASS"

        logger.info(f"  → API overall: "
              f"{'🔴 BREACH' if api_status == 'BREACH' else '✅ PASS'}\n")
        sla_results[api_name]["_api_status"] = api_status

    # STEP 3 — handle new APIs separately
    # ── NEW_APIs — capture and merge into baseline ─────────────────────────────
    logger.info("\n📊 Processing NEW APIs...\n") if api_changes["new_apis"] else None
    for api_name in api_changes["new_apis"]:
        # capture baseline, merge into baselineResults.json
        logger.info(f"🆕  NEW_API: {api_name} — no baseline entry found")

        current_metrics = get_normalised_keys(current_results).get(api_name, {})

        if not current_metrics:
            logger.warning(f"⚠️  No metrics found for {api_name}, skipping merge")
            sla_results[api_name] = {"_api_status": "NEW_BASELINE_SKIPPED"}
            continue

        # Merge into baseline
        baseline_data = merge_new_api_baseline(api_name, current_metrics, baseline_data)

        # Mark in sla_results — no comparison done this run
        sla_results[api_name] = {"_api_status": "NEW_BASELINE_CAPTURED"}
        logger.info(f"  → Marked as NEW_BASELINE_CAPTURED in report\n")

    # STEP 4 — handle removed APIs separately
    logger.info("\n📊 Processing REMOVED APIs...\n") if api_changes["removed_apis"] else None
    for api_name in api_changes["removed_apis"]:
        logger.warning(f"⚠️  REMOVED_API: {api_name} — present in baseline, not found in current run")
        logger.info(f"   Retained in baselineResults.json for historical reference")

        # Surface in sla_results for report visibility
        sla_results[api_name] = {
            "_api_status": "REMOVED_API",
            "_reason": "Present in baseline, not found in current run"
        }

    return sla_results

def evaluate_sla(metric_name, baseline_value, current_value, complexity):
    """Evaluate SLA for a single metric.

    Args:
        metric_name: Name of the metric (e.g., "Average Response Time", "Requests/s")
        baseline_value: Value from baseline
        current_value: Value from current run
        complexity: Complexity level ("small", "medium", "complex")

    Returns:
        dict: {baseline_value, current_value, deviation_pct, threshold, status}
    """
    # Buffer mapping based on complexity
    complexity_buffers = {
        "small": 0.05,      # 5%
        "medium": 0.10,     # 10%
        "complex": 0.12     # 12%
    }

    buffer = complexity_buffers.get(complexity, 0.10)

    # Handle zero baseline
    if baseline_value == 0:
        if current_value == 0:
            status = "PASS"
            deviation_pct = 0
            threshold = 0
        else:
            status = "BREACH"
            deviation_pct = 100 if current_value > 0 else -100
            threshold = 0
    else:
        # Calculate threshold and deviation
        threshold = baseline_value * (1 + buffer)
        deviation_pct = ((current_value - baseline_value) / baseline_value) * 100

        # RPS metric has inverted logic (lower is worse)
        if metric_name == "Requests/s":
            status = "BREACH" if current_value < threshold else "PASS"
        else:
            status = "BREACH" if current_value > threshold else "PASS"

    return {
        "baseline_value": baseline_value,
        "current_value": current_value,
        "deviation_pct": round(deviation_pct, 2),
        "threshold": round(threshold, 2) if threshold else 0,
        "status": status
    }

def aggregate_results(list_of_results):
    """Aggregate and average metrics across multiple runs.

    Args:
        list_of_results: List of result dicts from parse_locust_stats()

    Returns:
        dict: Averaged results with structure {api_name: {metric_name: avg_value, ...}}
    """
    if not list_of_results:
        return {}

    # Collect all APIs across all runs
    all_apis = set()
    for results in list_of_results:
        if results:
            all_apis.update(results.keys())

    aggregated = {}

    for api_name in all_apis:
        # Collect all metrics for this API across runs
        metrics_by_name = {}
        run_count = 0

        for results in list_of_results:
            if results and api_name in results:
                run_count += 1
                api_metrics = results[api_name]

                for metric_name, value in api_metrics.items():
                    if metric_name not in metrics_by_name:
                        metrics_by_name[metric_name] = []

                    # Only aggregate numeric values
                    if isinstance(value, (int, float)):
                        metrics_by_name[metric_name].append(value)
                    else:
                        # For non-numeric values (Type, Name), just use the first one
                        if metric_name not in metrics_by_name or not metrics_by_name[metric_name]:
                            metrics_by_name[metric_name] = value

        # Average numeric metrics, keep non-numeric as-is
        averaged_metrics = {}
        for metric_name, values in metrics_by_name.items():
            if isinstance(values, list):
                # Numeric values - calculate average
                averaged_metrics[metric_name] = sum(values) / len(values)
            else:
                # Non-numeric values
                averaged_metrics[metric_name] = values

        aggregated[api_name] = averaged_metrics

    return aggregated


def save_baseline(averaged_results, runs_count):
    """Save averaged baseline results to baselineResults.json.

    Args:
        averaged_results: Dict of averaged metrics per API
        runs_count: Number of runs that were averaged

    Returns:
        bool: True if saved successfully, False otherwise
    """
    baseline_path = get_baseline_path()

    # Prepare baseline data with metadata
    baseline_data = {
        **averaged_results,
        "baseline_created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "baseline_runs_averaged": runs_count
    }

    try:
        with open(baseline_path, "w") as f:
            json.dump(baseline_data, f, indent=2)

        logger.info(f"\n✅ Baseline saved successfully to {baseline_path}")
        logger.info(f"   - APIs captured: {len(averaged_results)}")
        logger.info(f"   - Runs averaged: {runs_count}")
        logger.info(f"   - Timestamp: {baseline_data['baseline_created_at']}")

        return True
    except Exception as e:
        logger.info(f"❌ Error saving baseline: {e}")
        return False