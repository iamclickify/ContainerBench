import argparse
import sys
from benchmark.core.benchmark_engine import BenchmarkEngine
from benchmark.utils.logger import get_logger

logger = get_logger(__name__)


def main() -> None:
    """CLI entry point for ContainerBench."""
    parser = argparse.ArgumentParser(description="ContainerBench Benchmark Automation Runner")
    parser.add_argument(
        "--workload",
        type=str,
        help="Target workload to benchmark (e.g., express)"
    )
    parser.add_argument(
        "--strategy",
        type=str,
        help="Docker optimization strategy to benchmark (e.g., baseline, alpine)"
    )
    parser.add_argument(
        "--all-strategies",
        action="store_true",
        help="Benchmark every strategy defined in metadata.yaml for the given workload"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Discover and benchmark every strategy for all workloads"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force execution even if benchmarks are already recorded in CSV"
    )
    parser.add_argument(
        "--repetitions",
        type=int,
        default=1,
        help="Number of times to repeat each benchmark run (default: 1)"
    )
    parser.add_argument(
        "--pilot",
        action="store_true",
        help="Runs the complete pilot experiment for Express (6 strategies x 5 repetitions)"
    )

    args = parser.parse_args()

    # If pilot flag is set, pre-configure workloads and repetitions
    if args.pilot:
        args.workload = "express"
        args.all_strategies = True
        args.repetitions = 5
        args.force = True  # Pilot runs should force execute to collect fresh pilot data

    # Validation
    if not args.all:
        if not args.workload:
            parser.error("Must specify --workload unless --all or --pilot is set.")
        if not args.strategy and not args.all_strategies:
            parser.error("Must specify --strategy or --all-strategies when --workload is set.")

    if args.repetitions < 1:
        parser.error("Repetitions must be a positive integer greater than or equal to 1.")

    engine = BenchmarkEngine()
    success = engine.run_suite(
        workload=args.workload,
        strategy=args.strategy,
        all_strategies=args.all_strategies,
        all_workloads=args.all,
        force=args.force,
        repetitions=args.repetitions
    )
    
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()