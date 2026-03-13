from datetime import datetime
from pathlib import Path

'''
def create_report_directory() -> Path:
    """
    Creates a timestamped report directory inside /reports
    Returns the Path object of the created directory.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    reports_root = Path("reports")
    reports_root.mkdir(exist_ok=True)

    report_dir = reports_root / timestamp
    report_dir.mkdir(exist_ok=True)

    return report_dir


def get_report_file_prefix(report_dir: Path) -> str:
    """
    Returns the prefix path for Locust CSV reports.
    Locust automatically appends _stats.csv, _failures.csv etc.
    """
    return str(report_dir / "report")


def generate_report(sla_results: dict, report_dir: Path, comparison_flag: bool) -> Path:
    """
    Generate HTML performance report from SLA evaluation results.

    Args:
        sla_results:     Dict of per-API per-metric evaluation results
        report_dir:      Path to timestamped report directory
        comparison_flag: True if this was a comparison run, False if baseline capture

    Returns:
        Path to the generated report file
    """
    report_path = report_dir / "performance_report.html"

    # ── Separate APIs by status ────────────────────────────────────────────
    breached_apis        = []
    passed_apis          = []
    new_baseline_apis    = []
    removed_apis         = []

    for api_name, metrics in sla_results.items():
        status = metrics.get("_api_status", "UNKNOWN")
        if status == "BREACH":
            breached_apis.append(api_name)
        elif status == "PASS":
            passed_apis.append(api_name)
        elif status in ("NEW_BASELINE_CAPTURED", "NEW_BASELINE_SKIPPED"):
            new_baseline_apis.append(api_name)
        elif status == "REMOVED_API":
            removed_apis.append(api_name)

    # ── Console summary ────────────────────────────────────────────────────
    print("\n" + "="*60)
    print("📊 PERFORMANCE REPORT SUMMARY")
    print("="*60)
    print(f"  Run type : {'COMPARISON' if comparison_flag else 'BASELINE CAPTURE'}")
    print(f"  Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Total APIs evaluated : {len(sla_results)}")
    print(f"  ✅ PASS              : {len(passed_apis)}")
    print(f"  🔴 BREACH            : {len(breached_apis)}")
    print(f"  🆕 NEW_BASELINE      : {len(new_baseline_apis)}")
    print(f"  ⚠️  REMOVED_API       : {len(removed_apis)}")

    if breached_apis:
        print("\n  ⚠️  BREACH SUMMARY:")
        for api in breached_apis:
            breached_metrics = [
                f"{m} (+{v['deviation_pct']}%)"
                for m, v in sla_results[api].items()
                if not m.startswith("_") and v.get("status") == "BREACH"
            ]
            print(f"    🔴 {api}")
            for bm in breached_metrics:
                print(f"       → {bm}")
    print("="*60)

    # ── Build HTML ─────────────────────────────────────────────────────────
    html = _build_html(sla_results, comparison_flag, {
        "breached_apis":     breached_apis,
        "passed_apis":       passed_apis,
        "new_baseline_apis": new_baseline_apis,
        "removed_apis":      removed_apis,
    })

    with open(report_path, "w") as f:
        f.write(html)

    print(f"\n📄 HTML report written to: {report_path}")
    return report_path


def _build_html(sla_results: dict, comparison_flag: bool, buckets: dict) -> str:
    """Build the full HTML report string."""

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    run_type  = "COMPARISON RUN" if comparison_flag else "BASELINE CAPTURE RUN"

    # ── Summary cards ──────────────────────────────────────────────────────
    summary_cards = f"""
    <div class="cards">
        <div class="card pass">
            <div class="card-number">{len(buckets['passed_apis'])}</div>
            <div class="card-label">✅ PASS</div>
        </div>
        <div class="card breach">
            <div class="card-number">{len(buckets['breached_apis'])}</div>
            <div class="card-label">🔴 BREACH</div>
        </div>
        <div class="card new">
            <div class="card-number">{len(buckets['new_baseline_apis'])}</div>
            <div class="card-label">🆕 NEW BASELINE</div>
        </div>
        <div class="card removed">
            <div class="card-number">{len(buckets['removed_apis'])}</div>
            <div class="card-label">⚠️ REMOVED</div>
        </div>
    </div>
    """

    # ── Breach summary block ───────────────────────────────────────────────
    breach_rows = ""
    for api in buckets["breached_apis"]:
        breached_metrics = [
            f"{m} <span class='dev'>(+{v['deviation_pct']}%)</span>"
            for m, v in sla_results[api].items()
            if not m.startswith("_") and v.get("status") == "BREACH"
        ]
        breach_rows += f"""
        <tr>
            <td><strong>{api}</strong></td>
            <td>{"<br>".join(breached_metrics)}</td>
        </tr>"""

    breach_section = f"""
    <h2>🔴 Breach Summary</h2>
    <table>
        <thead><tr><th>API</th><th>Breached Metrics</th></tr></thead>
        <tbody>{breach_rows if breach_rows else
            "<tr><td colspan='2'>No breaches detected ✅</td></tr>"}</tbody>
    </table>
    """ if comparison_flag else ""

    # ── Per-API per-metric detail table ───────────────────────────────────
    detail_rows = ""
    for api_name, metrics in sla_results.items():
        api_status = metrics.get("_api_status", "UNKNOWN")

        # Special status rows — no metric breakdown
        if api_status in ("NEW_BASELINE_CAPTURED", "NEW_BASELINE_SKIPPED", "REMOVED_API"):
            label_map = {
                "NEW_BASELINE_CAPTURED": "🆕 NEW BASELINE CAPTURED",
                "NEW_BASELINE_SKIPPED":  "🆕 NEW BASELINE SKIPPED",
                "REMOVED_API":           "⚠️ REMOVED API",
            }
            reason = metrics.get("_reason", "—")
            detail_rows += f"""
            <tr class="special-row">
                <td><strong>{api_name}</strong></td>
                <td colspan="6">{label_map[api_status]} — {reason}</td>
            </tr>"""
            continue

        # Normal metric rows
        for metric_name, evaluation in metrics.items():
            if metric_name.startswith("_"):
                continue

            status       = evaluation.get("status", "—")
            status_class = "pass" if status == "PASS" else "breach"
            status_label = "✅ PASS" if status == "PASS" else "🔴 BREACH"
            dev          = evaluation.get("deviation_pct", 0)
            dev_class    = "positive-dev" if dev > 0 else "negative-dev"

            detail_rows += f"""
            <tr>
                <td>{api_name}</td>
                <td>{metric_name}</td>
                <td>{evaluation.get('baseline_value', '—')}</td>
                <td>{evaluation.get('current_value', '—')}</td>
                <td class="{dev_class}">{dev:+.2f}%</td>
                <td>{evaluation.get('threshold', '—')}</td>
                <td class="{status_class}">{status_label}</td>
            </tr>"""

    detail_section = f"""
    <h2>📋 Per-API Metric Detail</h2>
    <table>
        <thead>
            <tr>
                <th>API</th>
                <th>Metric</th>
                <th>Baseline</th>
                <th>Current</th>
                <th>Deviation %</th>
                <th>Threshold</th>
                <th>Status</th>
            </tr>
        </thead>
        <tbody>{detail_rows}</tbody>
    </table>
    """

    # ── Full HTML page ─────────────────────────────────────────────────────
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Performance Report — {timestamp}</title>
    <style>
        body       {{ font-family: Arial, sans-serif; margin: 40px; background: #f9f9f9; color: #333; }}
        h1         {{ color: #2c3e50; }}
        h2         {{ color: #34495e; margin-top: 40px; }}
        .run-type  {{ display: inline-block; padding: 6px 14px; border-radius: 4px;
                      background: #2c3e50; color: white; font-weight: bold; }}
        .cards     {{ display: flex; gap: 20px; margin: 30px 0; }}
        .card      {{ padding: 20px 30px; border-radius: 8px; text-align: center;
                      min-width: 120px; color: white; }}
        .card.pass    {{ background: #27ae60; }}
        .card.breach  {{ background: #e74c3c; }}
        .card.new     {{ background: #2980b9; }}
        .card.removed {{ background: #f39c12; }}
        .card-number  {{ font-size: 2em; font-weight: bold; }}
        .card-label   {{ font-size: 0.85em; margin-top: 6px; }}
        table      {{ width: 100%; border-collapse: collapse; background: white;
                      box-shadow: 0 1px 4px rgba(0,0,0,0.1); margin-bottom: 40px; }}
        th         {{ background: #2c3e50; color: white; padding: 10px 14px; text-align: left; }}
        td         {{ padding: 9px 14px; border-bottom: 1px solid #eee; }}
        tr:hover   {{ background: #f1f1f1; }}
        .pass      {{ color: #27ae60; font-weight: bold; }}
        .breach    {{ color: #e74c3c; font-weight: bold; }}
        .positive-dev {{ color: #e74c3c; }}
        .negative-dev {{ color: #27ae60; }}
        .dev       {{ font-size: 0.85em; color: #888; }}
        .special-row td {{ background: #fef9e7; color: #7d6608; font-style: italic; }}
    </style>
</head>
<body>
    <h1>📊 Performance Report</h1>
    <p><span class="run-type">{run_type}</span> &nbsp; {timestamp}</p>
    {summary_cards}
    {breach_section}
    {detail_section}
</body>
</html>"""

def generate_page_report(
    report_dir        : Path,
    csv_path          : Path,
    users_per_profile : dict,
    total_users       : int
) -> Path:
    """
    Generate page-level HTML report with Chart.js grouped bar chart.

    Args:
        report_dir        : Path to timestamped report directory
        csv_path          : Path to report_stats.csv
        users_per_profile : { profile_name: user_count }
        total_users       : total number of users from --users CLI arg

    Returns:
        Path to generated page_report.html
    """
    import csv

    report_path = report_dir / "page_report.html"

    if not csv_path.exists():
        print(f"⚠️   Stats file not found: {csv_path} — "
              f"skipping page report generation")
        return None

    # ── Parse CSV ──────────────────────────────────────────────────────────
    page_rows     = {}   # { page_key: { profile_name: metrics } }
    endpoint_rows = {}   # { page_key: { profile_name: [ {label, metrics} ] } }

    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)

        for row in reader:
            row_type = row.get("Type", "").strip()
            row_name = row.get("Name", "").strip()

            if not row_name or row_name == "Aggregated":
                continue

            if not row_name.startswith("["):
                continue

            try:
                # ── Extract page_key ───────────────────────────────────────
                first_end  = row_name.index("]")
                page_key   = row_name[1:first_end]

                # ── Extract profile_name ───────────────────────────────────
                second_start = row_name.index("[", first_end)
                second_end   = row_name.index("]", second_start)
                profile_name = row_name[second_start + 1:second_end]

                # ── Extract endpoint label ─────────────────────────────────
                endpoint_label = row_name[second_end + 1:].strip()

            except ValueError:
                continue

            # ── Parse metrics ──────────────────────────────────────────────
            metrics = {}
            for key, value in row.items():
                if key in ("Type", "Name"):
                    continue
                try:
                    metrics[key] = float(value)
                except (ValueError, TypeError):
                    metrics[key] = value

            # ── Route to bucket ────────────────────────────────────────────
            if row_type == "PAGE":
                if page_key not in page_rows:
                    page_rows[page_key] = {}
                page_rows[page_key][profile_name] = metrics

            else:
                if page_key not in endpoint_rows:
                    endpoint_rows[page_key] = {}
                if profile_name not in endpoint_rows[page_key]:
                    endpoint_rows[page_key][profile_name] = []
                endpoint_rows[page_key][profile_name].append({
                    "label"  : endpoint_label,
                    "metrics": metrics
                })

    # ── Build and write HTML ───────────────────────────────────────────────
    html = _build_page_report_html(
        page_rows         = page_rows,
        endpoint_rows     = endpoint_rows,
        users_per_profile = users_per_profile,
        total_users       = total_users
    )

    with open(report_path, "w") as f:
        f.write(html)

    print(f"📄  Page report written to: {report_path}")
    return report_path

def _build_page_report_html(
    page_rows         : dict,
    endpoint_rows     : dict,
    users_per_profile : dict,
    total_users       : int
) -> str:
    """Build full HTML string for page report with checkbox profile filter."""

    timestamp     = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    page_keys     = sorted(page_rows.keys())
    profile_names = sorted(users_per_profile.keys())

    # ── Summary cards ──────────────────────────────────────────────────────
    profile_breakdown = "".join([
        f"<div class='profile-breakdown-row'>"
        f"<span class='pb-name'>{p}</span>"
        f"<span class='pb-count'>{users_per_profile[p]} users</span>"
        f"</div>"
        for p in profile_names
    ])

    summary_cards = f"""
    <div class="cards">
        <div class="card">
            <div class="card-number">{len(page_keys)}</div>
            <div class="card-label">📄 Pages</div>
        </div>
        <div class="card">
            <div class="card-number">{len(profile_names)}</div>
            <div class="card-label">👤 Profiles</div>
        </div>
        <div class="card wide">
            <div class="card-label">🔢 Total Users: {total_users}</div>
            <div class="profile-breakdown">
                {profile_breakdown}
            </div>
        </div>
    </div>"""

    # ── Chart colours — one per profile ───────────────────────────────────
    chart_colours = [
        ("rgba(52,  152, 219, 0.85)", "rgba(52,  152, 219, 1)"),  # blue
        ("rgba(46,  204, 113, 0.85)", "rgba(46,  204, 113, 1)"),  # green
        ("rgba(231, 76,  60,  0.85)", "rgba(231, 76,  60,  1)"),  # red
        ("rgba(155, 89,  182, 0.85)", "rgba(155, 89,  182, 1)"),  # purple
        ("rgba(241, 196, 15,  0.85)", "rgba(241, 196, 15,  1)"),  # yellow
        ("rgba(230, 126, 34,  0.85)", "rgba(230, 126, 34,  1)"),  # orange
        ("rgba(26,  188, 156, 0.85)", "rgba(26,  188, 156, 1)"),  # teal
        ("rgba(236, 112, 99,  0.85)", "rgba(236, 112, 99,  1)"),  # salmon
        ("rgba(133, 193, 233, 0.85)", "rgba(133, 193, 233, 1)"),  # light blue
        ("rgba(130, 224, 170, 0.85)", "rgba(130, 224, 170, 1)"),  # light green
        ("rgba(174, 214, 241, 0.85)", "rgba(174, 214, 241, 1)"),  # pale blue
        ("rgba(249, 231, 159, 0.85)", "rgba(249, 231, 159, 1)"),  # pale yellow
        ("rgba(210, 180, 222, 0.85)", "rgba(210, 180, 222, 1)"),  # lavender
        ("rgba(169, 223, 191, 0.85)", "rgba(169, 223, 191, 1)"),  # mint
        ("rgba(245, 183, 177, 0.85)", "rgba(245, 183, 177, 1)"),  # pink
    ]

    # ── Build chart datasets as JS ─────────────────────────────────────────
    chart_datasets = []
    for i, profile_name in enumerate(profile_names):
        data_values = []
        for page_key in page_keys:
            avg_ms = (
                page_rows
                .get(page_key, {})
                .get(profile_name, {})
                .get("Average Response Time", 0)
            )
            data_values.append(round(avg_ms, 2))

        bg, border = chart_colours[i % len(chart_colours)]

        chart_datasets.append(f"""{{
            label           : '{profile_name}',
            data            : {data_values},
            backgroundColor : '{bg}',
            borderColor     : '{border}',
            borderWidth     : 1,
            borderRadius    : 4
        }}""")

    chart_labels      = str(page_keys)
    chart_datasets_js = ",\n".join(chart_datasets)

    # ── Checkbox controls ──────────────────────────────────────────────────
    checkboxes_html = ""
    for i, profile_name in enumerate(profile_names):
        bg, _ = chart_colours[i % len(chart_colours)]
        checkboxes_html += f"""
        <label class="checkbox-label" title="{profile_name}">
            <input
                type     = "checkbox"
                class    = "profile-checkbox"
                value    = "{i}"
                checked
                onchange = "handleCheckbox(this)"
            >
            <span
                class = "checkbox-dot"
                style = "background:{bg}">
            </span>
            {profile_name}
            <span class="checkbox-users">
                ({users_per_profile.get(profile_name, 0)} users)
            </span>
        </label>"""

    # ── Page detail cards ──────────────────────────────────────────────────
    page_cards_html = ""

    for page_key in page_keys:
        profiles_html = ""
        profile_data  = page_rows.get(page_key, {})

        for profile_name in profile_names:
            metrics    = profile_data.get(profile_name, {})
            page_total = metrics.get("Average Response Time", 0)
            user_count = users_per_profile.get(profile_name, 0)
            section_id = f"{page_key}__{profile_name}".replace(" ", "_")

            # ── Endpoint rows ──────────────────────────────────────────────
            endpoints     = endpoint_rows.get(page_key, {}).get(profile_name, [])
            endpoint_html = ""

            for ep in endpoints:
                ep_label   = ep["label"]
                ep_metrics = ep["metrics"]
                avg        = ep_metrics.get("Average Response Time", 0)
                min_val    = ep_metrics.get("Min Response Time",     0)
                max_val    = ep_metrics.get("Max Response Time",     0)
                p95        = ep_metrics.get("95%",                   0)
                req_count  = int(ep_metrics.get("Request Count",     0))
                fail_count = int(ep_metrics.get("Failure Count",     0))
                fail_class = "fail-count" if fail_count > 0 else ""

                endpoint_html += f"""
                <tr>
                    <td class="endpoint-label">{ep_label}</td>
                    <td class="metric-val">{avg:.0f}ms</td>
                    <td class="metric-val">{min_val:.0f}ms</td>
                    <td class="metric-val">{max_val:.0f}ms</td>
                    <td class="metric-val">{p95:.0f}ms</td>
                    <td class="metric-val">{req_count}</td>
                    <td class="metric-val {fail_class}">{fail_count}</td>
                </tr>"""

            toggle_btn = (
                f"<button class='toggle-btn' "
                f"onclick='toggleDetail(\"{section_id}\", this)'>"
                f"▶ Show more</button>"
            ) if endpoints else ""

            endpoint_table = f"""
            <div class="endpoint-detail" id="detail_{section_id}">
                <table class="endpoint-table">
                    <thead>
                        <tr>
                            <th>Endpoint</th>
                            <th>Avg</th>
                            <th>Min</th>
                            <th>Max</th>
                            <th>p95</th>
                            <th>Requests</th>
                            <th>Failures</th>
                        </tr>
                    </thead>
                    <tbody>
                        {endpoint_html if endpoint_html
                         else "<tr><td colspan='7'>No endpoint data</td></tr>"}
                    </tbody>
                </table>
            </div>""" if endpoints else ""

            profiles_html += f"""
            <div class="profile-row">
                <div class="profile-summary">
                    <span class="profile-name">{profile_name}</span>
                    <span class="user-count">({user_count} users)</span>
                    <span class="page-total">{page_total:.0f}ms</span>
                    {toggle_btn}
                </div>
                {endpoint_table}
            </div>"""

        page_cards_html += f"""
        <div class="page-card">
            <div class="page-header">
                <span class="page-icon">📄</span>
                <span class="page-title">{page_key}</span>
            </div>
            <div class="page-profiles">
                {profiles_html}
            </div>
        </div>"""

    if not page_cards_html:
        page_cards_html = """
        <div class="empty-state">
            No PAGE rows found in CSV —
            ensure _fire_page_event() is called in all page classes
        </div>"""

    # ── Full HTML ──────────────────────────────────────────────────────────
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Page Report — {timestamp}</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.min.js"></script>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body              {{ font-family: Arial, sans-serif;
                             background: #f4f6f9; color: #333; }}

        /* ── Header ── */
        .header           {{ background: #2c3e50; color: white;
                             padding: 24px 40px; }}
        .header h1        {{ font-size: 1.6em; margin-bottom: 6px; }}
        .header .ts       {{ color: #aab; font-size: 0.9em; }}

        /* ── Nav links ── */
        .nav-links        {{ background: #34495e; padding: 10px 40px;
                             display: flex; gap: 12px; }}
        .nav-link         {{ color: #ecf0f1; text-decoration: none;
                             padding: 6px 16px; border-radius: 4px;
                             background: #2c3e50; font-size: 0.88em;
                             border: 1px solid #4a6278; }}
        .nav-link:hover   {{ background: #1a252f; }}

        /* ── Content ── */
        .content          {{ padding: 30px 40px; max-width: 1400px;
                             margin: 0 auto; }}

        /* ── Summary cards ── */
        .cards            {{ display: flex; gap: 20px; margin-bottom: 30px;
                             flex-wrap: wrap; }}
        .card             {{ background: white; border-radius: 8px;
                             padding: 20px 28px; text-align: center;
                             box-shadow: 0 1px 4px rgba(0,0,0,0.1);
                             min-width: 130px; }}
        .card.wide        {{ text-align: left; min-width: 280px; flex: 1; }}
        .card-number      {{ font-size: 2.2em; font-weight: bold;
                             color: #2c3e50; }}
        .card-label       {{ font-size: 0.88em; color: #666;
                             margin-top: 4px; font-weight: bold; }}
        .profile-breakdown     {{ margin-top: 10px; }}
        .profile-breakdown-row {{ display: flex; justify-content: space-between;
                                   padding: 4px 0;
                                   border-bottom: 1px solid #f0f0f0; }}
        .profile-breakdown-row:last-child {{ border-bottom: none; }}
        .pb-name          {{ color: #2c3e50; font-size: 0.88em; }}
        .pb-count         {{ color: #27ae60; font-weight: bold;
                             font-size: 0.88em; }}

        /* ── Chart section ── */
        .chart-section    {{ background: white; border-radius: 8px;
                             padding: 28px 32px; margin-bottom: 30px;
                             box-shadow: 0 1px 4px rgba(0,0,0,0.1); }}
        .chart-section h2 {{ color: #2c3e50; font-size: 1.1em;
                             margin-bottom: 20px; }}

        /* ── Checkbox filter ── */
        .filter-bar       {{ display: flex; flex-wrap: wrap; gap: 10px;
                             align-items: center; margin-bottom: 20px;
                             padding: 14px 16px; background: #f8f9fa;
                             border-radius: 6px;
                             border: 1px solid #e0e0e0; }}
        .filter-title     {{ font-size: 0.88em; font-weight: bold;
                             color: #555; margin-right: 6px; }}
        .filter-actions   {{ display: flex; gap: 8px; margin-left: auto; }}
        .filter-btn       {{ background: white; border: 1px solid #ccc;
                             color: #555; padding: 4px 12px;
                             border-radius: 4px; cursor: pointer;
                             font-size: 0.82em; }}
        .filter-btn:hover {{ background: #f0f0f0; }}
        .checkbox-label   {{ display: flex; align-items: center; gap: 6px;
                             font-size: 0.85em; cursor: pointer;
                             padding: 4px 10px; border-radius: 4px;
                             background: white;
                             border: 1px solid #ddd; }}
        .checkbox-label:hover {{ background: #f0f4ff; }}
        .checkbox-dot     {{ width: 12px; height: 12px; border-radius: 50%;
                             display: inline-block; flex-shrink: 0; }}
        .checkbox-users   {{ color: #888; font-size: 0.82em; }}
        .chart-wrapper    {{ position: relative; height: 380px; }}

        /* ── Page cards ── */
        .page-card        {{ background: white; border-radius: 8px;
                             margin-bottom: 20px;
                             box-shadow: 0 1px 4px rgba(0,0,0,0.1);
                             overflow: hidden; }}
        .page-header      {{ background: #2c3e50; color: white;
                             padding: 12px 20px;
                             display: flex; align-items: center;
                             gap: 10px; }}
        .page-icon        {{ font-size: 1.1em; }}
        .page-title       {{ font-size: 1em; font-weight: bold;
                             letter-spacing: 0.4px; }}
        .page-profiles    {{ padding: 0 20px; }}

        /* ── Profile row ── */
        .profile-row      {{ border-bottom: 1px solid #eee;
                             padding: 14px 0; }}
        .profile-row:last-child {{ border-bottom: none; }}
        .profile-summary  {{ display: flex; align-items: center;
                             gap: 16px; flex-wrap: wrap; }}
        .profile-name     {{ font-weight: bold; color: #2c3e50;
                             min-width: 220px; font-size: 0.95em; }}
        .user-count       {{ color: #888; font-size: 0.85em;
                             min-width: 80px; }}
        .page-total       {{ font-size: 1.05em; color: #27ae60;
                             font-weight: bold; min-width: 90px; }}

        /* ── Toggle button ── */
        .toggle-btn       {{ background: #eaf0fb;
                             border: 1px solid #aac4ee;
                             color: #2c3e50; padding: 4px 14px;
                             border-radius: 4px; cursor: pointer;
                             font-size: 0.83em; }}
        .toggle-btn:hover {{ background: #d0e1f9; }}

        /* ── Endpoint detail ── */
        .endpoint-detail  {{ display: none; margin: 10px 0 6px 0; }}
        .endpoint-table   {{ width: 100%; border-collapse: collapse;
                             background: #fafafa; border-radius: 6px;
                             overflow: hidden; }}
        .endpoint-table th {{ background: #34495e; color: white;
                              padding: 8px 12px; text-align: left;
                              font-size: 0.83em; }}
        .endpoint-table td {{ padding: 7px 12px;
                              border-bottom: 1px solid #eee;
                              font-size: 0.88em; }}
        .endpoint-table tr:last-child td {{ border-bottom: none; }}
        .endpoint-label   {{ color: #2c3e50; font-family: monospace; }}
        .metric-val       {{ color: #555; }}
        .fail-count       {{ color: #e74c3c; font-weight: bold; }}

        /* ── Empty state ── */
        .empty-state      {{ background: white; padding: 40px;
                             text-align: center; color: #888;
                             border-radius: 8px;
                             box-shadow: 0 1px 4px rgba(0,0,0,0.1); }}

        /* ── Min 1 tooltip ── */
        .min-warning      {{ display: none; color: #e74c3c;
                             font-size: 0.82em; margin-left: 8px; }}
        .min-warning.show {{ display: inline; }}
    </style>
</head>
<body>

    <!-- ── Header ── -->
    <div class="header">
        <h1>📄 Page Performance Report</h1>
        <div class="ts">Generated: {timestamp}</div>
    </div>

    <!-- ── Navigation links ── -->
    <div class="nav-links">
        <a class="nav-link" href="report.html">
            📊 Locust Default Report
        </a>
        <a class="nav-link" href="performance_report.html">
            📈 Performance Report
        </a>
    </div>

    <div class="content">

        <!-- ── Summary cards ── -->
        {summary_cards}

        <!-- ── Chart section ── -->
        <div class="chart-section">
            <h2>📊 Response Time by Page and Profile</h2>

            <!-- ── Checkbox filter bar ── -->
            <div class="filter-bar">
                <span class="filter-title">Compare Profiles:</span>
                {checkboxes_html}
                <span class="min-warning" id="minWarning">
                    ⚠️ At least one profile must be selected
                </span>
                <div class="filter-actions">
                    <button class="filter-btn" onclick="selectAll()">
                        Select All
                    </button>
                    <button class="filter-btn" onclick="clearAll()">
                        Clear All
                    </button>
                </div>
            </div>

            <!-- ── Chart canvas ── -->
            <div class="chart-wrapper">
                <canvas id="pageChart"></canvas>
            </div>
        </div>

        <!-- ── Page detail cards ── -->
        {page_cards_html}

    </div>

    <script>
        // ── All datasets from Python ───────────────────────────────────────
        const allDatasets = [
            {chart_datasets_js}
        ];

        // ── Initialise chart ───────────────────────────────────────────────
        const ctx = document
            .getElementById('pageChart')
            .getContext('2d');

        const chart = new Chart(ctx, {{
            type: 'bar',
            data: {{
                labels  : {chart_labels},
                datasets: allDatasets
            }},
            options: {{
                responsive         : true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{
                        position: 'bottom',
                        labels  : {{
                            padding: 20,
                            font   : {{ size: 12 }}
                        }}
                    }},
                    tooltip: {{
                        callbacks: {{
                            label: function(context) {{
                                return context.dataset.label +
                                       ': ' +
                                       context.parsed.y + 'ms';
                            }}
                        }}
                    }}
                }},
                scales: {{
                    x: {{
                        grid : {{ display: false }},
                        ticks: {{ font: {{ size: 11 }} }}
                    }},
                    y: {{
                        beginAtZero: true,
                        title: {{
                            display: true,
                            text   : 'Response Time (ms)',
                            font   : {{ size: 12 }}
                        }},
                        ticks: {{
                            callback: function(value) {{
                                return value + 'ms';
                            }}
                        }}
                    }}
                }}
            }}
        }});

        // ── Handle checkbox change ─────────────────────────────────────────
        function handleCheckbox(checkbox) {{
            const checked = document.querySelectorAll(
                '.profile-checkbox:checked'
            );

            // ── Prevent unchecking last profile ───────────────────────────
            if (checked.length === 0) {{
                checkbox.checked = true;
                document
                    .getElementById('minWarning')
                    .classList.add('show');
                setTimeout(() => {{
                    document
                        .getElementById('minWarning')
                        .classList.remove('show');
                }}, 2500);
                return;
            }}

            document
                .getElementById('minWarning')
                .classList.remove('show');

            updateChart();
        }}

        // ── Update chart with checked profiles only ────────────────────────
        function updateChart() {{
            const checked = Array.from(
                document.querySelectorAll('.profile-checkbox:checked')
            ).map(cb => parseInt(cb.value));

            chart.data.datasets = allDatasets.filter((_, i) =>
                checked.includes(i)
            );
            chart.update();
        }}

        // ── Select all profiles ────────────────────────────────────────────
        function selectAll() {{
            document
                .querySelectorAll('.profile-checkbox')
                .forEach(cb => cb.checked = true);
            chart.data.datasets = allDatasets;
            chart.update();
            document
                .getElementById('minWarning')
                .classList.remove('show');
        }}

        // ── Clear all — keep at least one ─────────────────────────────────
        function clearAll() {{
            const checkboxes = document.querySelectorAll(
                '.profile-checkbox'
            );

            // ── Uncheck all except first ───────────────────────────────────
            checkboxes.forEach((cb, i) => {{
                cb.checked = (i === 0);
            }});

            chart.data.datasets = [allDatasets[0]];
            chart.update();
        }}

        // ── Toggle endpoint detail ─────────────────────────────────────────
        function toggleDetail(sectionId, btn) {{
            const detail = document.getElementById(
                'detail_' + sectionId
            );
            if (detail.style.display === 'block') {{
                detail.style.display = 'none';
                btn.textContent = '▶ Show more';
            }} else {{
                detail.style.display = 'block';
                btn.textContent = '▼ Show less';
            }}
        }}
    </script>

</body>
</html>"""
'''