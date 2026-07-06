import datetime
import time
import uuid
from pathlib import Path
from typing import List, Optional, Any
from benchmark.config import ROOT_DIR, CSV_EXPORT_PATH
from benchmark.models import Experiment
from benchmark.core.database import get_connection, initialize_database
from benchmark.core.docker_runner import (
    build_image,
    get_image_size,
    get_layer_count,
    measure_startup_time,
    run_trivy_scan,
    is_trivy_installed
)
from benchmark.core.metrics import Timer
from benchmark.core.workload_loader import WorkloadLoader
from benchmark.core.exporter import append_to_csv, is_already_benchmarked, generate_summary_csv
from benchmark.utils.logger import get_logger
from benchmark.utils.environment import collect_environment

logger = get_logger(__name__)


class BenchmarkEngine:
    """Orchestrates container benchmarking experiments."""

    def __init__(self, workloads_dir: Path = None):
        self.loader = WorkloadLoader(workloads_dir)

    def run_suite(
        self,
        workload: Optional[str] = None,
        strategy: Optional[str] = None,
        all_strategies: bool = False,
        all_workloads: bool = False,
        force: bool = False,
        repetitions: int = 1
    ) -> bool:
        """Orchestrates single, workload-wide, or project-wide execution suites with repetitions."""
        collect_environment()

        suite_timer = Timer()
        suite_timer.start_timer()

        # Resolve workloads to run
        if all_workloads:
            workload_names = self.loader.list_workloads()
            if not workload_names:
                logger.error("No workloads discovered in workloads/ directory.")
                return False
        elif workload:
            workload_names = [workload]
        else:
            logger.error("No workload or project-wide execution specified.")
            return False

        # Gather target experiments to run
        experiments_to_run = []
        for w_name in workload_names:
            metadata = self.loader.get_metadata(w_name)
            dockerfiles = metadata.get("dockerfiles", {})
            
            if not dockerfiles:
                logger.warning(f"No strategies/dockerfiles found in metadata for workload: {w_name}")
                continue
                
            if all_workloads or all_strategies:
                for strat in dockerfiles.keys():
                    experiments_to_run.append((w_name, strat))
            elif strategy:
                if strategy not in dockerfiles:
                    logger.error(f"Strategy '{strategy}' not found in workload '{w_name}' metadata. Available: {list(dockerfiles.keys())}")
                    return False
                experiments_to_run.append((w_name, strategy))
            else:
                logger.error(f"Please specify a strategy or --all-strategies for workload '{w_name}'.")
                return False

        if not experiments_to_run:
            logger.warning("No benchmarks resolved to run.")
            return False

        # Build list of runs
        total_benchmarks = len(experiments_to_run) * repetitions
        passed = 0
        failed = 0
        skipped = 0

        # Group by workload for progress tracking
        workloads_groups = {}
        for w_name, strat in experiments_to_run:
            if w_name not in workloads_groups:
                workloads_groups[w_name] = []
            workloads_groups[w_name].append(strat)

        workload_keys = list(workloads_groups.keys())
        num_workloads = len(workload_keys)

        for w_idx, w_name in enumerate(workload_keys, start=1):
            strategies_list = workloads_groups[w_name]
            num_strategies = len(strategies_list)
            
            for s_idx, strat in enumerate(strategies_list, start=1):
                # Check skipping
                if not force and is_already_benchmarked(w_name, strat):
                    print(f"\n[Skipped] {w_name} ({strat}) already present in CSV.")
                    skipped += repetitions
                    continue
                
                # Run repetitions
                for rep in range(1, repetitions + 1):
                    print(f"\n[Progress] Workload {w_idx}/{num_workloads} | Strategy {s_idx}/{num_strategies} | Repetition {rep}/{repetitions} - {w_name} ({strat})")
                    
                    success = self.run_benchmark(w_name, strat, rep)
                    if success:
                        passed += 1
                    else:
                        failed += 1

        suite_timer.stop_timer()
        total_executed = passed + failed

        # Generate summary CSV files
        for w_name in workload_keys:
            if passed + failed > 0 or force:
                try:
                    generate_summary_csv(w_name)
                except Exception as e:
                    logger.error(f"Failed to generate summary CSV for {w_name}: {e}")

        # Print final summary (special format for pilot runs)
        workload_title = workload.capitalize() if workload else "Project-wide"
        num_strategies_tested = len(experiments_to_run)
        
        print("\n" + "=" * 42)
        print(f"{workload_title} Pilot Benchmark Complete")
        print("=" * 42)
        print(f"Strategies Tested : {num_strategies_tested}")
        print(f"Repetitions       : {repetitions}")
        print(f"Total Runs        : {total_benchmarks}")
        print(f"Successful Runs   : {passed}")
        print(f"Failed Runs       : {failed}")
        print("Raw CSV Saved")
        print("Summary CSV Saved")
        print("=" * 42 + "\n")

        # Let it succeed if overall_status is PASS or PARTIAL
        return failed == 0

    def run_benchmark(self, workload: str, strategy: str, repetition: int = 1) -> bool:
        """Runs the entire benchmark flow collecting research metrics and independent status fields."""
        # 1. Load metadata
        metadata = self.loader.get_metadata(workload)
        workload_dir = Path(metadata["path"])
        
        if not workload_dir.exists():
            logger.error(f"Workload directory not found: {workload_dir}")
            return False
        
        dockerfiles = metadata.get("dockerfiles", {})
        if strategy not in dockerfiles:
            logger.error(f"Strategy '{strategy}' not found in workload metadata. Available: {list(dockerfiles.keys())}")
            return False

        dockerfile_name = dockerfiles[strategy]
        
        # Resolve Dockerfile path
        dockerfile_path = workload_dir / "dockerfiles" / dockerfile_name
        if not dockerfile_path.exists():
            dockerfile_path = workload_dir / dockerfile_name
            if not dockerfile_path.exists():
                logger.error(f"Dockerfile not found: {dockerfile_name}")
                return False

        # Resolve Context path
        context_name = metadata.get("context", ".")
        context_path = workload_dir / context_name
        
        # Build image tag
        image_name = metadata.get("image_name", f"containerbench/{workload}")
        image_tag = f"{image_name}:{strategy}"

        run_id = f"run_{uuid.uuid4().hex[:8]}"
        timestamp = datetime.datetime.now().replace(microsecond=0).isoformat()
        command = f'docker build -t "{image_tag}" -f "{dockerfile_path}" "{context_path}"'
        
        # 2. Build Docker Image & Measure Build Time
        timer = Timer()
        timer.start_timer()
        result = build_image(command)
        timer.stop_timer()
        
        build_time_seconds = timer.elapsed
        
        # Independent statuses init
        build_status = "PENDING"
        startup_status = "PENDING"
        security_scan_status = "PENDING"
        overall_status = "PENDING"
        
        notes_list = []
        
        image_size_mb: Any = ""
        layer_count: Any = ""
        startup_time_seconds: Any = ""
        critical_vulnerabilities: Any = ""
        high_vulnerabilities: Any = ""
        medium_vulnerabilities: Any = ""
        low_vulnerabilities: Any = ""
        unknown_vulnerabilities: Any = ""

        # Status Logic
        if result.returncode != 0:
            build_status = "FAIL"
            startup_status = "SKIPPED"
            security_scan_status = "SKIPPED"
            overall_status = "FAIL"
            
            # Save complete command details to notes
            notes_list.append(f"Docker build failed. Command: {command}")
            if result.stdout:
                notes_list.append(f"Stdout: {result.stdout.strip()}")
            if result.stderr:
                notes_list.append(f"Stderr: {result.stderr.strip()}")
        else:
            build_status = "PASS"
            notes_list.append("Successful build")
            
            # Size metric
            try:
                image_size_mb = get_image_size(image_tag)
            except Exception as e:
                notes_list.append(f"Size check failed: {e}")
                
            # Layer Count metric
            try:
                layer_count = get_layer_count(image_tag)
            except Exception as e:
                notes_list.append(f"Layer check failed: {e}")
                
            # Startup Time metric
            try:
                startup_time_seconds = measure_startup_time(image_tag, timeout=15.0)
                startup_status = "PASS"
            except Exception as e:
                startup_status = "FAIL"
                notes_list.append(f"Startup check failed: {e}")
                
            # Trivy scan metric
            if not is_trivy_installed():
                security_scan_status = "SKIPPED"
                notes_list.append("TRIVY_NOT_INSTALLED")
            else:
                try:
                    vulns = run_trivy_scan(image_tag)
                    critical_vulnerabilities = vulns["CRITICAL"]
                    high_vulnerabilities = vulns["HIGH"]
                    medium_vulnerabilities = vulns["MEDIUM"]
                    low_vulnerabilities = vulns["LOW"]
                    unknown_vulnerabilities = vulns["UNKNOWN"]
                    security_scan_status = "PASS"
                except Exception as e:
                    security_scan_status = "FAIL"
                    notes_list.append(f"Trivy check failed: {e}")
            
            # Determine overall status
            if startup_status == "PASS":
                overall_status = "PASS"
            else:
                overall_status = "PARTIAL"

        notes = "; ".join(notes_list)

        # 4. Save to SQLite database (source of truth)
        initialize_database()
        self._save_to_db(
            run_id, workload, strategy, repetition, str(dockerfile_path), image_tag,
            build_time_seconds, image_size_mb, layer_count, startup_time_seconds,
            critical_vulnerabilities, high_vulnerabilities, medium_vulnerabilities,
            low_vulnerabilities, unknown_vulnerabilities,
            build_status, startup_status, security_scan_status, overall_status, notes, timestamp
        )

        # 5. Append experiment to CSV
        append_to_csv(
            run_id=run_id,
            timestamp=timestamp,
            workload=workload,
            strategy=strategy,
            repetition=repetition,
            build_time_seconds=build_time_seconds,
            image_size_mb=image_size_mb,
            layer_count=layer_count,
            startup_time_seconds=startup_time_seconds,
            critical_vulnerabilities=critical_vulnerabilities,
            high_vulnerabilities=high_vulnerabilities,
            medium_vulnerabilities=medium_vulnerabilities,
            low_vulnerabilities=low_vulnerabilities,
            unknown_vulnerabilities=unknown_vulnerabilities,
            build_status=build_status,
            startup_status=startup_status,
            security_scan_status=security_scan_status,
            overall_status=overall_status,
            notes=notes
        )

        # 6. Print benchmark summary
        self._print_summary(
            build_status, startup_status, security_scan_status, overall_status,
            build_time_seconds, image_size_mb
        )

        # Only a failed Docker build should completely fail an experiment.
        return overall_status in ["PASS", "PARTIAL"]

    def _save_to_db(
        self, run_id: str, workload: str, strategy: str, repetition: int, dockerfile: str, image_tag: str,
        build_time: float, image_size: Any, layer_count: Any, startup_time: Any,
        crit_v: Any, high_v: Any, med_v: Any, low_v: Any, unk_v: Any,
        build_status: str, startup_status: str, security_scan_status: str, overall_status: str, notes: str, timestamp: str
    ) -> None:
        """Saves the experiment record to SQLite."""
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO experiments (
                    run_id, workload, strategy, repetition, dockerfile, image_tag, build_type,
                    build_time, image_size_mb, layer_count, startup_time_seconds,
                    critical_vulnerabilities, high_vulnerabilities, medium_vulnerabilities,
                    low_vulnerabilities, unknown_vulnerabilities,
                    build_status, startup_status, security_scan_status, overall_status, notes, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id, workload, strategy, repetition, dockerfile, image_tag, "docker",
                    build_time,
                    None if image_size == "" else image_size,
                    None if layer_count == "" else layer_count,
                    None if startup_time == "" else startup_time,
                    None if crit_v == "" else crit_v,
                    None if high_v == "" else high_v,
                    None if med_v == "" else med_v,
                    None if low_v == "" else low_v,
                    None if unk_v == "" else unk_v,
                    build_status, startup_status, security_scan_status, overall_status, notes, timestamp
                )
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to save experiment to database: {e}")

    def _print_summary(
        self, build_status: str, startup_status: str, security_scan_status: str, overall_status: str,
        build_time: float, image_size: Any
    ) -> None:
        """Prints a clean benchmark summary to the console matching the requested layout."""
        csv_rel = Path(CSV_EXPORT_PATH).relative_to(ROOT_DIR) if CSV_EXPORT_PATH.is_relative_to(ROOT_DIR) else CSV_EXPORT_PATH
        
        build_time_str = f"{build_time:.3f} s"
        image_size_str = f"{image_size:.2f} MB" if image_size != "" else "NULL"

        summary = (
            "========================================\n"
            "ContainerBench Benchmark\n"
            "========================================\n"
            f"Build           : {build_status}\n"
            f"Startup         : {startup_status}\n"
            f"Security Scan   : {security_scan_status}\n"
            f"Overall         : {overall_status}\n"
            f"Build Time      : {build_time_str}\n"
            f"Image Size      : {image_size_str}\n"
            f"CSV Updated     : {csv_rel}\n"
            "========================================\n"
        )
        print(summary)
