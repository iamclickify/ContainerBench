import csv
import math
from pathlib import Path
from typing import Optional, Union, List, Dict, Any
from benchmark.config import CSV_EXPORT_PATH, PROCESSED_DIR


def append_to_csv(
    run_id: str,
    timestamp: str,
    workload: str,
    strategy: str,
    repetition: int,
    build_time_seconds: Union[float, str],
    image_size_mb: Union[float, str],
    layer_count: Union[int, str],
    startup_time_seconds: Union[float, str],
    critical_vulnerabilities: Union[int, str],
    high_vulnerabilities: Union[int, str],
    medium_vulnerabilities: Union[int, str],
    low_vulnerabilities: Union[int, str],
    unknown_vulnerabilities: Union[int, str],
    build_status: str,
    startup_status: str,
    security_scan_status: str,
    overall_status: str,
    notes: str
) -> None:
    """Appends a single experiment result row (including independent status fields) to the CSV file."""
    file_path = Path(CSV_EXPORT_PATH)
    file_exists = file_path.exists()
    
    headers = [
        "run_id",
        "timestamp",
        "workload",
        "strategy",
        "repetition",
        "build_time_seconds",
        "image_size_mb",
        "layer_count",
        "startup_time_seconds",
        "critical_vulnerabilities",
        "high_vulnerabilities",
        "medium_vulnerabilities",
        "low_vulnerabilities",
        "unknown_vulnerabilities",
        "build_status",
        "startup_status",
        "security_scan_status",
        "overall_status",
        "notes"
    ]
    
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Check if existing CSV has obsolete headers, if so delete it so it regenerates correctly
    if file_exists:
        try:
            with open(file_path, mode="r", encoding="utf-8") as f:
                first_line = f.readline()
                if "overall_status" not in first_line:
                    f.close()
                    file_path.unlink()
                    file_exists = False
        except Exception:
            pass
            
    with open(file_path, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(headers)
        writer.writerow([
            run_id,
            timestamp,
            workload,
            strategy,
            repetition,
            build_time_seconds,
            image_size_mb,
            layer_count,
            startup_time_seconds,
            critical_vulnerabilities,
            high_vulnerabilities,
            medium_vulnerabilities,
            low_vulnerabilities,
            unknown_vulnerabilities,
            build_status,
            startup_status,
            security_scan_status,
            overall_status,
            notes
        ])


def is_already_benchmarked(workload: str, strategy: str) -> bool:
    """Checks if a workload and strategy pair is already present in the CSV file."""
    file_path = Path(CSV_EXPORT_PATH)
    if not file_path.exists():
        return False
    try:
        with open(file_path, mode="r", newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            headers = next(reader, None)
            if not headers:
                return False
            try:
                workload_idx = headers.index("workload")
                strategy_idx = headers.index("strategy")
            except ValueError:
                return False
            for row in reader:
                if len(row) > max(workload_idx, strategy_idx):
                    if row[workload_idx] == workload and row[strategy_idx] == strategy:
                        return True
    except Exception:
        pass
    return False


def _mean(values: List[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _median(values: List[float]) -> float:
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    if n % 2 == 1:
        return sorted_vals[n // 2]
    return (sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / 2.0


def _stdev(values: List[float]) -> float:
    if len(values) < 2:
        return 0.0
    avg = _mean(values)
    variance = sum((x - avg) ** 2 for x in values) / (len(values) - 1)
    return math.sqrt(variance)


def generate_summary_csv(workload: str) -> Path:
    """Calculates statistics per strategy for the workload and saves to processed summary CSV."""
    raw_path = Path(CSV_EXPORT_PATH)
    summary_path = Path(PROCESSED_DIR) / f"{workload}_summary.csv"
    
    if not raw_path.exists():
        raise Exception(f"Raw CSV file does not exist: {raw_path}")
        
    strategy_groups: Dict[str, List[Dict[str, Any]]] = {}
    
    with open(raw_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("workload") == workload:
                strat = row.get("strategy", "")
                if strat not in strategy_groups:
                    strategy_groups[strat] = []
                strategy_groups[strat].append(row)
                
    summary_headers = [
        "strategy",
        "mean_build_time_seconds",
        "median_build_time_seconds",
        "stdev_build_time_seconds",
        "mean_image_size_mb",
        "mean_startup_time_seconds",
        "mean_layer_count",
        "mean_critical_vulnerabilities",
        "mean_high_vulnerabilities",
        "mean_medium_vulnerabilities",
        "mean_low_vulnerabilities",
        "total_runs",
        "passed_runs",
        "failed_runs"
    ]
    
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    
    with open(summary_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(summary_headers)
        
        for strat, runs in strategy_groups.items():
            build_times = []
            sizes = []
            startups = []
            layers = []
            criticals = []
            highs = []
            mediums = []
            lows = []
            passed = 0
            failed = 0
            
            for r in runs:
                status = r.get("overall_status", "FAIL")
                if status == "PASS":
                    passed += 1
                else:
                    failed += 1
                    
                try:
                    build_times.append(float(r["build_time_seconds"]))
                except (ValueError, TypeError, KeyError):
                    pass
                try:
                    if r.get("image_size_mb"):
                        sizes.append(float(r["image_size_mb"]))
                except (ValueError, TypeError):
                    pass
                try:
                    if r.get("startup_time_seconds"):
                        startups.append(float(r["startup_time_seconds"]))
                except (ValueError, TypeError):
                    pass
                try:
                    if r.get("layer_count"):
                        layers.append(int(r["layer_count"]))
                except (ValueError, TypeError):
                    pass
                try:
                    if r.get("critical_vulnerabilities"):
                        criticals.append(int(r["critical_vulnerabilities"]))
                except (ValueError, TypeError):
                    pass
                try:
                    if r.get("high_vulnerabilities"):
                        highs.append(int(r["high_vulnerabilities"]))
                except (ValueError, TypeError):
                    pass
                try:
                    if r.get("medium_vulnerabilities"):
                        mediums.append(int(r["medium_vulnerabilities"]))
                except (ValueError, TypeError):
                    pass
                try:
                    if r.get("low_vulnerabilities"):
                        lows.append(int(r["low_vulnerabilities"]))
                except (ValueError, TypeError):
                    pass

            writer.writerow([
                strat,
                round(_mean(build_times), 3),
                round(_median(build_times), 3),
                round(_stdev(build_times), 3),
                round(_mean(sizes), 2) if sizes else 0.0,
                round(_mean(startups), 3) if startups else 0.0,
                round(_mean(layers), 1) if layers else 0.0,
                round(_mean(criticals), 1) if criticals else 0.0,
                round(_mean(highs), 1) if highs else 0.0,
                round(_mean(mediums), 1) if mediums else 0.0,
                round(_mean(lows), 1) if lows else 0.0,
                len(runs),
                passed,
                failed
            ])
            
    return summary_path