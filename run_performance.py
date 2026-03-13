import sys
import csv
import subprocess
import argparse
import json
import os
from datetime import datetime, timezone

from utils.logger            import setup_logger, get_logger
from utils.comparison_engine import load_baseline, get_baseline_path, identify_api_changes, get_normalised_keys, \
    merge_new_api_baseline, archive_run_to_history, check_baseline_staleness
from utils.config_validator  import validate_study_pool, validate_test_data_files, validate_for_mode
from utils.profile_loader    import load_all_profiles
from utils.report_manager    import create_report_directory, get_report_file_prefix, generate_report, generate_page_report
from utils.sla_engine        import build_sla_overrides, run_sla_evaluation, aggregate_results, \
    save_baseline

# ── Module-level logger — assigned after setup_logger() is called ──────────
logger = None


def parse_input_args():
    parser = argparse.ArgumentParser()
    parser = argparse.ArgumentParser(description="Run Locust performance tests with baseline comparison.")
    parser.add_argument("--reset-baseline", action="store_true",
                        help="Delete the current baseline and trigger a fresh baseline capture on next run.")
    parser.add_argument("--clean-baseline", action="store_true",
                        help="Prune APIs from baseline not present in the last run.")
    parser.add_argument("--users", type=int, default=3, help="Number of users")
    parser.add_argument("--spawn-rate", type=int, default=2, help="Spawn rate")
    parser.add_argument("--run-time", type=str, default="20s", help="Run time")
    parser.add_argument("--mode", type=str, choices=["journey", "stress"], default="journey",
                        help="Test mode: 'journey' for user simulation, 'stress' for file size stress testing")
    return parser.parse_args()


def parse_locust_stats(report_dir):
    """Parse all metrics from report_stats.csv and return per-API results.

    Args:
        report_dir: Path to the report directory containing report_stats.csv

    Returns:
        dict: {api_name: {metric_name: value, ...}} or None if parsing fails
    """
    stats_file = report_dir / "report_stats.csv"

    if not stats_file.exists():
        logger.warning(f"Stats file not found: {stats_file}")
        return None

    logger.info(f"Reading stats from: {stats_file}")

    results = {}
    try:
        with open(stats_file, newline="") as csvfile:
            reader = csv.DictReader(csvfile)

            for row in reader:
                api_name = row.get("Name", "").strip()

                # Skip empty names and "Aggregated" row
                if not api_name or api_name == "Aggregated":
                    continue

                # Convert all numeric values to float, keep others as-is
                api_metrics = {}
                for key, value in row.items():
                    if key in ("Type", "Name"):
                        api_metrics[key] = value
                    else:
                        try:
                            api_metrics[key] = float(value)
                        except (ValueError, TypeError):
                            api_metrics[key] = value

                results[api_name] = api_metrics

        logger.debug(f"Parsed {len(results)} API entries from stats CSV")
        return results if results else None

    except Exception as e:
        logger.error(f"Error parsing stats: {e}")
        return None


def run_locust(c_flag, users, spawn_rate, run_time, mode, report_dir):
    """
    Run Locust as a subprocess.

    NOTE: report_dir is now passed in (created before logger init in __main__)
    rather than created here, so all output lands in the same timestamped directory.
    """
    html_report_path = report_dir / "report.html"
    csv_prefix       = get_report_file_prefix(report_dir)

    env                = os.environ.copy()
    env["LOCUST_MODE"] = mode

    if c_flag:
        command = [
            "locust",
            "-f", "locustfile.py",
            "--headless",
            "--users",      str(users),
            "--spawn-rate", str(spawn_rate),
            "--html",       str(html_report_path),
            "--csv",        csv_prefix,
        ]
    else:
        command = [
            "locust",
            "-f", "locustfile.py",
            "--headless",
            "--users",      str(users),
            "--spawn-rate", str(spawn_rate),
            "--run-time",   str(run_time),
            "--html",       str(html_report_path),
            "--csv",        csv_prefix,
        ]

    logger.info(f"Running Locust in '{mode}' mode")
    logger.info(f"Report directory: {report_dir}")
    logger.debug(f"Locust command: {' '.join(command)}")

    subprocess.run(command, check=True, env=env)

    logger.info("Locust process completed successfully")
    return report_dir


def read_locust_stats(report_dir):
    stats_file = report_dir / "report_stats.csv"
    logger.debug(f"Reading aggregated stats from: {stats_file}")

    with open(stats_file, newline="") as csvfile:
        reader = csv.DictReader(csvfile)

        for row in reader:
            if row["Name"] == "Aggregated":
                avg_response_time = float(row["Average Response Time"])
                p95_response_time = float(row["95%"])
                request_count     = float(row["Request Count"])
                failure_count     = float(row["Failure Count"])

                failure_rate = (
                    0
                    if request_count == 0
                    else (failure_count / request_count) * 100
                )

                logger.debug(
                    f"Aggregated — avg: {avg_response_time}ms | "
                    f"p95: {p95_response_time}ms | "
                    f"failure rate: {failure_rate:.2f}%"
                )
                return avg_response_time, p95_response_time, failure_rate

    raise Exception("Aggregated stats not found in CSV")


if __name__ == "__main__":

    from config.config import BASELINE_RUNS

    # ── Parse CLI arguments ────────────────────────────────────────────────
    input_arguments = parse_input_args()

    # ── Create report directory FIRST — logger writes run.log inside it ───
    report_dir = create_report_directory()

    # ── Initialise logger — must happen before any other logging ──────────
    setup_logger(report_dir)
    logger = get_logger(__name__)

    logger.info(
        f"Performance run starting — "
        f"mode: {input_arguments.mode} | "
        f"users: {input_arguments.users} | "
        f"spawn-rate: {input_arguments.spawn_rate} | "
        f"run-time: {input_arguments.run_time}"
    )

    # ── Stress mode stub ───────────────────────────────────────────────────
    if input_arguments.mode == "stress":
        logger.info("Stress mode selected — implementation pending")
        sys.exit(0)

    # ── Load profiles ──────────────────────────────────────────────────────
    profiles      = load_all_profiles()
    profile_count = len(profiles)
    total_users   = input_arguments.users

    logger.info(
        f"Loaded {profile_count} profile(s): "
        f"{', '.join(p['profile_name'] for p in profiles)}"
    )

    # ── Calculate users per profile ────────────────────────────────────────
    users_per_profile = {
        profile["profile_name"]: total_users // profile_count
        for profile in profiles
    }

    # Handle remainder — first N profiles get one extra user
    remainder = total_users % profile_count
    for i, profile in enumerate(profiles):
        if i < remainder:
            users_per_profile[profile["profile_name"]] += 1

    logger.debug(f"Users per profile: {users_per_profile}")

    if remainder != 0:
        logger.warning(
            f"Users ({total_users}) not evenly divisible by "
            f"profiles ({profile_count}) — "
            f"some profiles will have more users than others"
        )

    # ── Validate configuration ─────────────────────────────────────────────
    logger.info(f"Validating configuration for mode: {input_arguments.mode}")
    validate_for_mode(mode=input_arguments.mode, user_count=input_arguments.users, profiles=profiles)
    logger.info("Configuration validation passed")

    # ── Baseline flag handling ─────────────────────────────────────────────
    if input_arguments.reset_baseline:
        logger.info(
            "--reset-baseline flag detected — "
            "will delete baselineResults.json and trigger fresh baseline capture"
        )

    if input_arguments.clean_baseline:
        logger.info(
            "--clean-baseline flag detected — "
            "will prune removed APIs from baseline"
        )

    # ── Check if baseline exists ───────────────────────────────────────────
    baseline_path   = get_baseline_path()
    comparison_flag = baseline_path.exists()

    logger.info(
        f"Comparison flag: {comparison_flag} — "
        f"running in {'COMPARISON' if comparison_flag else 'BASELINE CAPTURE'} mode"
    )

    # ── COMPARISON MODE ────────────────────────────────────────────────────
    if comparison_flag:
        logger.info(f"Baseline found at {baseline_path}")

        report_dir = run_locust(
            comparison_flag,
            users      = input_arguments.users,
            spawn_rate = input_arguments.spawn_rate,
            run_time   = input_arguments.run_time,
            mode       = input_arguments.mode,
            report_dir = report_dir,
        )

        # ── Load baseline and parse current results ────────────────────────
        baseline_data   = load_baseline()
        current_results = parse_locust_stats(report_dir)

        logger.debug(f"Current results: {current_results}")

        if not baseline_data or not current_results:
            logger.error("Failed to load baseline or parse current results")
            sys.exit(1)

        # ── Identify API changes ───────────────────────────────────────────
        logger.info("Identifying API changes against baseline")
        api_changes = identify_api_changes(current_results, baseline_data)

        # ── SLA evaluation ─────────────────────────────────────────────────
        logger.info("Running SLA evaluation")
        sla_overrides = build_sla_overrides()
        sla_results   = run_sla_evaluation(
            api_changes, current_results, baseline_data, sla_overrides
        )

        # ── Log breach summary ─────────────────────────────────────────────
        breached = [k for k, v in sla_results.items() if v.get("_api_status") == "BREACH"]
        passed   = [k for k, v in sla_results.items() if v.get("_api_status") == "PASS"]
        logger.info(f"SLA evaluation complete — PASS: {len(passed)} | BREACH: {len(breached)}")
        for api in breached:
            logger.warning(f"SLA breach — {api}")

        # ── Generate reports ───────────────────────────────────────────────
        logger.info("Generating performance report")
        generate_report(sla_results, report_dir, comparison_flag)

        logger.info("Generating page report")
        csv_path = report_dir / "report_stats.csv"
        generate_page_report(
            report_dir        = report_dir,
            csv_path          = csv_path,
            users_per_profile = users_per_profile,
            total_users       = total_users,
        )

        archive_run_to_history(current_results, sla_results, comparison_flag)
        check_baseline_staleness(baseline_data)

        logger.info(f"Run complete — reports written to: {report_dir}")

    # ── BASELINE CAPTURE MODE ──────────────────────────────────────────────
    else:
        logger.info(f"No baseline found at {baseline_path}")
        logger.info(
            f"Running in BASELINE CAPTURE mode — "
            f"will run {BASELINE_RUNS} time(s) and average results"
        )

        successful_results = []
        run_num = 1

        logger.info(f"Baseline run {run_num}/{BASELINE_RUNS} starting")
        try:
            report_dir = run_locust(
                comparison_flag,
                users      = input_arguments.users,
                spawn_rate = input_arguments.spawn_rate,
                run_time   = input_arguments.run_time,
                mode       = input_arguments.mode,
                report_dir = report_dir,
            )
            stats = parse_locust_stats(report_dir)

            if stats:
                successful_results.append(stats)
                logger.info(f"Baseline run {run_num} completed — {len(stats)} APIs captured")
            else:
                logger.warning(f"Baseline run {run_num} failed to parse stats — skipping")

        except Exception as e:
            logger.error(f"Baseline run {run_num} failed: {e}")

        if successful_results:
            logger.info(f"Aggregating results from {len(successful_results)} successful run(s)")
            aggregated = aggregate_results(successful_results)
            save_baseline(aggregated, len(successful_results))
            logger.info("Baseline capture complete")
            sys.exit(0)
        else:
            logger.error("No successful runs completed — baseline capture failed")
            sys.exit(1)