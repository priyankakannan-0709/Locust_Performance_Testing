from datetime import datetime, timezone
import json
from pathlib import Path
from config.config import BASELINE_STALE_DAYS
from utils.logger import get_logger
logger = get_logger(__name__)

BASE_DIR = Path(__file__).parent.parent
BASELINE_FILE = BASE_DIR / "baselineResults.json"

def get_project_root():
    """Return the framework root directory (where run_performance.py is located)."""
    return Path(__file__).parent.parent

def get_baseline_path():
    """Return the path to baselineResults.json in the framework root."""
    return get_project_root() / "baselineResults.json"

def load_baseline() -> dict:
    """
    Load baselineResults.json from the framework root.
    Returns the full baseline dict including metadata and results.
    """
    """Load baseline results from baselineResults.json.

        Returns:
            dict: Baseline data with all APIs and metadata, or None if file doesn't exist or loading fails
        """
    baseline_path = get_baseline_path()

    if not baseline_path.exists():
        logger.warning(f"⚠️  Baseline file not found: {baseline_path}")
        return None

    try:
        with open(baseline_path, "r") as f:
            baseline_data = json.load(f)

        logger.info(f"✅ Baseline loaded from {baseline_path}")
        apis_in_baseline = len(
            [k for k in baseline_data.keys() if k not in ('baseline_created_at', 'baseline_runs_averaged')])
        logger.info(f"   - APIs in baseline: {apis_in_baseline}")
        logger.info(f"   - Created at: {baseline_data.get('baseline_created_at', 'N/A')}")

        return baseline_data
    except Exception as e:
        logger.error(f"❌ Error loading baseline: {e}")
        return None


def get_normalised_keys(results: dict) -> dict:
    """
    Return a new dict with all endpoint keys normalised.
    Original keys are replaced — values are preserved as-is.

    Args:
        results: raw results dict keyed by endpoint path

    Returns:
        dict with normalised endpoint keys
    """
    return {normalise_endpoint(k): v for k, v in results.items()}


def normalise_endpoint(endpoint: str) -> str:
    """
    Normalise endpoint path for consistent matching.
    Strips trailing slashes and lowercases.

    Examples:
        "/users/"   -> "/users"
        "/Auth/Me"  -> "/auth/me"
        "/users"    -> "/users"
    """
    return endpoint.rstrip("/").lower()

def identify_api_changes(current_results: dict, baseline_data: dict) -> dict:
    """
    Compare current result keys against baseline keys to identify
    new and removed APIs.

    Args:
        current_results: Parsed stats from current Locust run
        baseline_data:   Loaded baselineResults.json dict

    Returns:
        dict: {
            "new_apis":     set of endpoints in current but missing from baseline,
            "removed_apis": set of endpoints in baseline but missing from current,
            "common_apis":  set of endpoints present in both
        }
    """
    # Metadata keys that are not API entries — exclude from comparison
    METADATA_KEYS = {"baseline_created_at", "baseline_runs_averaged"}

    # Normalise both sides
    normalised_current  = set(normalise_endpoint(k) for k in current_results.keys())
    normalised_baseline = set(
        normalise_endpoint(k)
        for k in baseline_data.keys()
        if k not in METADATA_KEYS
    )

    new_apis     = normalised_current - normalised_baseline
    removed_apis = normalised_baseline - normalised_current
    common_apis  = normalised_current & normalised_baseline

    # Log findings
    if new_apis:
        for api in new_apis:
            logger.info(f"🆕  NEW_API detected: {api} — not found in baseline")

    if removed_apis:
        for api in removed_apis:
            logger.warning(f"⚠️  REMOVED_API detected: {api} — present in baseline, missing from current run")

    if common_apis:
        logger.info(f"✅  {len(common_apis)} API(s) matched between current run and baseline")

    return {
        "new_apis":     new_apis,
        "removed_apis": removed_apis,
        "common_apis":  common_apis
    }

def merge_new_api_baseline(api_name: str, current_metrics: dict, baseline_data: dict) -> dict:

    baseline_path = get_baseline_path()

    # ✅ Store flat — same format as save_baseline()
    numeric_metrics = {
        k: v for k, v in current_metrics.items()
        if isinstance(v, (int, float)) and k not in ("Type", "Name")
    }

    # ── Flat storage — no nested "metrics" key ─────────────────────────────
    baseline_data[api_name] = numeric_metrics  # ← flat, not {"metrics": ...}

    try:
        with open(baseline_path, "w") as f:
            json.dump(baseline_data, f, indent=2)
        logger.info(f"✅  NEW_API {api_name} — baseline merged into baselineResults.json")
    except Exception as e:
        logger.error(f"❌  Failed to merge baseline for {api_name}: {e}")

    return baseline_data



def archive_run_to_history(current_results: dict, sla_results: dict, comparison_flag: bool) -> Path:
    """
    Save a combined snapshot of the current run to /baseline_history/.
    Called after every comparison run completes.

    Args:
        current_results: Raw parsed metrics from parse_locust_stats()
        sla_results:     Enriched comparison output with PASS/BREACH evaluations
        comparison_flag: True if this was a comparison run

    Returns:
        Path to the archived file
    """
    history_dir = BASE_DIR / "baseline_history"
    history_dir.mkdir(exist_ok=True)

    timestamp     = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")
    archive_path  = history_dir / f"baseline_{timestamp}.json"

    snapshot = {
        "archived_at":      datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "comparison_flag":  comparison_flag,
        "raw_results":      current_results,
        "sla_evaluation":   sla_results,
    }

    try:
        with open(archive_path, "w") as f:
            json.dump(snapshot, f, indent=2)
        logger.info(f"📁  Run archived to: {archive_path}")
    except Exception as e:
        logger.error(f"❌  Failed to archive run history: {e}")

    return archive_path


def check_baseline_staleness(baseline_data: dict) -> None:
    """
    Warn if baselineResults.json is older than BASELINE_STALE_DAYS.
    Does not block execution — warning only.

    Args:
        baseline_data: Already loaded baseline dict containing baseline_created_at
    """
    created_at_str = baseline_data.get("baseline_created_at")

    if not created_at_str:
        logger.info("⚠️  baseline_created_at not found in baseline — skipping staleness check")
        return

    try:
        created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
        age_days   = (datetime.now(timezone.utc) - created_at).days

        if age_days > BASELINE_STALE_DAYS:
            logger.warning(f"⚠️  BASELINE STALE WARNING — baseline was created {age_days} days ago "
                  f"(threshold: {BASELINE_STALE_DAYS} days). "
                  f"Consider running --reset-baseline to capture a fresh one.")
        else:
            logger.info(f"✅  Baseline age: {age_days} day(s) — within {BASELINE_STALE_DAYS} day threshold")

    except Exception as e:
        logger.error(f"❌  Failed to parse baseline_created_at: {e}")